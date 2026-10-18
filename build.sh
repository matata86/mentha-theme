#!/bin/bash
# Mentha: postaví dist/Mentha-{Light,Dark} ze src/tokens.json + upstream (Orchis, Mint-Y 2.3.8).
# Použití: ./build.sh            (akcent z tokens.json)
#          MENTHA_ACCENT=blue ./build.sh
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$PWD/build/bin:$PATH"

python3 build/gen-tokens.py "${MENTHA_ACCENT:-}"
for part in gtk shell libadwaita; do
  echo "== $part"
  bash "build/$part.sh"
done
echo "hotovo: $(ls -d dist/Mentha-*)"
