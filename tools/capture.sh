#!/bin/bash
# Reprodukovatelná sada snímků pro UX audit motivu Mentha. Použití: tools/capture.sh <outdir> [--only REGEX] [--variant light|dark]
# MENTHA_DISPLAY (výchozí 7) = číslo Broadway displeje; vždy po sobě zastaví scénu. Podrobnosti: tools/capture.py.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
export MENTHA_DISPLAY=${MENTHA_DISPLAY:-7}
trap '"$here/scene.sh" stop "$MENTHA_DISPLAY" >/dev/null 2>&1 || true' EXIT
python3 "$here/capture.py" "$@"
