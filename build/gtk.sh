#!/usr/bin/env bash
# Mentha: GTK2 + GTK3 + GTK4 -> dist/Mentha-{Light,Dark}/{gtk-2.0,gtk-3.0,gtk-4.0}
# Orchis (kopie v build/work/gtk) + přebarvení z tokenů + vrstva src/gtk/_mentha-gtk.scss.
# Idempotentní; volitelně MENTHA_ACCENT=<klíč z tokens.json accents>.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PATH="$ROOT/build/bin:$PATH"
UP=upstream/Orchis-theme/src
W=build/work/gtk
SASSC="sassc -t expanded"

python3 build/gen-tokens.py ${MENTHA_ACCENT:+"$MENTHA_ACCENT"} >/dev/null

# ---- 1) pracovní kopie Orchisu (upstream zůstává read-only) ------------------
rm -rf "$W"
mkdir -p "$W"
cp -r "$UP/_sass" "$UP/gtk" "$UP/gtk-2.0" "$W/"

# ---- 2) tweaks-temp jako install.sh/core.sh: default corner 12px, theme default,
#         solid opacity, bez mac stylu; check/radio v barvě akcentu (ne zelená)
cp "$W/_sass/_tweaks.scss" "$W/_sass/_tweaks-temp.scss"
sed -i "/\$opacity:/s/default/solid/; /\$check_radio:/s/default/primary/" "$W/_sass/_tweaks-temp.scss"

# ---- 3) tokeny + Mentha SCSS dovnitř, přepsání Orchisových proměnných --------
cp build/gen/_mentha-tokens.scss src/gtk/_mentha-palette.scss src/gtk/_mentha-variables.scss \
   src/gtk/_mentha-gtk.scss "$W/_sass/"
printf "\n// --- Mentha ---\n@import 'mentha-variables';\n" >> "$W/_sass/_variables.scss"
printf "\n// --- Mentha ---\n@import 'mentha-palette';\n"   >> "$W/_sass/_colors.scss"

# ---- 4) PNG jezdce (modré) -> CSS kreslený jezdec: vyřadit url(*.png) ze scale slideru
python3 - "$W/_sass/gtk/_common-3.20.scss" "$W/_sass/gtk/_common-4.0.scss" <<'PY'
import re, sys
pat = re.compile(r"-gtk-scaled\(url\('#\{\$_(?:url|scale_asset)\}\.png'\),\s*url\('#\{\$_(?:url|scale_asset)\}@2\.png'\)\),\s*")
for f in sys.argv[1:]:
    s = open(f).read()
    s, n = pat.subn("", s)
    open(f, "w").write(s)
    print(f"  {f}: {n} slider PNG url odstraněno")
PY

# ---- 5) vstupní scss: Orchisův gtk-{Light,Dark}.scss + $gtk + vrstva na konec -
mk_entry() { # <gtk 3|4> <Light|Dark>
  local d="$W/gtk/$1.0"
  { echo "\$gtk: $1;"; cat "$d/gtk-$2.scss"; echo "@import '../../_sass/mentha-gtk';"; } > "$d/mentha-$2.scss"
}
for v in 3 4; do for c in Light Dark; do mk_entry $v $c; done; done

compile() { # <3|4> <Light|Dark>; deprecation varování dart-sassu jdou do logu, chyby na stderr
  $SASSC "$W/gtk/$1.0/mentha-$2.scss" "$W/gtk/$1.0/out-$2.css" 2>"$W/sass-$1-$2.log" \
    || { cat "$W/sass-$1-$2.log" >&2; return 1; }
}
pids=()
for v in 3 4; do for c in Light Dark; do compile $v $c & pids+=($!); done; done
for p in "${pids[@]}"; do wait "$p" || { echo "FAIL: sass kompilace" >&2; exit 1; }; done
for f in 3.0/out-Light 3.0/out-Dark 4.0/out-Light 4.0/out-Dark; do
  [ -s "$W/gtk/$f.css" ] || { echo "FAIL: $f.css prázdné/chybí" >&2; exit 1; }
done

