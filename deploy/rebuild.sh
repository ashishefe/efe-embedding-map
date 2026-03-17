#!/usr/bin/env bash
# rebuild.sh — Re-runs the full EFE Embedding Map pipeline
# Usage: bash deploy/rebuild.sh
#
# Requires:
#   - Python 3.10+ with venv at .venv/
#   - GEMINI_API_KEY set in .env
#
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== EFE Embedding Map — Full Rebuild ==="
echo ""

# Activate virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

# Check for API key
if ! grep -q "GEMINI_API_KEY" .env 2>/dev/null; then
  echo "ERROR: .env file must contain GEMINI_API_KEY"
  exit 1
fi

echo "--- Phase 1: Scraping ---"
python scrape/scrape_wordpress.py
python scrape/scrape_substack.py
python scrape/merge_and_dedup.py
python verify/verification_phase1.py
echo ""

echo "--- Phase 2: Embeddings + UMAP + Clustering ---"
python embed/generate_embeddings.py
python embed/run_umap.py
python embed/cluster_and_label.py
python embed/generate_journeys.py
python verify/verification_phase2.py
echo ""

echo "--- Copying data to viz/ ---"
cp data/posts_with_coords.json viz/posts_with_coords.json
echo ""

echo "--- Building standalone version ---"
bash deploy/build_standalone.sh
echo ""

echo "--- Running all verifications ---"
python verify/verification_phase3.py
python verify/verification_phase4.py
python verify/verification_phase5.py
python verify/verification_phase6.py
echo ""

echo "=== Rebuild complete ==="
echo "Open viz/index.html with a local server, or viz/index_standalone.html directly."
