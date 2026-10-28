"""Shared settings and corpus definition for the offline pipeline."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
load_dotenv(ROOT / ".env")

PAPERS_FILE = DATA_DIR / "papers.jsonl"
CITATIONS_FILE = DATA_DIR / "citations.jsonl"

S2_API_URL = "https://api.semanticscholar.org/graph/v1"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "paperweave-dev")
S2_API_KEY = os.getenv("S2_API_KEY") or None

# Landmark papers always included, so the graph has well-known anchors and
# lineage questions ("what built on RAG?") have answers.
SEED_ARXIV_IDS = [
    # Foundations
    "1706.03762",  # Attention Is All You Need
    "1810.04805",  # BERT
    "1910.10683",  # T5
    "2005.14165",  # GPT-3
    "2203.02155",  # InstructGPT
    "2303.08774",  # GPT-4 Technical Report
    "2302.13971",  # LLaMA
    "2307.09288",  # Llama 2
    "2310.06825",  # Mistral 7B
    "2106.09685",  # LoRA
    "2104.09864",  # RoFormer (RoPE)
    "2004.05150",  # Longformer
    "2205.14135",  # FlashAttention
    # Retrieval
    "1908.10084",  # Sentence-BERT
    "2004.04906",  # Dense Passage Retrieval
    "2004.12832",  # ColBERT
    "2212.10496",  # HyDE
    # Retrieval-augmented generation
    "2002.08909",  # REALM
    "2005.11401",  # RAG (Lewis et al.)
    "2007.01282",  # Fusion-in-Decoder
    "2112.04426",  # RETRO
    "2208.03299",  # Atlas
    "2307.03172",  # Lost in the Middle
    "2310.11511",  # Self-RAG
    "2312.10997",  # RAG survey (Gao et al.)
    "2401.15884",  # Corrective RAG
    "2401.18059",  # RAPTOR
    "2403.14403",  # Adaptive-RAG
    "2404.16130",  # GraphRAG (From Local to Global)
    "2405.14831",  # HippoRAG
    "2410.05779",  # LightRAG
    "2309.15217",  # RAGAS
    # Reasoning and agents
    "2201.11903",  # Chain-of-Thought
    "2210.03629",  # ReAct
    "2302.04761",  # Toolformer
    "2303.11366",  # Reflexion
    "2304.03442",  # Generative Agents
    "2305.10601",  # Tree of Thoughts
]

# Topic searches that fill the corpus beyond the seeds (Semantic Scholar bulk
# search syntax). Results are sorted by citation count, so each topic
# contributes its most influential arXiv papers.
TOPIC_QUERIES = [
    '"retrieval-augmented generation"',
    '"knowledge graph" + ("large language model" | LLM)',
    '("LLM agent" | "language agent" | "autonomous agent") + ("large language model" | LLM)',
    '"dense retrieval" | "passage retrieval"',
    '"long context" + "language model"',
    'hallucination + ("large language model" | LLM)',
]
