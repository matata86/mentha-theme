#!/usr/bin/env bash
# Mentha: Cinnamon shell téma -> dist/Mentha-{Light,Dark}/cinnamon/ (+ index.theme, pokud chybí)
# Vše se regeneruje z upstream/mint-themes (Mint-Y/cinnamon) + src/cinnamon + src/tokens.json.
# Použití: bash build/shell.sh            (akcent z tokens.json)
#          MENTHA_ACCENT=<akcent> bash build/shell.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT=$PWD
export PATH="$ROOT/build/bin:$PATH"

UP="upstream/mint-themes/src/Mint-Y/cinnamon"
SRC="src/cinnamon"
WORK="build/work/shell"

[[ -d "$UP/sass" ]] || { echo "chybí $UP/sass" >&2; exit 1; }

# 1) tokeny (vždy, ať výstup závisí jen na vstupech)
python3 build/gen-tokens.py ${MENTHA_ACCENT:+"$MENTHA_ACCENT"}

# 2) pracovní kopie upstream sass + Mentha paleta + vrstva
rm -rf "$WORK"
mkdir -p "$WORK"
cp -r "$UP/sass" "$WORK/sass"
cp "$SRC/_colors.scss" "$SRC/_mentha-shell.scss" build/gen/_mentha-tokens.scss "$WORK/sass/"
# upstream překlep (tranparentize) -> transparentize
sed -i 's/tranparentize(/transparentize(/g' "$WORK/sass/_dialogs.scss"
# vrstva Mentha se importuje jako poslední (po _deprecated)
for f in cinnamon cinnamon-dark; do
  grep -q '_mentha-shell' "$WORK/sass/$f.scss" || printf '\n@import "_mentha-shell";\n' >> "$WORK/sass/$f.scss"
done

build_variant() {  # $1=light|dark  $2=Light|Dark  $3=scss vstup
  local v="$1" V="$2" scss="$3" out="dist/Mentha-$2/cinnamon"
  rm -rf "$out"
  mkdir -p "$out"
  sassc "$WORK/sass/$scss.scss" "$WORK/$v.raw.css"
  python3 "$SRC/postprocess.py" "$WORK/$v.raw.css" "$out/cinnamon.css"
  python3 "$SRC/gen-assets.py" "$v" "$out"
  if [[ ! -f "dist/Mentha-$V/index.theme" ]]; then
    local icon=Papirus; [[ $v == dark ]] && icon=Papirus-Dark
    cat > "dist/Mentha-$V/index.theme" <<THEME
[Desktop Entry]
Type=X-GNOME-Metatheme
Name=Mentha-$V
Comment=Mentha desktop theme ($V)
Encoding=UTF-8

[X-GNOME-Metatheme]
GtkTheme=Mentha-$V
MetacityTheme=Mentha-$V
IconTheme=$icon
CursorTheme=Bibata-Modern-Classic
ButtonLayout=:minimize,maximize,close
THEME
  fi
}

build_variant light Light cinnamon
build_variant dark  Dark  cinnamon-dark

# 3) validace: zelená z Mint-Y, rozbité url(), nepodporovaná syntaxe barev
fail=0
for V in Light Dark; do
  d="dist/Mentha-$V/cinnamon"; css="$d/cinnamon.css"
  if grep -niE '#35a854|53a854|#2e8b57|#3eb15c|#4ac26b|#2d9a4b' "$css" "$d"/*-assets -r >/dev/null 2>&1; then
    echo "[$V] zůstala Mint-Y zelená:" >&2; grep -niE '#35a854|#2e8b57|#3eb15c|#4ac26b|#2d9a4b' -r "$css" "$d"/*-assets | head >&2; fail=1
  fi
  while IFS= read -r u; do
    [[ -f "$d/$u" ]] || { echo "[$V] chybí asset: $u" >&2; fail=1; }
  done < <(grep -o 'url("[^"]*")' "$css" | sed 's/url("//;s/")$//' | sort -u)
  if grep -nE 'rgba?\([^)]*(/|%)' "$css" >/dev/null; then echo "[$V] rgb() s % nebo /" >&2; fail=1; fi
  if grep -nE 'linear-gradient|backdrop-filter|text-transform|[^-]opacity:' "$css" | grep -v 'StIcon' >/dev/null; then
    echo "[$V] nepodporovaná St vlastnost:" >&2; grep -nE 'linear-gradient|backdrop-filter|text-transform|[^-]opacity:' "$css" | head >&2; fail=1
  fi
done
[[ $fail == 0 ]] || { echo "shell.sh: validace SELHALA" >&2; exit 1; }
echo "shell: OK -> $(ls -d dist/Mentha-*/cinnamon | tr '\n' ' ')"
