"""The agent's nodes. Each takes the state and returns the fields it changes.

    plan -> retrieve -> check --(thin evidence, < MAX_REWRITES)--> rewrite -> retrieve
                              \\--(enough)--> answer -> subgraph -> END
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage

from app import config, stores
from app.agent import citations, llm, prompts
from app.agent.state import AgentState, CypherQuery, Plan
from app.tools import arxiv_live, graph_query, vector_search
from app.tools import cypher_templates as T
from app.tools.cypher_guard import CypherRejected

GRAPH_INTENTS = {"lineage", "compare", "dataset", "top_cited", "graph"}


def _step(node: str, message: str) -> dict:
    return {"node": node, "message": message}


def heuristic_plan(question: str) -> Plan:
    """Keyword fallback if the planner LLM fails, so a question always gets an answer."""
    q = question.lower()
    year = re.search(r"\b(?:since|after|from)\s+(20\d\d)\b", q)
    if re.search(r"\b(vs\.?|versus|compare|comparison|difference)\b", q):
        intent = "compare"
    elif re.search(r"\b(improv\w*|built on|build on|extend\w*|lineage|successor)\b", q):
        intent = "lineage"
    elif re.search(r"\b(latest|newest|this (week|month|year))\b", q):
        intent = "recent"
    elif re.search(r"\b(most cited|influential|top papers)\b", q):
        intent = "top_cited"
    elif re.search(r"\b(dataset|benchmark)s?\b", q):
        intent = "dataset"
    else:
        intent = "lookup"
    return Plan(intent=intent, search_query=question[:200], min_year=int(year.group(1)) if year else None,
                needs_live=intent == "recent")


def plan(state: AgentState) -> dict:
    question = state["question"]
    try:
        result = llm.structured("router", Plan).invoke(
            [SystemMessage(prompts.PLANNER), HumanMessage(question)]
        )
        how = "planned"
    except Exception:  # noqa: BLE001 - any provider/parse failure falls back to keywords
        result, how = heuristic_plan(question), "planned (keyword fallback)"
    entities = f"; entities: {', '.join(result.entities)}" if result.entities else ""
    return {
        "plan": result.model_dump(),
        "attempts": 0,
        "papers": {},
        "facts": [],
        "steps": [_step("plan", f"{how.capitalize()}: {result.intent} question{entities}")],
    }


def _graph_tools(p: dict, question: str) -> tuple[graph_query.GraphResult, str]:
    entities, intent = p["entities"], p["intent"]
    if intent == "lineage" and entities:
        result = graph_query.GraphResult()
        for name in entities[:2]:
            r = graph_query.lineage(name)
            result.facts += r.facts
            result.paper_ids += [i for i in r.paper_ids if i not in result.paper_ids]
        return result, f"traced lineage of {', '.join(entities[:2])}"
    if intent == "compare" and entities:
        return graph_query.compare(entities[:4]), f"compared {', '.join(entities[:4])}"
    if intent == "dataset" and entities:
        return graph_query.dataset_users(entities[0]), f"looked up papers evaluating on {entities[0]}"
    if intent == "top_cited":
        topic = entities[0] if entities else None
        return graph_query.top_cited(p.get("min_year"), topic), "ranked papers by citations"
    if intent == "graph":
        query = llm.structured("router", CypherQuery).invoke([
            SystemMessage(prompts.TEXT_TO_CYPHER.format(schema=graph_query.SCHEMA_FOR_LLM)),
            HumanMessage(question),
        ])
        return graph_query.run_llm_cypher(query.cypher), "ran a generated read-only Cypher query"
    return graph_query.GraphResult(), ""


def retrieve(state: AgentState) -> dict:
    p = state["plan"]
    papers = dict(state.get("papers") or {})
    facts = list(state.get("facts") or [])
    steps, gaps = [], []

    if p["intent"] in GRAPH_INTENTS:
        try:
            result, what = _graph_tools(p, state["question"])
            new_facts = [f for f in result.facts if f not in facts]
            facts += new_facts
            details = stores.read(T.PAPER_DETAILS, ids=result.paper_ids) if result.paper_ids else []
            by_id = {d["arxiv_id"]: d for d in details}
            for i in result.paper_ids:
                if i in by_id:
                    papers.setdefault(i, {**by_id[i], "source": "graph"})
            if what:
                steps.append(_step("graph", f"Knowledge graph: {what} ({len(new_facts)} facts)"))
            if not new_facts or all(f.startswith(("No method", "'")) for f in new_facts):
                gaps.append(f"the graph had no useful facts for {p['entities'] or p['intent']}")
        except CypherRejected as exc:
            gaps.append(f"generated Cypher was rejected: {exc}")
            steps.append(_step("graph", f"Blocked an unsafe generated query ({exc})"))
        except Exception as exc:  # noqa: BLE001
            gaps.append(f"graph query failed: {exc}")
            steps.append(_step("graph", "Knowledge graph query failed; continuing with search"))

    # A generated-Cypher answer (authors, counts) stands on its own; unrelated search hits
    # would only distract the answer LLM.
    if not (p["intent"] == "graph" and facts and not gaps):
        hits = vector_search.search(p["search_query"], limit=6, min_year=p.get("min_year"))
        for h in hits:
            papers.setdefault(h["arxiv_id"], {**h, "source": "search"})
        steps.append(_step("search", f"Searched {p['search_query']!r}: {len(hits)} papers"))
        if not hits:
            gaps.append("search found no papers")

    if p.get("needs_live") or p["intent"] == "recent":
        live, source = arxiv_live.search(p["search_query"])
        for h in live:
            papers.setdefault(h["arxiv_id"], {**h, "source": "live"})
        steps.append(_step("live", f"Live {source} search: {len(live)} recent papers"))

    return {"papers": papers, "facts": facts, "gaps": gaps, "steps": steps}


def check(state: AgentState) -> dict:
    """Decide (without an LLM) whether the evidence is enough to answer."""
    gaps = state.get("gaps") or []
    if len(state.get("papers") or {}) < 2 and not state.get("facts"):
        gaps = [*gaps, "fewer than 2 relevant papers"]
    attempts = state.get("attempts", 0)
    if gaps and attempts < config.MAX_REWRITES:
        return {"gaps": gaps, "steps": [_step("check", f"Evidence is thin ({'; '.join(gaps)}); rewriting the query")]}
    note = "Evidence looks sufficient" if not gaps else "Answering with the best evidence found"
    return {"gaps": [], "steps": [_step("check", note)]}


def route_after_check(state: AgentState) -> str:
    return "rewrite" if state.get("gaps") else "answer"


def rewrite(state: AgentState) -> dict:
    p = state["plan"]
    try:
        new = llm.structured("router", Plan).invoke([
            SystemMessage(prompts.PLANNER),
            HumanMessage(state["question"]),
            HumanMessage(prompts.REWRITE.format(gaps="; ".join(state["gaps"]), plan=p)),
        ])
    except Exception:  # noqa: BLE001
        new = Plan(intent="lookup", search_query=state["question"][:200], min_year=p.get("min_year"))
    return {
        "plan": new.model_dump(),
        "attempts": state.get("attempts", 0) + 1,
        "steps": [_step("rewrite", f"Retrying as a {new.intent} question: {new.search_query!r}")],
    }


def _context(state: AgentState) -> tuple[str, str]:
    # Graph-sourced papers first (they back the facts), then search, then live results;
    # "latest" questions put the live results first.
    order = {"graph": 0, "search": 1, "live": 2}
    if state["plan"]["intent"] == "recent":
        order["live"] = -1
    papers = sorted(state["papers"].values(), key=lambda x: order.get(x.get("source"), 3))
    papers = papers[: config.MAX_CONTEXT_PAPERS]
    paper_text = "\n\n".join(
        f"[{x['arxiv_id']}] {x['title']} ({x.get('year')}){' (live arXiv result)' if x.get('source') == 'live' else ''}\n"
        f"{(x.get('abstract') or '')[:700]}"
        for x in papers
    )
    return "\n".join(state.get("facts") or []) or "(none)", paper_text


def answer(state: AgentState) -> dict:
    facts, papers = _context(state)
    system = prompts.ANSWER
    if state["plan"]["intent"] == "compare":
        system = system.replace(" No tables.", "") + prompts.ANSWER_TABLE
    response = llm.chat("answer").invoke([
        SystemMessage(system),
        HumanMessage(prompts.ANSWER_USER.format(question=state["question"], facts=facts, papers=papers)),
    ])
    text, cited = citations.validate(response.content, set(state["papers"]))
    refs = [
        {k: state["papers"][i].get(k) for k in ("arxiv_id", "title", "year", "abs_url", "source")}
        for i in cited
    ]
    return {"answer": text, "citations": refs,
            "steps": [_step("answer", f"Wrote the answer with {len(refs)} verified citations")]}


def subgraph(state: AgentState) -> dict:
    """Papers behind the answer, their methods/datasets, and the links among them, for the UI."""
    corpus_ids = [c["arxiv_id"] for c in state.get("citations") or [] if c.get("source") != "live"]
    if not corpus_ids:
        corpus_ids = [i for i, x in state["papers"].items() if x.get("source") != "live"][:6]
    ids = corpus_ids[:12]
    nodes: dict[str, dict] = {}
    links: list[dict] = []
    for i in ids:
        x = state["papers"].get(i, {})
        nodes[f"paper:{i}"] = {"id": f"paper:{i}", "type": "Paper", "label": x.get("title", i),
                               "arxiv_id": i, "year": x.get("year")}
    if ids:
        for r in stores.read(T.SUBGRAPH_ENTITIES, ids=ids):
            node_id = f"{r['label'].lower()}:{r['name']}"
            nodes.setdefault(node_id, {"id": node_id, "type": r["label"], "label": r["name"]})
            links.append({"source": f"paper:{r['paper']}", "target": node_id, "type": r["rel"]})
        for r in stores.read(T.SUBGRAPH_CITES, ids=ids):
            links.append({"source": f"paper:{r['source']}", "target": f"paper:{r['target']}", "type": "CITES"})
        methods = [n["label"] for n in nodes.values() if n["type"] == "Method"]
        for r in stores.read(T.SUBGRAPH_IMPROVES, names=methods):
            links.append({"source": f"method:{r['source']}", "target": f"method:{r['target']}", "type": "IMPROVES_ON"})
    graph = {"nodes": list(nodes.values()), "links": links}
    return {"subgraph": graph,
            "steps": [_step("subgraph", f"Built a graph of {len(graph['nodes'])} nodes and {len(links)} links")]}
