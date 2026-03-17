#!/usr/bin/env bash
# build_standalone.sh — Creates viz/index_standalone.html with data inlined
# This version can be opened directly in a browser without a server.
set -euo pipefail
cd "$(dirname "$0")/.."

DATA_FILE="data/posts_with_coords.json"
HTML_FILE="viz/index.html"
OUTPUT="viz/index_standalone.html"

if [ ! -f "$DATA_FILE" ]; then
  echo "ERROR: $DATA_FILE not found. Run the pipeline first."
  exit 1
fi

if [ ! -f "$HTML_FILE" ]; then
  echo "ERROR: $HTML_FILE not found."
  exit 1
fi

echo "Building standalone HTML..."

# Use Python to handle the large JSON insertion (too big for shell variables)
python3 << 'PYEOF'
data_file = "data/posts_with_coords.json"
html_file = "viz/index.html"
output_file = "viz/index_standalone.html"

html = open(html_file).read()
data = open(data_file).read()

script_tag = '<script>window.__INLINE_DATA__ = ' + data + ';</script>'
marker = '<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>'
output = html.replace(marker, script_tag + '\n' + marker)

with open(output_file, 'w') as f:
    f.write(output)

import os
size = os.path.getsize(output_file)
print(f"Created {output_file} ({size:,} bytes)")
PYEOF
