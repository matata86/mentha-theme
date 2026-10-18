#!/bin/bash
# Vykreslí tapety Mentha Aurora (den/noc) přes headless Chrome do ~/Obrázky/Mentha/
set -euo pipefail
cd "$(dirname "$0")"
out="$HOME/Obrázky/Mentha"; mkdir -p "$out"
for m in day night; do
  sed "s/MODE/$m/" aurora.html > "/tmp/mentha-aurora-$m.html"
  google-chrome --headless=new --disable-gpu --hide-scrollbars --window-size=1920,1080 \
    --screenshot="$out/mentha-aurora-$m.png" "file:///tmp/mentha-aurora-$m.html" 2>/dev/null
  rm -f "/tmp/mentha-aurora-$m.html"
done
ls -la "$out"
