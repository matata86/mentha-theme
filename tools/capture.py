#!/usr/bin/env python3
"""Reprodukovatelná sada snímků GTK vrstvy motivu Mentha (Light + Dark) pro UX audit.

Použití: tools/capture.sh <outdir> [--only REGEX] [--variant light|dark]
  MENTHA_DISPLAY=N  Broadway display (výchozí 7), web na 127.0.0.1:8080+N
Výstup: <outdir>/{light,dark}/<NN>-<scena>.png (+ výřezy <NN>-<scena>--<detail>@2x.png),
        <outdir>/manifest.json, <outdir>/checks.json (slepé snímky, test načtení motivu),
        <outdir>/logs/<variant>/<NN>-<scena>.log (varování GTK z app.log).
Pořadí a číslování scén je stabilní (index v SCENES); --only filtruje podle REGEX nad "<NN>-<scena>" nebo aplikací.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
HOME = os.path.expanduser("~")
FIX = os.path.join(HOME, ".cache", "mentha-qa", "fixtures")
DEEP = os.path.join(HOME, "System", "FNS projekty", "AAA_CLAUDE", "Infrastruktura", "Asus")
W, H = 1400, 1000
# GTK4 aplikace, které sice linkují libadwaita, ale nevolají adw_init (GtkApplication) -> libadwaita motiv nenačítají, vzhled dělá gtk-4.0
NO_ADW_INIT = {"simple-scan"}


# ---------------------------------------------------------------- kroky cdp.py
def click(x, y): return {"click": [x, y]}
def rclick(x, y): return {"rclick": [x, y]}
def move(x, y): return {"move": [x, y]}
def scroll(x, y, dy): return {"scroll": [x, y, dy]}
def key(k): return {"key": k}
def wait(ms): return {"wait": ms}
def typ(t): return {"type": t}


SHOT = {"shot": "@"}          # zástupce: kam se uloží hlavní snímek (výchozí na konci scény)


class Scene:
    def __init__(self, sid, app, tags, desc, cmd, steps=(), crops=(), gtk4=False, maxwin=True, pre=1500, settle=1500):
        self.sid, self.app, self.tags, self.desc, self.cmd = sid, app, tags, desc, cmd
        self.steps, self.crops, self.gtk4, self.maxwin, self.pre, self.settle = list(steps), list(crops), gtk4, maxwin, pre, settle


def gallery(page, desc, tags, steps=(), crops=(), pre=2800, maxwin=True, sid=None):
    return Scene(sid or f"gal-{page}", "gallery3", tags, desc, ["python3", os.path.join(TOOLS, "gallery3.py"), "--page", page],
                 steps, crops, maxwin=maxwin, pre=300, settle=pre)


def nemo(sid, desc, steps=(), crops=(), path=None, tags=("nemo",), maxwin=True, pre=1800, settle=1800):
    return Scene(sid, "nemo", list(tags), desc, ["nemo", "--no-desktop", path or HOME], steps, crops, maxwin=maxwin, pre=pre, settle=settle)


# výřezy Nemo (souřadnice z maximalizovaného okna 1400x1000)
NEMO_TOOLBAR = ("toolbar-pathbar", (0, 66, 640, 40))
NEMO_SIDEBAR = ("sidebar", (0, 105, 172, 600))  # včetně Souborového systému a disk baru
NEMO_STATUS = ("statusbar", (900, 962, 500, 38))

GENERIC_MENU = [click(34, 50), wait(500)]

SCENES = [
    # --- galerie GTK3 (jedna stránka = jedno okno)
    gallery("buttons", "Tlačítka: běžná, suggested/destructive, flat, linked, toggle, kruhová, menu; vynucené stavy", ["controls"]),
    gallery("entries", "Entry, search, spin, combo, progress v entry; stavy normal/focus/disabled/error", ["controls"]),
    gallery("toggles", "Check, radio, switch, scale, progressbar, levelbar, spinner", ["controls"]),
    gallery("spin", "GtkSpinner 16/32/96 px (vlastní ikona kroužek + oblouk)", ["controls"]),
    gallery("upd", "Hlavní okno mintUpdate: rámeček s TreeView nad notebookem", ["lists"]),
    gallery("hist", "Okno Historie aktualizací (mintUpdate): rámeček scrolledwindow s TreeView", ["lists"]),
    gallery("lists", "TreeView, ListBox, PlacesSidebar, Nemo-like sidebar, IconView", ["lists", "controls"]),
    gallery("containers", "Notebook, Frame, Expander, InfoBar, Paned, scrollbary", ["controls", "chrome"]),
    gallery("headerbar", "HeaderBar: titulek+podtitulek, StackSwitcher, MenuButton, search, linked", ["chrome", "controls"]),
    gallery("popovers", "Otevřené Gtk.Popover s obsahem a popover menu (submenu, model)", ["menus", "controls"], pre=3000),
    gallery("menus", "Menubar + otevřené menu Soubor se submenu (check/radio/accelerátory/oddělovače)", ["menus"],
            steps=[click(34, 50), wait(400), key("Down"), key("Down"), key("Down"), key("Right"), wait(700)]),
    gallery("menus", "Kontextové menu (pravý klik)", ["menus"], sid="gal-menus-context", steps=[rclick(700, 500), wait(500)]),
    gallery("typography", "Typografie: nadpisy, mono, odkazy, selectable, tooltip", ["typography", "controls"]),
    gallery("dlg-message", "MessageDialog (otázka, destructive tlačítko)", ["dialogs"], steps=[key("F5"), wait(2500)], maxwin=True),
    gallery("dlg-message-focus", "MessageDialog: klávesnicový fokus na tlačítku (prstenec)", ["dialogs"], steps=[key("F5"), wait(2500), key("Tab"), wait(600)], maxwin=True),
    gallery("dlg-filechooser", "FileChooserDialog OPEN", ["dialogs", "lists"], steps=[key("F5"), wait(3500)]),
    gallery("dlg-about", "AboutDialog", ["dialogs"], steps=[key("F5"), wait(2500)]),
    gallery("dlg-color", "ColorChooserDialog", ["dialogs"], steps=[key("F5"), wait(2500)]),
]

# číslování od 1 podle pořadí; zbytek tabulky se doplňuje v souboru níže (EXTRA)
EXTRA = [
    # --- Nemo (výchozí motiv uživatele: správce souborů, hlavní předmět výtky)
    nemo("nemo-home-icons", "Nemo: ikonový pohled, Domov (výchozí stav)", crops=[NEMO_TOOLBAR, NEMO_SIDEBAR, NEMO_STATUS]),
    nemo("nemo-sidebar-select", "Nemo: sidebar s vybraným řádkem Pracovní plocha + hover na jiném řádku",
         steps=[click(95, 204), wait(20000), move(95, 274), wait(500)], crops=[NEMO_SIDEBAR, NEMO_TOOLBAR]),
    nemo("nemo-file-select-hover", "Nemo: vybraný soubor + hover na jiném",
         steps=[click(243, 153), wait(400), move(513, 153), wait(500)]),
    nemo("nemo-list-view", "Nemo: seznamový pohled s výběrem a hlavičkami sloupců",
         steps=[key("ctrl+2"), wait(1200), click(300, 213), wait(300), move(300, 305), wait(500)], crops=[("header-rows", (170, 100, 700, 150))]),
    nemo("nemo-compact-view", "Nemo: kompaktní pohled", steps=[key("ctrl+3"), wait(1200)]),
    nemo("nemo-deep-path", "Nemo: hluboká cesta v pathbaru", path=DEEP, crops=[NEMO_TOOLBAR]),
    nemo("nemo-pathbar-forward", "Nemo: pathbar po kliknutí na nadřazený drobek (zbylé podsložky tlumeně vpravo)", path=DEEP,
         steps=[click(365, 86), move(700, 800), wait(900)], crops=[NEMO_TOOLBAR]),
    nemo("nemo-location-entry", "Nemo: location entry (Ctrl+L)", steps=[key("ctrl+l"), wait(700)], crops=[NEMO_TOOLBAR]),
    nemo("nemo-search", "Nemo: hledání (Ctrl+F) s textem", steps=[key("ctrl+f"), wait(500), typ("a"), wait(1500)], crops=[NEMO_TOOLBAR]),
    nemo("nemo-rename-inline", "Nemo: inline přejmenování (F2); po snímku Escape (nic se nepřejmenuje)",
         steps=[click(243, 153), key("F2"), wait(800), SHOT, key("Escape")]),
    nemo("nemo-ctx-file", "Nemo: kontextové menu na souboru", steps=[rclick(243, 153), wait(800)]),
    nemo("nemo-ctx-empty", "Nemo: kontextové menu na prázdné ploše", steps=[rclick(700, 800), wait(800)]),
    nemo("nemo-menu-file", "Nemo: otevřené menu Soubor", steps=[click(34, 50), wait(700)], tags=("nemo", "menus")),
    nemo("nemo-menu-file-submenu", "Nemo: menu Soubor s otevřeným submenu (Vytvořit nový dokument)",
         steps=[click(34, 50), wait(500), move(120, 170), wait(900)], tags=("nemo", "menus")),
    nemo("nemo-tabs", "Nemo: záložky (Ctrl+T, 2 taby)", steps=[key("ctrl+t"), wait(1500)], crops=[("tabs", (160, 66, 700, 70))]),
    nemo("nemo-dualpane", "Nemo: dvoupanel (F3)", steps=[key("F3"), wait(1500)]),
    nemo("nemo-props", "Nemo: dialog Vlastnosti složky", steps=[click(243, 153), key("alt+Return"), wait(2500)], tags=("nemo", "dialogs")),
    nemo("nemo-prefs", "Nemo: dialog Předvolby", steps=[click(75, 50), wait(500), click(140, 536), move(1200, 900), wait(2500)], tags=("nemo", "dialogs")),
    nemo("nemo-tooltip", "Nemo: tooltip tlačítka toolbaru (hover 1,5 s)", steps=[move(1254, 85), wait(2200)], crops=[("toolbar-right", (1100, 66, 300, 120))]),
    nemo("nemo-statusbar-zoom", "Nemo: statusbar se zoom posuvníkem + hover na něm", steps=[move(1328, 978), wait(1200)],
         crops=[NEMO_STATUS]),
    # --- další GTK3 aplikace
    Scene("xed-window", "xed", ["chrome", "controls"], "xed: okno s textem, toolbar, záložka, statusbar", ["xed"],
          steps=[click(600, 400), typ("Mentha ahoj svete"), wait(500), move(5, 995), wait(400)], crops=[("toolbar-tab", (56, 50, 640, 170)), ("statusbar", (700, 895, 650, 45))]),
    Scene("xed-menu", "xed", ["menus", "chrome"], "xed: otevřené menu Soubor", ["xed"], steps=[click(90, 100), wait(700)]),
    Scene("xed-tabs", "xed", ["chrome"], "xed: tři záložky (3 soubory z CLI)",
          ["bash", "-c", 'd=$(mktemp -d /tmp/mentha-xed-XXXX); echo prvni > $d/prvni; echo druha > $d/druha; echo treti > $d/treti; exec xed $d/prvni $d/druha $d/treti'],
          # xed z CLI aktivuje první soubor; na třetí přepnout Alt+3 (dokumenty už jsou načtené, žádný časový závod)
          pre=3500, steps=[click(600, 400), wait(300), key("alt+3"), wait(800), move(5, 995), wait(400)], crops=[("tabs", (56, 150, 640, 70))]),
    Scene("cs-overview", "cinnamon-settings", ["chrome", "controls"], "Nastavení systému: hlavní přehled (ikonový pohled, vyhledávací pole)", ["cinnamon-settings"], pre=3000),
    Scene("cs-themes", "cinnamon-settings", ["controls", "chrome"], "Nastavení systému: modul Motivy vzhledu (combo, segmenty, barvy)", ["cinnamon-settings", "themes"], pre=3000),
    Scene("cs-mouse", "cinnamon-settings", ["controls", "lists"], "Nastavení systému: Myš a touchpad (switch, spin, scale, combo, list)", ["cinnamon-settings", "mouse"], pre=3000,
          crops=[("scale", (86, 480, 1230, 200)), ("switches", (1100, 140, 220, 230))]),
    Scene("gnome-disks-window", "gnome-disks", ["lists", "chrome"], "Disky: seznam zařízení vlevo, prázdný stav", ["gnome-disks"], pre=2500),
    Scene("gnome-disks-drive", "gnome-disks", ["lists", "controls"], "Disky: vybrané zařízení (jen výběr, žádná akce)", ["gnome-disks"], pre=2500,
          steps=[click(100, 62), wait(2500)]),
    Scene("file-roller-window", "file-roller", ["lists", "chrome"], "Správce archivů: demo.zip, seznam se sloupci", ["file-roller", os.path.join(FIX, "demo.zip")], pre=2500),
    Scene("file-roller-menu", "file-roller", ["menus", "chrome"], "Správce archivů: otevřené menu (kebab v headerbaru)", ["file-roller", os.path.join(FIX, "demo.zip")], pre=2500,
          steps=[click(1257, 22), wait(900)]),
    Scene("terminal-prefs", "gnome-terminal", ["dialogs", "controls", "lists"], "Terminál: okno předvoleb (sidebar, check, combo)",
          ["bash", "-c", "/usr/libexec/gnome-terminal-server & gdbus wait --session --timeout 10 org.gnome.Terminal; gnome-terminal --preferences; sleep 600"],
          maxwin=False, pre=2500, settle=1000),
    # --- GTK4 / libadwaita (libadwaita-1 potvrzeno přes ldd: font-viewer, baobab, system-monitor, simple-scan, calendar)
    Scene("fontviewer-window", "gnome-font-viewer", ["adw", "gtk4", "typography"], "Fonty (GTK4/libadwaita): hlavní okno, mřížka písem", ["gnome-font-viewer"], gtk4=True, pre=3500),
    Scene("fontviewer-search", "gnome-font-viewer", ["adw", "gtk4", "controls"], "Fonty (GTK4/libadwaita): otevřené vyhledávání s textem (Ctrl+F)", ["gnome-font-viewer"],
          gtk4=True, pre=3500, steps=[key("ctrl+f"), wait(700), typ("ar"), wait(1500), move(570, 200), wait(300), move(572, 202), wait(600)]),   # hover na dlaždici (ADW-21)
    Scene("baobab-window", "baobab", ["adw", "gtk4", "lists"], "Analyzátor disku (GTK4/libadwaita): zařízení a umístění, ukazatel zaplnění", ["baobab"], gtk4=True, pre=3500),
    Scene("baobab-prefs", "baobab", ["adw", "gtk4", "dialogs"], "Analyzátor disku (GTK4/libadwaita): dialog Předvolby (Ctrl+,) s jedním ignorovaným umístěním (list.content)",
          # GSETTINGS_BACKEND=memory je per-proces, gsettings z hostitele by aplikaci nepředalo -> keyfile v izolovaném XDG_CONFIG_HOME;
          # skutečné nastavení uživatele (dconf) se nedotkne
          ["bash", "-c", 'd=$(mktemp -d /tmp/mentha-baobab-XXXX); export GSETTINGS_BACKEND=keyfile XDG_CONFIG_HOME=$d; '
           "gsettings set org.gnome.baobab.preferences excluded-uris \"['file:///tmp/mentha-qa']\"; exec baobab"], gtk4=True, pre=3500,
          steps=[key("ctrl+,"), wait(2500)]),
    Scene("sysmon-processes", "gnome-system-monitor", ["adw", "gtk4", "lists"], "Sledování systému (GTK4/libadwaita): karta Procesy, ViewSwitcher",
          ["gnome-system-monitor"], gtk4=True, pre=3500, maxwin=False,   # dvojklik do titulku by rozhodil souřadnice klikání
          steps=[key("alt+1"), wait(3500), click(200, 247), wait(800), move(200, 352), wait(300), move(202, 354), wait(600)]),   # karta Procesy, výběr dlouho žijícího procesu + hover o řádky níž (první řádky jsou nestabilní)
    Scene("sysmon-menu", "gnome-system-monitor", ["adw", "gtk4", "menus"], "Sledování systému (GTK4/libadwaita): hlavní nabídka (F10)",
          ["gnome-system-monitor"], gtk4=True, pre=3500, steps=[key("alt+1"), wait(2500), key("F10"), wait(1500)]),   # alt+1 = karta Procesy: stejná karta pod menu v Light i Dark
    Scene("simplescan-window", "simple-scan", ["adw", "gtk4", "controls"], "Skenování (GTK4/libadwaita): hlavní okno (stav závisí na dostupnosti skeneru v síti)",
          ["simple-scan"], gtk4=True, pre=3500, settle=6000),
    Scene("simplescan-prefs-top", "simple-scan", ["adw", "gtk4", "dialogs"], "Skenování (GTK4/libadwaita): Předvolby (Ctrl+,), horní část bez scrollu: linked skupina Přední/Zadní/Obě",
          ["simple-scan"], gtk4=True, pre=3500, steps=[key("ctrl+,"), wait(2500), key("Tab"), wait(300), key("shift+Tab"), wait(400), move(380, 100), wait(300)]),   # Tab = deterministický fokus prvního řádku (P5-28)
    Scene("simplescan-prefs-bottom", "simple-scan", ["adw", "gtk4", "dialogs"], "Skenování (GTK4/libadwaita): Předvolby, spodní část (scale s marks, přepínač)",
          ["simple-scan"], gtk4=True, pre=3500, steps=[key("ctrl+,"), wait(2500)] + [scroll(600, 400, 400)] * 24 + [wait(900), move(380, 100), wait(300)]),   # spodní polovina předvoleb (přepínače, spin)
    Scene("sysmon-prefs", "gnome-system-monitor", ["adw", "gtk4", "dialogs"], "Sledování systému (GTK4/libadwaita): Předvolby (Ctrl+,): přepínač, spin row (jen čtení)",
          ["gnome-system-monitor"], gtk4=True, pre=3500, maxwin=False, steps=[key("ctrl+,"), wait(2500)]),
    # --- fokus z klávesnice (P7-05): bez --kbd-focus galerie žádný outline neukazuje (fokus jako po kliknutí myší)
] + [Scene(f"kbd-focus-{k}", "gallery3", ["controls"], f"Galerie toggles: fokus z klávesnice na {k} (outline)",
           ["python3", os.path.join(TOOLS, "gallery3.py"), "--page", "toggles", "--kbd-focus", k], maxwin=True, pre=300, settle=2800)
     for k in ("check", "radio", "scale", "switch")] + [
    # r8 (CTRL-714, A11Y-709): fokus z klávesnice na dalších ovladačích; nové scény jen na konec seznamu (číslování)
    Scene(f"kbd-focus-{k}", "gallery3", ["controls"], f"Galerie {pg}: fokus z klávesnice na {k} (outline)",
          ["python3", os.path.join(TOOLS, "gallery3.py"), "--page", pg, "--kbd-focus", k], maxwin=True, pre=300, settle=2800)
    for k, pg in (("button", "buttons"), ("suggested", "buttons"), ("linked", "buttons"), ("pathbar", "buttons"),
                  ("entry", "entries"), ("combo", "entries"), ("spin", "entries"), ("textview", "entries"))] + [
    # 2026-10-18: nastavení appletu (XApp SettingsSection v zaobleném rámu, stackswitcher po kliknutí na 2. kartu).
    # Jen čte ~/.config/cinnamon/spices/grouped-window-list@cinnamon.org/2.json, nic v nastavení neměnit.
    Scene("xlet-gwl-settings", "xlet-settings", ["lists", "chrome", "controls"],
          "Nastavení appletu Seznam seskupených oken: karta Panel po kliknutí (fokus zůstává na 1. segmentu), rohy rámu sekce",
          ["xlet-settings", "applet", "grouped-window-list@cinnamon.org", "-i", "2"], pre=3000,
          steps=[click(618, 62), move(700, 900), wait(1200)],
          crops=[("switcher", (400, 30, 600, 70)), ("corner", (60, 90, 300, 160))]),
    # LIMIT harnessu (P6-13, ADW-501/502): skupina předvoleb je v Broadway úzká (~174 px, popisky se lámou po písmenech) i se stock Adwaita
    # (ADW_DEBUG_THEME_NAME=Adwaita: stejná šířka 174 px jako Mentha, qa/round-6-i2-fix-libadwaita-stock) -> velikost AdwDialog/AdwPreferencesPage
    # v Broadway, ne vada motivu. Totéž platí pro simplescan-prefs-*. Neladit motiv podle této zúžené skupiny.
]


def all_scenes():
    return SCENES + EXTRA


# ---------------------------------------------------------------- pomocné
def sh(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def ensure_fixtures():
    os.makedirs(FIX, exist_ok=True)
    zp = os.path.join(FIX, "demo.zip")
    if not os.path.exists(zp):
        with zipfile.ZipFile(zp, "w") as z:
            for n, c in [("README.md", "# Demo\n"), ("src/main.py", "print(1)\n"), ("src/util.py", "x = 1\n"),
                         ("docs/navod.txt", "text\n" * 50), ("img/logo.png", "x" * 3000)]:
                zi = zipfile.ZipInfo(n, date_time=(2026, 1, 15, 10, 30, 0))   # pevné datum = stejný snímek
                zi.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi, c)


def token_colors(variant):
    t = json.load(open(os.path.join(ROOT, "src", "tokens.json")))
    base, acc = t["base"][variant], t["accents"][t["default_accent"]][variant]
    pick = {k: base[k] for k in ("bg", "surface_alt", "border", "fg", "fg_muted") if k in base}
    pick["accent"] = acc["accent"]
    out = {}
    for k, v in pick.items():
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            out[k] = tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))
    return out


def analyse(path, variant):
    """Slepý snímek (málo barev) a test, že v něm jsou barvy motivu Mentha (ne Adwaita)."""
    im = np.asarray(Image.open(path).convert("RGB"))
    flat = (im[..., 0].astype(np.uint32) << 16) | (im[..., 1].astype(np.uint32) << 8) | im[..., 2]
    uniq, cnt = np.unique(flat, return_counts=True)
    n_colors = len(uniq)
    # dominantní barva zabírá < 99.5 % a snímek má aspoň 25 barev
    blank = n_colors < 25 or cnt.max() / flat.size > 0.995
    have = set(int(u) for u in uniq)
    found = [k for k, rgb in token_colors(variant).items() if (rgb[0] << 16 | rgb[1] << 8 | rgb[2]) in have]
    return {"colors": int(n_colors), "blank": bool(blank), "theme_hits": found, "theme_ok": len(found) >= 2}


def run_scene(sc, variant, disp, outpng, logdir, wait_s=45):
    """Jeden snímek: scene.sh start -> cdp (waitwin, maxwin, kroky, shot) -> stop. Vrací (ok, důvod, log)."""
    Var = variant.capitalize()
    env = dict(os.environ)
    env["MENTHA_GTK4"] = "1" if sc.gtk4 else "0"
    scene_sh = os.path.join(TOOLS, "scene.sh")
    sh([scene_sh, "stop", str(disp)], env=env)
    time.sleep(0.4)
    r = sh([scene_sh, Var, str(disp)] + sc.cmd, env=env)
    m = re.search(r"log (\S+)", r.stdout)
    applog = m.group(1) if m else None
    steps = [{"waitwin": wait_s * 1000}, wait(sc.pre)]
    if sc.maxwin:
        steps.append({"maxwin": True})
        # dvojklik do titulku nechá kurzor nad obsahem (falešný hover); scéna s vlastním move ho řeší sama
        if not any("move" in s for s in sc.steps):
            # Nemo: (5, 995) je přepínač „Zobrazit místa“ a vyvolá tooltip; prázdná plocha pohledu
            steps.append(move(700, 800) if sc.app == "nemo" else move(5, 995))
    steps.append(wait(sc.settle))
    body = [dict(s) for s in sc.steps]
    if not any(s.get("shot") == "@" for s in body):
        body.append(dict(SHOT))
    for s in body:
        if s.get("shot") == "@":
            s["shot"] = outpng
    steps += body
    os.makedirs(os.path.dirname(outpng), exist_ok=True)
    if os.path.exists(outpng):
        os.remove(outpng)
    script = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(steps, script)
    script.close()
    try:
        p = sh(["python3", os.path.join(TOOLS, "cdp.py"), f"http://127.0.0.1:{8080 + disp}/", f"{W}x{H}", script.name], timeout=120)
        ok, why = os.path.exists(outpng), ""
        if p.returncode == 3:
            ok, why = False, f"aplikace neotevřela okno do {wait_s} s"
        elif not ok:
            ok, why = False, "cdp selhalo: " + (p.stderr.strip().splitlines() or ["?"])[-1][:200]
        if "maxwin: nepovedlo" in p.stderr:
            why = (why + " maxwin nepovedl").strip()
    except subprocess.TimeoutExpired:
        ok, why = False, "timeout cdp (120 s)"
    finally:
        os.unlink(script.name)
        sh([scene_sh, "stop", str(disp)], env=env)
    warns = ""
    if applog and os.path.exists(applog):
        txt = open(applog, errors="replace").read()
        keep = [l for l in txt.splitlines() if re.search(r"Theme parser|WARNING|CRITICAL|Gtk-|Adwaita-", l)]
        warns = "\n".join(keep[:200])
        # GTK4/libadwaita scéna platí jen když libadwaita opravdu načetla Mentha (ne Adwaitu / Mint-Y-Aqua) – snímek jinak zahodit
        if ok and sc.gtk4 and sc.app not in NO_ADW_INIT and not re.search(r"Using theme 'Mentha-[\w-]+' found in", txt):
            ok, why = False, "libadwaita nenačetla motiv Mentha (app.log bez \"Using theme 'Mentha-\")"
            os.remove(outpng)
        shutil.rmtree(os.path.dirname(applog), ignore_errors=True)
    if warns and logdir:
        os.makedirs(logdir, exist_ok=True)
        open(os.path.join(logdir, os.path.basename(outpng)[:-4] + ".log"), "w").write(warns + "\n")
    return ok, why


def crop2x(src, dst, box):
    x, y, w, h = box
    r = sh(["convert", src, "-crop", f"{w}x{h}+{x}+{y}", "+repage", "-scale", "200%", dst])
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--only", default=None)
    ap.add_argument("--variant", choices=["light", "dark"], default=None)
    a = ap.parse_args()
    out = os.path.abspath(a.outdir)
    disp = int(os.environ.get("MENTHA_DISPLAY", "7"))
    ensure_fixtures()
    os.makedirs(out, exist_ok=True)
    mpath = os.path.join(out, "manifest.json")
    cpath = os.path.join(out, "checks.json")
    entries, checks = {}, {}
    if a.only or a.variant:
        if os.path.exists(mpath):
            entries = {e["file"]: e for e in json.load(open(mpath))}
        if os.path.exists(cpath):
            checks = json.load(open(cpath))
    else:
        for v in ("light", "dark"):
            shutil.rmtree(os.path.join(out, v), ignore_errors=True)
        shutil.rmtree(os.path.join(out, "logs"), ignore_errors=True)
    scenes = all_scenes()
    rx = re.compile(a.only) if a.only else None
    failed = []
    variants = [a.variant] if a.variant else ["light", "dark"]
    t0 = time.time()
    for variant in variants:
        for i, sc in enumerate(scenes, 1):
            name = f"{i:02d}-{sc.sid}"
            if rx and not (rx.search(name) or rx.search(sc.app)):
                continue
            rel = f"{variant}/{name}.png"
            outpng = os.path.join(out, rel)
            logdir = os.path.join(out, "logs", variant)
            ok, why = False, ""
            for attempt in (1, 2, 3):
                ok, why = run_scene(sc, variant, disp, outpng, logdir)
                if ok:
                    chk = analyse(outpng, variant)
                    if chk["blank"]:
                        ok, why = False, "prázdný snímek"
                if ok:
                    break
            for k in [k for k in entries if k.startswith(f"{variant}/{name}")]:
                del entries[k]
            if not ok:
                failed.append(f"{variant}/{name}: {why}")
                checks[rel] = {"failed": why}
                print(f"[{time.time() - t0:5.0f}s] FAIL {rel}: {why}", flush=True)
                continue
            checks[rel] = chk
            tags = sc.tags
            entries[rel] = {"file": rel, "variant": variant, "app": sc.app, "scene": sc.sid, "tags": tags, "desc": sc.desc}
            for det, box in sc.crops:
                crel = f"{variant}/{name}--{det}@2x.png"
                if crop2x(outpng, os.path.join(out, crel), box):
                    entries[crel] = {"file": crel, "variant": variant, "app": sc.app, "scene": f"{sc.sid}--{det}",
                                     "tags": tags, "desc": f"{sc.desc} (výřez 2×: {det})"}
            flag = "" if chk["theme_ok"] else "  [Mentha NEOVĚŘENA]"
            print(f"[{time.time() - t0:5.0f}s] ok   {rel}{flag}", flush=True)
    man = sorted(entries.values(), key=lambda e: (e["variant"], e["file"]))
    json.dump(man, open(mpath, "w"), ensure_ascii=False, indent=1)
    json.dump(checks, open(cpath, "w"), ensure_ascii=False, indent=1)
    pngs = sum(1 for e in man if os.path.exists(os.path.join(out, e["file"])))
    bad_theme = [k for k, v in checks.items() if "theme_ok" in v and not v["theme_ok"]]
    print(f"\nHotovo: {pngs} snímků, manifest {mpath}; selhalo {len(failed)}; bez dokladu o Mentha {len(bad_theme)}")
    for f in failed:
        print("  FAIL", f)
    for b in bad_theme:
        print("  THEME?", b)
    json.dump({"failed": failed, "bad_theme": bad_theme}, open(os.path.join(out, "summary.json"), "w"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
