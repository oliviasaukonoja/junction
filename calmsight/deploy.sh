#!/bin/bash
# One command: deploy the Calmsight brain to Modal and push to GitHub.
set -e
cd "$(dirname "$0")/brain"
python3 -m modal deploy calmsight_brain.py
URL="https://kristisaralidze--calmsight-brain-web.modal.run"
echo; echo "Health:"; curl -s "$URL/health"; echo
cd ../..
git add calmsight
git commit -m "Calmsight update $(date +%H:%M)" || true
git pull --rebase || true
git push || true
echo; echo "Test page:    $URL"
echo "Glasses page: $URL/glasses"
