# PaperWeave frontend

Next.js 16 app for [PaperWeave](../README.md):
- **`/`:** home page with example questions
- **`/ask?q=...`:** streaming agent steps, cited answer and graph view
- **`/paper/[id]`:** paper card and citation graph

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL points at the FastAPI backend
npm install
npm run dev                  # http://localhost:3000
npm run lint && npm run build
```

`public/examples.json` holds saved answers for the example questions. They are served without the backend, so the demo works while the free-tier server sleeps. Regenerate them with `backend/scripts/export_examples.py`.
