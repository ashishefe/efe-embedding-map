#!/bin/bash
set -e
echo "Running all verification agents..."
for phase in 1 2 3 4 5 6; do
    echo ""
    echo "━━━ Phase $phase ━━━"
    python verify/verification_phase${phase}.py
done
echo ""
echo "All phases verified ✓"
