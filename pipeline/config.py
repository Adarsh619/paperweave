"""Shared settings and corpus definition for the offline pipeline."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
load_dotenv(ROOT / ".env")
# Windows without Developer Mode can't symlink the model cache; it still works.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
# Windows encodes redirected output as cp1252, which crashes on titles with "∞" etc.
sys.stdout.reconfigure(encoding="utf-8")

PAPERS_FILE = DATA_DIR / "papers.jsonl"
CITATIONS_FILE = DATA_DIR / "citations.jsonl"
ENTITIES_RAW_FILE = DATA_DIR / "entities_raw.jsonl"  # LLM output, one row per paper
ENTITIES_FILE = DATA_DIR / "entities.jsonl"  # normalized; what load_neo4j.py reads
ENTITY_INDEX_FILE = DATA_DIR / "entity_index.jsonl"  # one row per entity with aliases

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")

S2_API_URL = "https://api.semanticscholar.org/graph/v1"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "paperweave-dev")
S2_API_KEY = os.getenv("S2_API_KEY") or None

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
# true on Qdrant Cloud: the server embeds text, so nothing runs locally.
# false (local docker): qdrant-client embeds with fastembed on this machine.
QDRANT_CLOUD_INFERENCE = os.getenv("QDRANT_CLOUD_INFERENCE", "false").lower() == "true"
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "papers")
DENSE_MODEL = os.getenv("QDRANT_DENSE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")  # 384-dim, cosine
SPARSE_MODEL = os.getenv("QDRANT_SPARSE_MODEL", "Qdrant/bm25")  # keyword scores; Qdrant applies IDF

TOPIC_STATS_FILE = DATA_DIR / "topic_stats.jsonl"  # field-wide paper counts per topic and year

# Fields group topics on the site ("Coverage") and in the graph: (:Topic)-[:PART_OF]->(:Field).
LLM = "AI: language models"
AI = "AI: beyond language"
CS = "Computer science"
PHYSICS = "Physics"
MATH = "Math & statistics"

# Each topic: its field, a Semantic Scholar bulk-search query, the S2 field of study to
# filter on, and landmark seed papers that are always included (so lineage questions
# like "what built on RAG?" have anchors). fetch_papers.py takes the most cited arXiv
# papers per topic *per year*, so recent years aren't crowded out by older classics.
TOPICS: dict[str, dict] = {
    "Language model foundations": {
        "field": LLM, "fos": "Computer Science",
        "query": '"language model" + (pretraining | "instruction tuning" | "scaling laws")',
        "seeds": ["1706.03762", "1810.04805", "1910.10683", "2005.14165", "2203.02155", "2303.08774",
                  "2302.13971", "2307.09288", "2310.06825", "2106.09685", "2104.09864", "2004.05150",
                  "2205.14135"],
    },
    "Retrieval-augmented generation": {
        "field": LLM, "fos": "Computer Science",
        "query": '"retrieval-augmented generation"',
        "seeds": ["2002.08909", "2005.11401", "2007.01282", "2112.04426", "2208.03299", "2307.03172",
                  "2310.11511", "2312.10997", "2401.15884", "2401.18059", "2403.14403", "2309.15217"],
    },
    "Knowledge graphs + LLMs": {
        "field": LLM, "fos": "Computer Science",
        "query": '"knowledge graph" + ("large language model" | LLM)',
        "seeds": ["2404.16130", "2405.14831", "2410.05779"],
    },
    "LLM agents": {
        "field": LLM, "fos": "Computer Science",
        "query": '("LLM agent" | "language agent" | "autonomous agent") + ("large language model" | LLM)',
        "seeds": ["2201.11903", "2210.03629", "2302.04761", "2303.11366", "2304.03442", "2305.10601"],
    },
    "Dense retrieval": {
        "field": LLM, "fos": "Computer Science",
        "query": '"dense retrieval" | "passage retrieval"',
        "seeds": ["1908.10084", "2004.04906", "2004.12832", "2212.10496"],
    },
    "Long context": {
        "field": LLM, "fos": "Computer Science",
        "query": '"long context" + "language model"',
        "seeds": [],
    },
    "Hallucination": {
        "field": LLM, "fos": "Computer Science",
        "query": 'hallucination + ("large language model" | LLM)',
        "seeds": [],
    },
    "Computer vision": {
        "field": AI, "fos": "Computer Science",
        "query": '"object detection" | "semantic segmentation" | "image classification" | "vision transformer"',
        "seeds": ["1512.03385", "2010.11929", "2304.02643"],  # ResNet, ViT, Segment Anything
    },
    "Image generation": {
        "field": AI, "fos": "Computer Science",
        "query": '"diffusion model" | "text-to-image" | "image generation"',
        "seeds": ["2006.11239", "2112.10752"],  # DDPM, latent diffusion (Stable Diffusion)
    },
    "Multimodal models": {
        "field": AI, "fos": "Computer Science",
        "query": '"vision-language" | "multimodal large language model" | "visual question answering"',
        "seeds": ["2103.00020"],  # CLIP
    },
    "Reinforcement learning": {
        "field": AI, "fos": "Computer Science",
        "query": '"reinforcement learning"',
        "seeds": ["1312.5602", "1707.06347"],  # DQN, PPO
    },
    "Robotics": {
        "field": AI, "fos": "Computer Science",
        "query": 'robot + (learning | manipulation | navigation)',
        "seeds": [],
    },
    "Speech": {
        "field": AI, "fos": "Computer Science",
        "query": '"speech recognition" | "text-to-speech" | "speech synthesis"',
        "seeds": ["2006.11477", "2212.04356"],  # wav2vec 2.0, Whisper
    },
    "Graph neural networks": {
        "field": AI, "fos": "Computer Science",
        "query": '"graph neural network" | "graph convolutional network"',
        "seeds": ["1609.02907", "1710.10903"],  # GCN, GAT
    },
    "Alignment & interpretability": {
        "field": AI, "fos": "Computer Science",
        "query": '"AI alignment" | "AI safety" | "mechanistic interpretability" | "explainable AI"',
        "seeds": ["2212.08073", "2305.18290"],  # Constitutional AI, DPO
    },
    "Efficient ML": {
        "field": AI, "fos": "Computer Science",
        "query": '"model compression" | "knowledge distillation" | "network quantization" | "network pruning"',
        "seeds": ["1910.01108", "2210.17323", "2305.14314"],  # DistilBERT, GPTQ, QLoRA
    },
    "Security & privacy": {
        "field": CS, "fos": "Computer Science",
        "query": '"differential privacy" | "federated learning" | "adversarial attack" | "malware detection"',
        "seeds": [],
    },
    "Distributed systems": {
        "field": CS, "fos": "Computer Science",
        "query": '"distributed systems" | "cloud computing" | "serverless" | "distributed training"',
        "seeds": [],
    },
    "Databases": {
        "field": CS, "fos": "Computer Science",
        "query": '"query optimization" | "database systems" | "vector database" | "text-to-SQL"',
        "seeds": [],
    },
    "Code & software engineering": {
        "field": CS, "fos": "Computer Science",
        "query": '"code generation" | "program synthesis" | "software engineering"',
        "seeds": ["2107.03374"],  # Codex
    },
    "Algorithms & theory": {
        "field": CS, "fos": "Computer Science",
        "query": '"approximation algorithm" | "computational complexity" | "graph algorithm"',
        "seeds": [],
    },
    "Quantum computing": {
        "field": PHYSICS, "fos": "Physics",
        "query": '"quantum computing" | "quantum algorithm" | "quantum error correction"',
        "seeds": ["1910.11333"],  # quantum supremacy (Sycamore)
    },
    "Condensed matter": {
        "field": PHYSICS, "fos": "Physics",
        "query": 'superconductivity | "topological insulator" | "condensed matter"',
        "seeds": [],
    },
    "Astrophysics & cosmology": {
        "field": PHYSICS, "fos": "Physics",
        "query": 'cosmology | "dark matter" | "dark energy" | exoplanet',
        "seeds": ["1807.06209"],  # Planck 2018 cosmological parameters
    },
    "Particle physics": {
        "field": PHYSICS, "fos": "Physics",
        "query": '"Higgs boson" | "Large Hadron Collider" | "particle physics"',
        "seeds": ["1207.7214"],  # ATLAS Higgs discovery
    },
    "Gravitational waves": {
        "field": PHYSICS, "fos": "Physics",
        "query": '"gravitational waves" | "black hole merger"',
        "seeds": ["1602.03837"],  # GW150914
    },
    "Machine learning for physics": {
        "field": PHYSICS, "fos": "Physics",
        "query": '"physics-informed neural network" | "neural network quantum states" | "machine learning" + physics',
        "seeds": ["1606.02318", "1711.10561"],  # neural quantum states, PINNs
    },
    "Optimization": {
        "field": MATH, "fos": "Mathematics",
        "query": '"stochastic gradient descent" | "convex optimization" | "nonconvex optimization"',
        "seeds": ["1412.6980"],  # Adam
    },
    "Probability & stochastic processes": {
        "field": MATH, "fos": "Mathematics",
        "query": '"stochastic process" | "random matrix" | "Markov chain"',
        "seeds": [],
    },
    "Statistics & causal inference": {
        "field": MATH, "fos": "Mathematics",
        "query": '"causal inference" | "bayesian inference" | "conformal prediction"',
        "seeds": ["2107.07511"],  # conformal prediction tutorial
    },
}

SEED_ARXIV_IDS = [s for t in TOPICS.values() for s in t["seeds"]]
