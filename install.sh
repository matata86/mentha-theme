#!/bin/bash
# Nasadí dist/Mentha-{Light,Dark} do ~/.themes a přimě GTK + Cinnamon načíst novou verzi.
# Nemění, který motiv je zvolený (to dělá applet auto-dark-light / gsettings).
set -euo pipefail
cd "$(dirname "$0")"

# ./install.sh --uninstall: odebere motiv i chevron ikony z hicolor
if [ "${1:-}" = "--uninstall" ]; then
  rm -rf "$HOME/.themes/Mentha-Light" "$HOME/.themes/Mentha-Dark"
  rm -f "$HOME"/.local/share/icons/hicolor/scalable/actions/mentha-chevron-{down,up,left,right}-symbolic.svg
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
  echo "odebráno: ~/.themes/Mentha-*, hicolor mentha-chevron-*"; exit 0
fi

# MENTHA_THEME: nasadit pod jiným názvem (paralelní kopie zdroje pro harness, viz tools/scene.sh)
name=${MENTHA_THEME:-Mentha}
for v in Light Dark; do
  src="dist/Mentha-$v"
  [ -f "$src/index.theme" ] || { echo "chybí $src, spusť ./build.sh" >&2; exit 1; }
  rsync -a --delete "$src/" "$HOME/.themes/$name-$v/"
done

# Obrysové chevrony (rozbalovací šipky): GTK3 bere GtkImage a expander šipky jen z ikonového motivu
# (-gtk-icontheme), proto jdou do hicolor (fallback každého ikonového motivu). Doc: dokumentace.md.
ICON_DST="$HOME/.local/share/icons/hicolor/scalable/actions"
mkdir -p "$ICON_DST"
for d in down up left right; do cp "src/gtk/assets/mentha-chevron-$d-symbolic.svg" "$ICON_DST/"; done
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

# reload: přepnout na chvíli jinam a zpět (GTK i Cinnamon shell čtou CSS jen při změně názvu)
reload() {
  local schema=$1 key=$2 tmp=$3 cur
  cur=$(gsettings get "$schema" "$key" | tr -d "'")
  case "$cur" in Mentha-*) gsettings set "$schema" "$key" "$tmp"; sleep 0.3; gsettings set "$schema" "$key" "$cur";; esac
}
# MENTHA_NORELOAD=1: jen zkopírovat (testy v Broadway načítají motiv při startu aplikace)
if [ -z "${MENTHA_NORELOAD:-}" ]; then
  reload org.cinnamon.desktop.interface gtk-theme Adwaita
  reload org.cinnamon.theme name ""
fi
echo "nasazeno do ~/.themes/$name-{Light,Dark}"
