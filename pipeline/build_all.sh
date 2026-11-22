#!/usr/bin/env bash
# Rebuild the whole snapshot and load it locally, unattended. Every step resumes where it
# stopped (search cache, append-only extraction), so just re-run this after an interruption.
#
#   bash pipeline/build_all.sh            # from the repo root; needs Docker + Ollama running
set -euo pipefail
cd "$(dirname "$0")"
PY=../.venv/Scripts/python
[ -x "$PY" ] || PY=../.venv/bin/python

step() { echo; echo "=== $(date '+%H:%M') $1"; }

step "fetch papers (~10K, cached per topic-year)"
$PY -u fetch_papers.py --max-papers 10000
step "fetch citations"
$PY -u fetch_citations.py
step "extract entities with Ollama (the long one: ~6-11 s per new paper)"
$PY -u extract_entities.py
step "normalize entity names"
$PY -u normalize.py
step "load Neo4j + Qdrant from the snapshot"
$PY -u rebuild.py --fresh
step "export coverage stats for the website"
$PY -u export_stats.py
step "checks"
$PY -u check_graph.py
$PY -u check_search.py
echo; echo "=== $(date '+%H:%M') done"
