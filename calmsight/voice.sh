#!/bin/bash
# Re-voice all StepCloser guide clips with the ElevenLabs coach voice (key stays in Modal).
set -e
cd "$(dirname "$0")/brain"
python3 -m modal run calmsight_brain.py::voice_stepcloser
echo "Done. Rebuild the Android app to include the new voice."
