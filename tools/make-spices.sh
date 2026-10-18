#!/bin/bash
# Připraví podklady pro cinnamon-spices-themes: dist-spices/<UUID>/{info.json,README.md,screenshot.png,files/<UUID>/...}
# z dist/Mentha-{Light,Dark} (nejdřív ./build.sh, modrý akcent). Do PR kopírovat obsah dist-spices/.
# Spices README nesmí odkazovat na stažení variant mimo Spices, proto je krátké a bez odkazu na build.
set -euo pipefail
cd "$(dirname "$0")/.."
out=dist-spices; rm -rf "$out"
for v in Light Dark; do
  u=Mentha-$v; [ -f "dist/$u/index.theme" ] || { echo "chybí dist/$u, spusť ./build.sh" >&2; exit 1; }
  lc=$(echo "$v" | tr 'A-Z' 'a-z')
  mkdir -p "$out/$u/files"
  rsync -a "dist/$u/" "$out/$u/files/$u/"
  cp "docs/screenshots/spices-$lc.png" "$out/$u/screenshot.png"
  cat > "$out/$u/info.json" <<J
{
	"author": "matata86",
	"name": "$u",
	"description": "Mentha ($lc) is a calm, modern blue theme with rounded geometry, flat buttons and switches, and gradients only on level and progress bars. It includes Cinnamon, GTK 2, GTK 3 and GTK 4/libadwaita themes and is tuned for Cinnamon 6.x.",
	"license": "GPL-3.0"
}
J
  cat > "$out/$u/README.md" <<R
# $u

A calm, modern blue theme for Cinnamon ($lc variant): rounded geometry, flat buttons and switches,
gradients only on level and progress bars. Includes Cinnamon shell, GTK 2, GTK 3 and GTK 4 / libadwaita
(1.5 and 1.7) themes, tuned for Cinnamon 6.x on Linux Mint 22.

Pair it with the Papirus icon theme and Bibata cursors for the intended look (the theme works with any icons).

Based on Orchis (Vince Liuice) and Mint-Y (Linux Mint), both GPL-3.0.

Support the author: [ko-fi.com/matata86](https://ko-fi.com/matata86)
R
done
find "$out" -type f | wc -l | sed 's/^/souborů: /'; du -sh "$out"
