#!/usr/bin/env bash
# deploy.sh — Deploy the visualization
# Currently supports GitHub Pages deployment via the viz/ directory.
#
# For Vercel: Run `npx vercel viz/` from the project root.
# For Netlify: Point the deploy directory to `viz/`.
#
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== EFE Embedding Map — Deploy ==="
echo ""

# Ensure data is copied
if [ ! -f "viz/posts_with_coords.json" ]; then
  echo "Copying data to viz/..."
  cp data/posts_with_coords.json viz/posts_with_coords.json
fi

# Build standalone version
bash deploy/build_standalone.sh

echo ""
echo "Deployment files ready in viz/:"
ls -lh viz/
echo ""
echo "To deploy:"
echo "  GitHub Pages: Push viz/ contents to gh-pages branch"
echo "  Vercel:       npx vercel viz/"
echo "  Netlify:      Set deploy dir to viz/"
echo "  Manual:       Upload viz/ contents to any static host"
