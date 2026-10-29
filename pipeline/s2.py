"""Minimal Semantic Scholar Graph API client with pacing and retries."""

import re
import time

import httpx

from config import S2_API_KEY, S2_API_URL

# Without a key the shared limit is roughly 100 requests / 5 minutes.
REQUEST_DELAY_S = 1.0 if S2_API_KEY else 3.5

_last_request = 0.0


def client() -> httpx.Client:
    headers = {"User-Agent": "PaperWeave/0.1 (portfolio project)"}
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    return httpx.Client(base_url=S2_API_URL, timeout=120, headers=headers)


def request(http: httpx.Client, method: str, path: str, **kwargs) -> dict | list:
    """Send a request, pacing calls and backing off on 429/5xx throttling."""
    global _last_request
    for attempt in range(8):  # up to ~6 min of backoff for the shared no-key limit
        wait = REQUEST_DELAY_S - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        resp = http.request(method, path, **kwargs)
        # S2 throttles with 429 and sometimes 5xx.
        if resp.status_code == 429 or resp.status_code >= 500:
            backoff = 10 * (attempt + 1)
            print(f"  Semantic Scholar returned {resp.status_code}; retrying in {backoff}s")
            time.sleep(backoff)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Semantic Scholar kept throttling {path}; try later or set S2_API_KEY")


def arxiv_id_of(paper: dict) -> str | None:
    """Versionless arXiv ID from a paper's externalIds, e.g. '2005.11401'."""
    raw = (paper.get("externalIds") or {}).get("ArXiv")
    return re.sub(r"v\d+$", "", raw) if raw else None
