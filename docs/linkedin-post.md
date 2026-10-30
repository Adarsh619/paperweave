# LinkedIn post draft

> Draft. Fill in the live demo link after deploying, and attach a short screen recording of an answer streaming in with its graph.

---

I built **PaperWeave**, a research assistant that shows how AI research connects. 🕸️

Ask it something like *"What improved on RAG, and which datasets did those papers use?"* and it doesn't just search for matching text. A LangGraph agent:

1️⃣ plans the question (lineage? comparison? latest work?)
2️⃣ queries a **Neo4j knowledge graph** of 500 influential AI/LLM papers, plus hybrid vector search (Qdrant) and live arXiv
3️⃣ checks whether the evidence is enough, and retries with a better query if not
4️⃣ writes a cited answer, **verifies every arXiv ID** against what it retrieved, and shows the graph behind it

**Why a graph?** Plain vector RAG finds papers that *sound like* your question. It can't follow "method A improves on method B, which was evaluated on dataset C". On 30 golden questions, the agent got **EVAL_MULTIHOP** of the needed papers into context on multi-hop questions, versus **EVAL_MULTIHOP_BASELINE** for vector-only RAG.

What I learned building it:
🔹 Small local LLMs are great for **offline extraction**. A 4B model on my laptop GPU extracted methods, datasets and tasks from 500 abstracts in under an hour. Cleaning the names (merging "RAG", "Retrieval-Augmented Generation" and "retrieval augmented generation (RAG)") mattered as much as the model.
🔹 For agents, **let the LLM plan and let code pick the tools.** That was far more reliable than open-ended tool calling.
🔹 **Never trust a citation you didn't check.** The model garbled arXiv IDs, so a validator repairs or drops them.
🔹 LLM-written Cypher runs behind a read-only guard **and** in a read-only transaction. Defense in depth.

The stack runs 24/7 on free tiers: Next.js on Vercel, FastAPI + LangGraph on Render, Neo4j AuraDB, Qdrant Cloud, Groq.

🔗 Live demo: LINK
💻 Code: https://github.com/Adarsh619/paperweave

#RAG #GraphRAG #LLM #LangGraph #Neo4j #AIEngineering #FullStack
