#!/bin/bash
# Spustí GTK aplikaci v izolovaném Broadway displeji (neviditelné, neruší plochu uživatele).
# Použití: tools/scene.sh <Light|Dark> <N> <příkaz...>   -> web na http://127.0.0.1:$((8080+N))/
#          tools/scene.sh stop <N>
# Motiv bere z ~/.themes (nejdřív ./install.sh). Ikony Papirus, písmo Inter 10 (cílový stav).
# GTK4/libadwaita aplikace: MENTHA_GTK4=1 tools/scene.sh ... (daemon gtk4-broadwayd stažený
#   tools/fetch-gtk4-broadwayd.sh do ~/.cache/mentha-qa, protože libgtk-4-bin není nainstalován; stejná adresa :N / web 8080+N).
# GSETTINGS_BACKEND=memory: aplikace v testu nesmí zapisovat do skutečného dconf uživatele.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
if [ "$1" = stop ]; then
  pkill -f "^broadwayd :$2\b" || true
  pkill -f "gtk4-broadwayd :$2\b" || true
  pkill -f "BROADWAY_DISPLAY=:$2 " || true
  # aplikace běží ve vlastní skupině procesů (setsid) -> zabít celou, i potomky dbus-run-session
  [ -f "/tmp/mentha-scene-$2.pgid" ] && { kill -- "-$(cat /tmp/mentha-scene-$2.pgid)" 2>/dev/null || true; rm -f "/tmp/mentha-scene-$2.pgid"; }
  exit 0
fi
variant=$1 n=$2; shift 2
# MENTHA_THEME: jiný název instalace (paralelní kopie zdroje, např. Mentha-r8nemo -> ~/.themes/Mentha-r8nemo-Light)
theme=${MENTHA_THEME:-Mentha}
icons=Papirus; [ "$variant" = Dark ] && icons=Papirus-Dark
cfg=$(mktemp -d /tmp/mentha-scene-XXXX)
mkdir -p "$cfg/gtk-3.0" "$cfg/gtk-4.0"
for d in gtk-3.0 gtk-4.0; do
  printf '[Settings]\ngtk-theme-name=$theme-%s\ngtk-icon-theme-name=%s\ngtk-font-name=Inter 10\ngtk-application-prefer-dark-theme=%s\n' \
    "$variant" "$icons" "$([ "$variant" = Dark ] && echo 1 || echo 0)" > "$cfg/$d/settings.ini"
done
if [ "${MENTHA_GTK4:-0}" = 1 ]; then
  g4=$("$here/fetch-gtk4-broadwayd.sh")   # verze shodná se systémovým GTK 4.14 (jinak prázdné okno)
  [ -x "$g4" ] || { echo "gtk4-broadwayd nenalezen" >&2; exit 2; }
  pgrep -f "gtk4-broadwayd :$n\b" >/dev/null || { "$g4" ":$n" >/dev/null 2>&1 & sleep 1; }
else
  pgrep -f "^broadwayd :$n\b" >/dev/null || { broadwayd ":$n" >/dev/null 2>&1 & sleep 0.8; }
fi
scheme=default; [ "$variant" = Dark ] && scheme=prefer-dark
# Izolovaná session-bus smí aktivovat jen gvfs. Portály/keyring/Nextcloud/GPaste/kdeconnect by se jinak spouštěly
# (a xdg-desktop-portal čeká 25 s na org.freedesktop.secrets -> aplikace se otevírají ~13 s).
dbc="$HOME/.cache/mentha-qa/dbus"; mkdir -p "$dbc/services"
# Metadata záměrně NEzpřístupnit: gvfsd-metadata by zapisoval pohled/zoom složek (Nemo) do skutečného ~/.local/share/gvfs-metadata uživatele.
rm -f "$dbc/services/"*.service
for f in /usr/share/dbus-1/services/org.gtk.vfs.*.service; do case "$f" in *Metadata*) ;; *) ln -sf "$f" "$dbc/services/";; esac; done
cat > "$dbc/session.conf" <<EOC
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig><type>session</type><keep_umask/><listen>unix:tmpdir=/tmp</listen>
<servicedir>$dbc/services</servicedir>
<policy context="default"><allow send_destination="*" eavesdrop="true"/><allow eavesdrop="true"/><allow own="*"/></policy></busconfig>
EOC
# GTK4/libadwaita: GTK_THEME by načetl gtk-4.0 (Orchis) + Adwaitu místo naší libadwaita-1.5 (Mint patch čte název motivu z gsettings,
# v izolované session by vyšel Mint-Y-Aqua) -> motiv předat přes ADW_DEBUG_THEME_NAME a nechat si ho potvrdit v app.log (ADW_DEBUG_THEMES).
if [ "${MENTHA_GTK4:-0}" = 1 ]; then themeenv=(ADW_DEBUG_THEME_NAME="${ADW_DEBUG_THEME_NAME:-$theme-$variant}" ADW_DEBUG_THEMES=1); else themeenv=(GTK_THEME="$theme-$variant"); fi
setsid nohup dbus-run-session --config-file="$dbc/session.conf" -- env GDK_BACKEND=broadway BROADWAY_DISPLAY=":$n" \
  GSETTINGS_BACKEND=memory GTK_USE_PORTAL=0 GDK_DEBUG=no-portals NO_AT_BRIDGE=1 "${themeenv[@]}" XDG_CONFIG_DIRS="$cfg:/etc/xdg" ADW_DEBUG_COLOR_SCHEME="$scheme" \
  "$@" >"$cfg/app.log" 2>&1 &
echo $! > "/tmp/mentha-scene-$n.pgid"
echo "scene :$n ($variant) -> http://127.0.0.1:$((8080+n))/  log $cfg/app.log"
