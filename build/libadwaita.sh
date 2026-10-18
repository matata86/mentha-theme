#!/usr/bin/env bash
# Mentha: libadwaita recolor -> dist/Mentha-{Light,Dark}/libadwaita-{1.5,1.7}/
# Volitelně: MENTHA_ACCENT=<akcent z src/tokens.json>
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 build/gen-tokens.py ${MENTHA_ACCENT:+"$MENTHA_ACCENT"}   # vždy: výstup závisí jen na vstupech

python3 build/libadwaita-recolor.py build
python3 build/libadwaita-recolor.py check
