"""Backend settings, read from environment variables (and the repo's .env when run locally)."""

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> repo root. In the Docker image there is no .env; Render sets env vars.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "paperweave-dev")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
QDRANT_CLOUD_INFERENCE = os.getenv("QDRANT_CLOUD_INFERENCE", "false").lower() == "true"
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "papers")
# Must match pipeline/config.py, which built the index. Overridable in case Qdrant Cloud
# Inference lists the same models under different names.
DENSE_MODEL = os.getenv("QDRANT_DENSE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
SPARSE_MODEL = os.getenv("QDRANT_SPARSE_MODEL", "Qdrant/bm25")

# LLM providers are tried in this order: Groq, Gemini, then local Ollama.
# Ollama is used only when no cloud key is set, or when LLM_LOCAL_FALLBACK=true.
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or None
GROQ_ANSWER_MODEL = os.getenv("GROQ_ANSWER_MODEL", "llama-3.3-70b-versatile")
GROQ_ROUTER_MODEL = os.getenv("GROQ_ROUTER_MODEL", "llama-3.1-8b-instant")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or None
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")
LLM_LOCAL_FALLBACK = os.getenv("LLM_LOCAL_FALLBACK", "false").lower() == "true"

S2_API_URL = "https://api.semanticscholar.org/graph/v1"
S2_API_KEY = os.getenv("S2_API_KEY") or None

CACHE_PATH = Path(os.getenv("CACHE_PATH", Path(__file__).resolve().parents[1] / ".cache" / "answers.sqlite"))
CACHE_TTL_S = int(os.getenv("CACHE_TTL_S", str(7 * 24 * 3600)))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "15"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

MAX_REWRITES = 2  # evidence-check retries before answering with what we have
MAX_CONTEXT_PAPERS = 12  # keeps the answer prompt within Groq's free-tier tokens/minute
