"""Run the example questions through the agent and save the answers for the frontend.

The frontend serves these from frontend/public/examples.json without calling the backend,
so the demo works instantly even while the free-tier server is asleep. Events use the same
shape as the /api/chat stream. Re-run after changing the agent or switching LLM provider
(Groq answers are much better than a local 4B model's).

    python scripts/export_examples.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import llm  # noqa: E402
from app.agent.graph import run  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "examples.json"

QUESTIONS = [
    "What improved on RAG, and which datasets did those papers use?",
    "Compare GraphRAG, RAPTOR and HippoRAG",
    "Which papers in the corpus build on Attention Is All You Need?",
    "Compare Self-RAG and Corrective RAG",
    "Which papers evaluate on HotpotQA, and what do they propose?",
    "What are the most cited papers on hallucination since 2023?",
    "How does HyDE improve zero-shot dense retrieval?",
    "What are the latest papers on agent memory?",
    "Compare ReAct and Reflexion",
    "Which authors wrote the most papers in the corpus?",
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    examples = []
    for n, question in enumerate(QUESTIONS, 1):
        start = time.perf_counter()
        state = run(question)
        examples.append({
            "question": question,
            "events": [{"event": "step", "data": s} for s in state["steps"]] + [
                {"event": "answer", "data": {"text": state["answer"]}},
                {"event": "citations", "data": state["citations"]},
                {"event": "subgraph", "data": state["subgraph"]},
            ],
        })
        print(f"[{n}/{len(QUESTIONS)}] {time.perf_counter() - start:.0f}s  {question}", flush=True)
        # Write after each question so a crash keeps the finished ones.
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": ", ".join(llm.provider_names()),
            "examples": examples,
        }, indent=1), encoding="utf-8")
    print(f"Wrote {len(examples)} examples to {OUT}")


if __name__ == "__main__":
    main()
