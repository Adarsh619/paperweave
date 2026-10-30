"""Compare the PaperWeave agent with vector-only RAG on the golden questions.

Each golden question lists the papers a correct answer must draw on ("gold").
Both systems get the same budget: the 12 papers the answer LLM is shown.

  context recall   share of gold papers that reach the answer LLM's context
  hit rate         share of questions with at least one gold paper in context
  citation recall  share of gold papers the final answer cites (--answers only)

    python -m evals.run_eval              # retrieval only: planner LLM + tools, fast
    python -m evals.run_eval --answers    # also write and score full answers (slow on local LLMs)
    python -m evals.run_eval --only C01,M02
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

from app import config
from app.agent import nodes
from app.tools import vector_search

HERE = Path(__file__).parent
GOLDEN = HERE / "golden.jsonl"
RESULTS_JSON = HERE / "results.json"
RESULTS_MD = HERE / "results.md"


def agent_state(question: str) -> dict:
    """Run the agent up to (not including) the answer step: plan, retrieve, check, rewrite loop."""
    state: dict = {"question": question, "steps": []}

    def apply(update: dict) -> None:
        steps = update.pop("steps", [])
        state.update(update)
        state["steps"] += steps

    apply(nodes.plan(state))
    while True:
        apply(nodes.retrieve(state))
        apply(nodes.check(state))
        if nodes.route_after_check(state) != "rewrite":
            return state
        apply(nodes.rewrite(state))


def baseline_state(question: str) -> dict:
    """Vector-only RAG: the question straight into hybrid search, top 12, no graph, no planning."""
    hits = vector_search.search(question, limit=config.MAX_CONTEXT_PAPERS)
    return {"question": question, "plan": {"intent": "lookup"}, "facts": [], "steps": [],
            "papers": {h["arxiv_id"]: {**h, "source": "search"} for h in hits}}


def score(gold: list[str], found: list[str]) -> float:
    return len(set(gold) & set(found)) / len(gold)


def evaluate(item: dict, answers: bool) -> dict:
    row = {"id": item["id"], "category": item["category"], "question": item["question"], "gold": item["gold"]}
    for name, build in (("agent", agent_state), ("baseline", baseline_state)):
        start = time.perf_counter()
        state = build(item["question"])
        context = [p["arxiv_id"] for p in nodes.context_papers(state)]
        result = {"context": context, "context_recall": score(item["gold"], context)}
        if name == "agent":
            result["intent"] = state["plan"]["intent"]
        if answers:
            out = nodes.answer(state)
            cited = [c["arxiv_id"] for c in out["citations"]]
            result.update(answer=out["answer"], cited=cited, citation_recall=score(item["gold"], cited))
        result["seconds"] = round(time.perf_counter() - start, 1)
        row[name] = result
    return row


def summarize(rows: list[dict], answers: bool) -> str:
    metrics = [("context_recall", "Context recall"), ("hit", "Hit rate")]
    if answers:
        metrics.append(("citation_recall", "Citation recall"))
    groups = [("All", rows)] + [
        (c.replace("-", " ").capitalize(), [r for r in rows if r["category"] == c])
        for c in ("lookup", "multi-hop", "comparison")
    ]

    def avg(rs: list[dict], system: str, metric: str) -> float:
        if metric == "hit":
            values = [1.0 if r[system]["context_recall"] > 0 else 0.0 for r in rs]
        else:
            values = [r[system][metric] for r in rs]
        return sum(values) / len(values)

    header = "| Questions | n | " + " | ".join(f"{label}: vector-only → agent" for _, label in metrics) + " |"
    lines = [header, "|" + "---|" * (2 + len(metrics))]
    for name, rs in groups:
        if not rs:
            continue
        cells = [f"{avg(rs, 'baseline', m):.0%} → **{avg(rs, 'agent', m):.0%}**" for m, _ in metrics]
        lines.append(f"| {name} | {len(rs)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--answers", action="store_true", help="also generate and score full answers")
    parser.add_argument("--only", help="comma-separated question IDs")
    args = parser.parse_args()

    items = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.only:
        wanted = set(args.only.split(","))
        items = [i for i in items if i["id"] in wanted]

    rows = []
    for n, item in enumerate(items, 1):
        row = evaluate(item, args.answers)
        rows.append(row)
        print(f"[{n}/{len(items)}] {item['id']} {row['agent']['intent']:10} "
              f"recall vector-only {row['baseline']['context_recall']:.0%} -> agent {row['agent']['context_recall']:.0%}",
              flush=True)

    table = summarize(rows, args.answers)
    providers = ", ".join(__import__("app.agent.llm", fromlist=["x"]).provider_names())
    report = (f"Evaluated {date.today()} on {len(rows)} golden questions with {providers}. "
              f"Both systems see at most {config.MAX_CONTEXT_PAPERS} papers.\n\n{table}\n")
    if not args.only:
        RESULTS_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        RESULTS_MD.write_text(report, encoding="utf-8")
    print("\n" + report)


if __name__ == "__main__":
    main()
