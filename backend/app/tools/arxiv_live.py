"""Live search for papers newer than the indexed corpus: arXiv API, Semantic Scholar fallback."""

import re
import xml.etree.ElementTree as ET

import httpx

from app import config

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
STOPWORDS = {"the", "a", "an", "of", "for", "in", "on", "and", "or", "to", "with", "what", "which", "how",
             "are", "is", "new", "latest", "recent", "papers", "paper", "about"}


def _terms(query: str) -> list[str]:
    words = [w for w in re.findall(r"[A-Za-z0-9\-]+", query) if w.lower() not in STOPWORDS]
    return words[:6]


def search_arxiv(query: str, limit: int = 5) -> list[dict]:
    terms = _terms(query)
    if not terms:
        return []
    params = {
        "search_query": " AND ".join(f"all:{t}" for t in terms),
        "sortBy": "relevance",
        "max_results": limit * 2,
    }
    resp = httpx.get(ARXIV_API, params=params, timeout=10, follow_redirects=True)
    resp.raise_for_status()
    papers = []
    for entry in ET.fromstring(resp.text).findall("a:entry", ATOM):
        arxiv_id = re.sub(r"v\d+$", "", entry.findtext("a:id", "", ATOM).rsplit("/abs/", 1)[-1])
        papers.append({
            "arxiv_id": arxiv_id,
            "title": " ".join(entry.findtext("a:title", "", ATOM).split()),
            "abstract": " ".join(entry.findtext("a:summary", "", ATOM).split()),
            "year": int(entry.findtext("a:published", "0000", ATOM)[:4]),
            "published": entry.findtext("a:published", "", ATOM)[:10],
            "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
        })
    # Most relevant 2x, then newest first: "latest" questions want recent work.
    return sorted(papers, key=lambda p: p["published"], reverse=True)[:limit]


def search_semantic_scholar(query: str, limit: int = 5) -> list[dict]:
    headers = {"x-api-key": config.S2_API_KEY} if config.S2_API_KEY else {}
    resp = httpx.get(
        f"{config.S2_API_URL}/paper/search",
        params={"query": query, "limit": limit * 2, "fields": "title,abstract,year,publicationDate,externalIds"},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    papers = []
    for p in resp.json().get("data") or []:
        arxiv_id = (p.get("externalIds") or {}).get("ArXiv")
        if arxiv_id and p.get("abstract"):
            papers.append({
                "arxiv_id": re.sub(r"v\d+$", "", arxiv_id),
                "title": p["title"],
                "abstract": p["abstract"],
                "year": p.get("year"),
                "published": p.get("publicationDate") or str(p.get("year") or ""),
                "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
            })
    return sorted(papers, key=lambda p: p["published"], reverse=True)[:limit]


def search(query: str, limit: int = 5) -> tuple[list[dict], str]:
    """Returns (papers, source). Empty list if both services fail; live search is optional."""
    for name, fn in (("arXiv", search_arxiv), ("Semantic Scholar", search_semantic_scholar)):
        try:
            if papers := fn(query, limit):
                return papers, name
        except (httpx.HTTPError, ET.ParseError):
            continue
    return [], "none"