# ---- 5b) gtk-4.0: upstream Orchis dává do CSS věci, které GTK 4.14 neparsuje
#          (:root s neinterpolovanými $proměnnými, color-mix, var(--libadwaita)); bez úpravy upstreamu
python3 - "$W/gtk/4.0/out-Light.css" "$W/gtk/4.0/out-Dark.css" <<'PY'
import re, sys
mix = re.compile(r"color-mix\(in srgb,\s*(#[0-9A-Fa-f]{6})\s+(\d+)%,\s*transparent\)")
def rgba(m):
    h = m.group(1)[1:]
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {int(m.group(2)) / 100:g})"
for f in sys.argv[1:]:
    s = open(f).read()
    s = re.sub(r"^:root \{.*?^\}\n", "", s, count=1, flags=re.S | re.M)   # --blue-1: $blue_1 ...
    s = mix.sub(rgba, s)
    # zbylé bloky (libadwaita app-specific) s color-mix/var(--) zahodit celé
    s = re.sub(r"[^{}]*\{[^{}]*(?:color-mix\(|var\(--)[^{}]*\}\n?", "", s)
    open(f, "w").write(s)
    print(f"  {f}: gtk-4.0 očištěno")
PY

# ---- 6) assety ---------------------------------------------------------------
# GTK3/4: symbolické SVG (neutrální, recolor řídí GTK barvou) + recolor PNG selection-mode
# Muffin/titlebutton: assety minimize/maximize/close se používají jen v mac stylu (vypnut).
build_variant() { # <Light|Dark> <light|dark> <Dark suffix pro gtk-2.0: ''|-Dark> <png suffix>
  local name="Mentha-$1" var="$2" g2="$3"
  local D="dist/$name"
  mkdir -p "$D"
  rm -rf "$D/gtk-2.0" "$D/gtk-3.0" "$D/gtk-4.0"

  for v in 3 4; do
    mkdir -p "$D/gtk-$v.0/assets"
    cp -r "$W/gtk/scalable" "$D/gtk-$v.0/assets/scalable"
    cp "$W/gtk/$v.0/out-$1.css" "$D/gtk-$v.0/gtk.css"
    cp "$W/gtk/$v.0/out-Dark.css" "$D/gtk-$v.0/gtk-dark.css"
    cp src/gtk/assets/*.svg "$D/gtk-$v.0/assets/"   # vlastní symbolické glyfy check/radio
  done
  # GTK3 PNG s akcentem (selection-mode checkbox, row-selected v gnome sidebaru): light sada tokeny
  # tohoto variantu, -dark sada tmavými tokeny (kvůli gtk-dark.css)
  local stage="$W/stage-selmode"
  rm -rf "$stage"; mkdir -p "$stage" "$D/gtk-3.0/assets"
  cp "$W/gtk/assets"/selectionmode-checkbox*.png "$W/gtk/assets"/row-selected{,-light,-dark}{,@2}.png "$stage/"
  python3 build/gtk-recolor.py png "$var"  "$stage" "$D/gtk-3.0/assets"
  mkdir -p "$stage-dark"; rm -f "$stage-dark"/*
  cp "$stage"/*-dark*.png "$stage-dark/"
  python3 build/gtk-recolor.py png dark "$stage-dark" "$D/gtk-3.0/assets"

  cp "$D/gtk-3.0/assets"/row-selected*.png "$D/gtk-4.0/assets/"   # GTK4 gnome sidebar

  # GTK2: Orchisovy gtkrc + PNG přebarvené na akcent
  mkdir -p "$D/gtk-2.0/assets"
  cp "$W/gtk-2.0/common/"{apps.rc,hacks.rc,main.rc} "$D/gtk-2.0/"
  python3 build/gtk-recolor.py rc "$var" "$W/gtk-2.0/gtkrc$g2" "$D/gtk-2.0/gtkrc"
  python3 build/gtk-recolor.py png "$var" "$W/gtk-2.0/assets-folder/assets-common$g2" "$D/gtk-2.0/assets"
  python3 build/gtk-recolor.py png "$var" "$W/gtk-2.0/assets-folder/assets$g2"        "$D/gtk-2.0/assets"

  sed -i '/^MetacityTheme=/d' "$D/index.theme" 2>/dev/null || true   # metacity-1 part zatím neexistuje
  if [ ! -e "$D/index.theme" ]; then
    local icon="Papirus"; [ "$var" = dark ] && icon="Papirus-Dark"
    cat > "$D/index.theme" <<EOT
[Desktop Entry]
Type=X-GNOME-Metatheme
Name=$name
Comment=Mentha desktop theme ($var)
Encoding=UTF-8

[X-GNOME-Metatheme]
GtkTheme=$name
IconTheme=$icon
CursorTheme=Bibata-Modern-Classic
ButtonLayout=:minimize,maximize,close
EOT
  fi
}
build_variant Light light ""
build_variant Dark  dark  "-Dark"

python3 build/gtk-validate.py
echo "OK: dist/Mentha-{Light,Dark}/{gtk-2.0,gtk-3.0,gtk-4.0}"
