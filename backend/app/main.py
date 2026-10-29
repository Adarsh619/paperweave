"""PaperWeave API.

    uvicorn app.main:app --reload        (from backend/)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config, stores
from app.agent import llm
from app.api import chat, papers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.getLogger("paperweave").info("LLM providers: %s", ", ".join(llm.provider_names()))
    yield
    stores.close()


app = FastAPI(title="PaperWeave API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(chat.router)
app.include_router(papers.router)


def check_databases() -> dict:
    """Real reads on both databases. UptimeRobot calls /health every few minutes, which keeps
    Render awake and stops AuraDB (3 idle days) and Qdrant Cloud (1 idle week) from pausing."""
    status = {}
    try:
        status["papers"] = stores.read("MATCH (p:Paper) RETURN count(p) AS n")[0]["n"]
    except Exception as exc:  # noqa: BLE001
        status["neo4j_error"] = type(exc).__name__
    try:
        points, _ = stores.qdrant().scroll(config.QDRANT_COLLECTION, limit=1, with_payload=False)
        status["vectors_ok"] = bool(points)
    except Exception as exc:  # noqa: BLE001
        status["qdrant_error"] = type(exc).__name__
    return status


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    status = check_databases()
    ok = "papers" in status and status.get("vectors_ok") is True
    return JSONResponse({"status": "ok" if ok else "degraded", **status}, status_code=200 if ok else 503)


@app.get("/")
def root():
    return {"name": "PaperWeave API", "docs": "/docs", "health": "/health"}
