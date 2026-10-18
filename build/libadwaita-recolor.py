#!/usr/bin/env python3
"""Mentha: libadwaita recolor.

Zdroj: upstream/mint-themes/src/Mint-Y/libadwaita-{1.5,1.7}  (READ-ONLY)
Barvy: build/gen/tokens-{light,dark}.json  (z src/tokens.json, akcent přepínatelný)
Výstup: dist/Mentha-{Light,Dark}/libadwaita-{1.5,1.7}/

Co se dělá:
  * defaults-light.css / defaults-dark.css: hodnoty @define-color přepsány z tokenů
    (žádný ručně psaný hex; odvozené barvy se počítají z tokenů)
  * base.css / base-hc.css: kopie; radiusy tlačítek/entry -> mt radius.sm,
    okno (1.7) -> radius.md; připojen blok s gradientem jen pro progress/scale highlight
  * assets: kopie
Volání: libadwaita-recolor.py build | check
"""
import json, re, shutil, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
UP = ROOT / "upstream/mint-themes/src/Mint-Y"
DIST = ROOT / "dist"
VERSIONS = ["1.5", "1.7"]
THEMES = ["Mentha-Light", "Mentha-Dark"]
VARIANTS = ("light", "dark")

TOK = {v: json.loads((ROOT / f"build/gen/tokens-{v}.json").read_text()) for v in VARIANTS}
SRC = json.loads((ROOT / "src/tokens.json").read_text())
RADIUS = SRC["radius"]


# ---------- barvy ----------
def parse(c):
    c = c.strip()
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(x * 2 for x in h)
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    m = re.match(r"rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)", c)
    return [float(m.group(i)) for i in (1, 2, 3)]


def hexs(rgb):
    return "#" + "".join(f"{max(0, min(255, round(x))):02X}" for x in rgb)


def lum(rgb):
    def f(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    return [x + (y - x) * t for x, y in zip(a, b)]


def readable(color, bg, target=4.5):
    """Zesvětlí/ztmaví barvu, dokud nemá kontrast >= target vůči bg (směr podle bg)."""
    c, b = parse(color), parse(bg)
    goal = [0, 0, 0] if lum(b) > 0.4 else [255, 255, 255]
    for i in range(21):
        out = mix(c, goal, i * 0.05)
        if contrast(out, b) >= target:
            return hexs(out)
    return hexs(goal)


def fg_on(color):
    """Text na barevném podkladu: bílá vs. rgba(0,0,0,.8) podle vyššího kontrastu."""
    c = parse(color)
    return "#FFFFFF" if contrast(c, [255, 255, 255]) >= contrast(c, [0, 0, 0]) else "rgba(0, 0, 0, 0.8)"


def shadow_rgba(sh):
    """Barva (rgba) ze stínu tokenu, např. '0 12px 28px rgba(24, 40, 80, 0.16)'."""
    return re.search(r"rgba?\([^)]*\)", sh).group(0)


# ---------- mapování tokenů na @define-color ----------
def palette(var):
    t = TOK[var]
    light = var == "light"
    err = readable(t["error"], t["surface"])
    err_bg = readable(t["error"], t["error_fg"])      # bold label na error_bg >= 4.5
    ok = readable(t["success"], t["surface"])
    return {
        "mint_accent": t["accent"],
        "mint_header": t["surface"],
        "mint_button_hover": t["hover"],
        "mint_button_unfocused": t["fg_disabled"],
        "accent_bg_color": t["accent"],
        "accent_fg_color": t["accent_fg"],
        "accent_color": t["accent_text"],
        "destructive_bg_color": err_bg,
        "destructive_fg_color": t["error_fg"],
        "destructive_color": err,
        "success_bg_color": t["success"],
        "success_fg_color": fg_on(t["success"]),
        "success_color": ok,
        "warning_bg_color": t["warning"],
        "warning_fg_color": "rgba(0, 0, 0, 0.8)",
        "warning_color": t["warning_text"],
        "error_bg_color": err_bg,
        "error_fg_color": t["error_fg"],
        "error_color": err,
        "window_bg_color": t["surface"],          # okno = surface (mockup .win), headerbar splývá
        "window_fg_color": t["fg"],
        "view_bg_color": t["surface"],
        "view_fg_color": t["fg"],
        "headerbar_bg_color": t["surface"],
        "headerbar_fg_color": t["fg"],
        "headerbar_border_color": t["fg"],
        "headerbar_backdrop_color": t["surface"],
        "headerbar_shade_color": "transparent",   # spec: bez dělicí čáry pod headerbarem
        "headerbar_darker_shade_color": t["hairline"],
        "sidebar_bg_color": t["surface_alt"],
        "sidebar_fg_color": t["fg"],
        "sidebar_backdrop_color": t["surface_alt"],
        "sidebar_shade_color": t["hairline"],
        "sidebar_border_color": t["hairline"],
        "secondary_sidebar_bg_color": t["bg"],
        "secondary_sidebar_fg_color": t["fg"],
        "secondary_sidebar_backdrop_color": t["bg"],
        "secondary_sidebar_shade_color": t["hairline"],
        "secondary_sidebar_border_color": t["hairline"],
        "card_bg_color": t["surface_alt"],
        "card_fg_color": t["fg"],
        "card_shade_color": t["hairline"],
        "dialog_bg_color": t["surface_raised"],
        "dialog_fg_color": t["fg"],
        "popover_bg_color": t["surface_raised"],
        "popover_fg_color": t["fg"],
        "popover_shade_color": t["hairline"],
        "thumbnail_bg_color": t["surface_raised"],
        "thumbnail_fg_color": t["fg"],
        "shade_color": t["hairline"],
        "scrollbar_outline_color": t["surface"] if light else t["bg"],
        # vlastní (Mentha) – pro gradient na progress/scale
        "mentha_grad_from": t["grad_from"],
        "mentha_grad_to": t["grad_to"],
        "mentha_fg_muted": t["fg_muted"],
        "mentha_track": t["track"],                        # dráha ukazatelů (scale/progress/levelbar): >= 2:1 vůči plochám
        # vypnutý switch: Light světlá dráha switch_off (PLSH-704); na povýšené kartě v Dark o chlup světlejší, aby dráha držela >= 3:1
        "mentha_switch_off": t["switch_off"],
        "mentha_switch_off_hover": t["switch_off_hover"],
        "mentha_switch_off_card": t["switch_off"] if light else hexs(mix(parse(t["switch_off"]), parse(t["fg_muted"]), 0.2)),
        "mentha_level_low": t.get("level_low", t["warning"]),     # levelbar .low (parita s GTK3; token z P6-07)
        "mentha_level_high": t.get("level_high", t["success"]),   # levelbar .high/.full
        "mentha_fg_disabled": t["fg_disabled"],
        "mentha_track_soft": t["track_soft"],                  # dráha vypnutého scale
        "mentha_tooltip_bg": t["tooltip_bg"],
        "mentha_tooltip_fg": t["tooltip_fg"],
        "mentha_tooltip_border": "rgba(255, 255, 255, 0.1)" if light else t["border"],   # upstream lem; v Dark viditelný obrys
        "mentha_switch_knob": t.get("switch_knob", "#FFFFFF"),   # jezdec přepínače: stejná barva jako v GTK3 (token, jinak bílá)
        "mentha_control_border": t["control_border"],      # okraj ovládacích prvků (tlačítka, segmenty)
        # karta uvnitř dialogu: Light surface_alt; Dark o stupeň světlejší než povýšený podklad dialogu
        "mentha_card_raised": t["surface_alt"] if light else hexs(mix(parse(t["surface_raised"]), parse(t["fg"]), 0.04)),
        # tlačítka / pole / výběr / focus — stejné tokeny jako GTK3 vrstva (jeden zdroj pravdy)
        "mentha_fg": t["fg"],
        "mentha_hairline": t["hairline"],
        # stíny z tokenů (modrý nádech, v Dark černý): celé rgba pro popover/okno, opaque odstín pro karty
        "mentha_shadow_popup": shadow_rgba(t["shadow_popup"]),
        "mentha_shadow_window": shadow_rgba(t["shadow_window"]),
        "mentha_shadow_window_backdrop": shadow_rgba(t["shadow_window_backdrop"]),
        "mentha_shadow_tint": hexs(parse(shadow_rgba(t["shadow_popover_inline"]))),
        "mentha_surface": t["surface"],
        "mentha_slider_ring": t["slider_ring"],
        "mentha_surface_alt": t["surface_alt"],
        "mentha_border": t["border"],
        "mentha_border_strong": t["border_strong"],
        "mentha_hover": t["hover"],
        "mentha_active": t["active"],
        "mentha_accent_soft": t["accent_soft"],
        "mentha_accent_soft_hover": t["accent_soft_hover"],
        "mentha_accent_text": t["accent_text"],
        "mentha_accent_hover": t["accent_hover"],
        "mentha_accent_pressed": t["accent_pressed"],
        "mentha_error_hover": t["error_hover"],
        "mentha_error_pressed": t["error_pressed"],
        "mentha_selection": t["selection"],
        "mentha_selection_strong": t["selection_strong"],
        "mentha_focus": t["focus"],   # plná barva: 2px outline musí mít >= 3:1 vůči kartě i oknu
    }


# CSS vlastnosti v :root bloku na konci defaults (jen 1.7); mají přednost před oklab odvozením
def root_overrides(var):
    t, p = TOK[var], palette(var)
    d = {
        "--accent-color": p["accent_color"],
        "--active-toggle-bg-color": t["surface"] if var == "light" else t["active"],
        "--active-toggle-fg-color": t["fg"],
        "--overview-bg-color": t["bg"],
        "--overview-fg-color": t["fg"],
    }
    if var == "light":
        d["--warning-color"] = t["warning_text"]
    return d


DEF_RE = re.compile(r"^@define-color\s+(\w+)\s+(.*);\s*$")


def recolor_defaults(text, var, version):
    pal = palette(var)
    done, out = set(), []
    for line in text.splitlines():
        m = DEF_RE.match(line)
        if m and m.group(1) in pal:
            out.append(f"@define-color {m.group(1)} {pal[m.group(1)]};")
            done.add(m.group(1))
        else:
            out.append(line)
    missing = [k for k in pal if k not in done]
    # chybějící definice (1.7 nemá accent_*) vložit za komentář GTK NAMED COLORS
    ins = [f"@define-color {k} {pal[k]};" for k in missing]
    res = []
    placed = False
    for line in out:
        res.append(line)
        if not placed and line.startswith("/* GTK NAMED COLORS"):
            res += ins
            placed = True
    if not placed:
        res = ins + res
    body = "\n".join(res) + "\n"
    r = body.find(":root")
    if r >= 0:
        tail = body[r:]
        for prop, val in root_overrides(var).items():
            pat = re.compile(re.escape(prop) + r":\s*(?:[^;()]|\((?:[^()]|\([^()]*\))*\))*;")
            tail, n = pat.subn(lambda _m: f"{prop}: {val};", tail, count=1)
            if n != 1:
                raise SystemExit(f"{version}/{var}: {prop} v :root nenalezen")
        body = body[:r] + tail
    head = (f"/* Mentha {var} / libadwaita-{version} — GENEROVÁNO build/libadwaita-recolor.py "
            f"z tokenů (akcent: {ACCENT}). Needitovat. */")
    return head + "\n" + body


# ---------- base.css ----------
BTN_SELECTORS = [
    r"^notebook > header > tabs > arrow, row\.spin spinbutton",      # obecné tlačítko
    r"^menubutton\.suggested-action, menubutton\.(destructive-action, )?opaque",
    r"^splitbutton$",
    r"^actionbar > revealer > box splitbutton",
    r"^spinbutton, entry$",
    r"^spinbutton:not\(\.vertical\) > button\.image-button\.up",
    r"^spinbutton\.vertical > button\.image-button\.up",
]
RAD_RE = re.compile(r"(border-radius:\s*)([^;]*);")


# Tlačítka: upstream kreslí šedou výplň alpha(currentColor, x) jedním pravidlem pro `button` a
# ploché kontexty (headerbar/toolbar ikonová tlačítka) pozdějším pravidlem `button.flat` se stejnými stavy.
# Přepisujeme hodnoty přímo v těchto pravidlech, ne přidáváme další s vyšší specificitou:
# vrstvení „obecné tlačítko -> ploché v headerbaru/toolbaru“ tak zůstane přesně upstreamové.
BTN_BORDER = "box-shadow: inset 0 0 0 1px @mentha_control_border;"


def cc(prop, pct):
    """Upstream šedá výplň: 1.5 `alpha(currentColor,.x)`, 1.7 `color-mix(in srgb, currentColor x%, transparent)`."""
    return {f"{prop}: alpha(currentColor,{pct / 100:g});", f"{prop}: color-mix(in srgb, currentColor {pct}%, transparent);"}


# (selektor, původní tělo pravidla) -> nové tělo
BTN_STATES = [
    ("button", cc("background-color", 10), f"background-color: transparent; {BTN_BORDER}"),
    ("button:hover", cc("background-color", 15), "background-color: @mentha_hover;"),
    ("button:active", cc("background-color", 30), "background-color: @mentha_active;"),
    ("button:checked", cc("background-color", 30),
     "background-color: @mentha_accent_soft; color: @mentha_accent_text; box-shadow: none;"),
    ("button:checked:hover", cc("background-color", 35), "background-color: @mentha_accent_soft_hover;"),
    ("button:checked:active", cc("background-color", 40), "background-color: @mentha_accent_soft_hover;"),
    ("button.flat:hover", cc("background", 7), "background: @mentha_hover;"),
    ("button.flat:active", cc("background", 16), "background: @mentha_active;"),
    ("button.flat:checked", cc("background", 10), "background: @mentha_accent_soft; color: @mentha_accent_text;"),
    ("button.flat:checked:hover", cc("background", 13), "background: @mentha_accent_soft_hover;"),
    ("button.flat:checked:active", cc("background", 19), "background: @mentha_accent_soft_hover;"),
]
FOCUS_UP = ("alpha(@accent_color,0.5)", "color-mix(in srgb, var(--accent-color) 50%, transparent)")  # půlprůhledný, pod 3:1


def patch_base(text, counts):
    sm = RADIUS["sm"]
    for up in FOCUS_UP:
        counts["focus"] += text.count(up)
        text = text.replace(up, "@mentha_focus")
    lines = text.split("\n")
    for i, l in enumerate(lines):
        m = re.match(r"([^{]*)\{(.*)\}\s*$", l)
        if not m:
            continue
        sel = m.group(1).strip()
        sels = {x.strip() for x in sel.split(", ")}
        body = m.group(2).strip()
        state = next((new for bare, old, new in BTN_STATES if bare in sels and body in old), None)
        if state:
            lines[i] = f"{sel} {{ {state} }}"
            counts["state"] += 1
        elif WINCTL_UP.match(sel) and ("border-radius: 100%" in m.group(2) or "color: white" in m.group(2)):
            lines[i] = None
            counts["wc"] += 1
        elif any(re.match(p, sel) for p in BTN_SELECTORS):
            def sub(mm):
                new = re.sub(r"\b(6|9)px\b", sm, mm.group(2))
                if new != mm.group(2):
                    counts["btn"] += 1
                return mm.group(1) + new + ";"
            lines[i] = RAD_RE.sub(sub, l)
        elif sel == ":root" and re.fullmatch(r"\s*--window-radius:\s*15px;\s*", m.group(2)):
            lines[i] = f":root {{ --window-radius: {RADIUS['md']}; }}"
            counts["win"] += 1
    return "\n".join(l for l in lines if l is not None)


# upstream (Mint-Y/libadwaita) kulatá tlačítka titulku: `windowcontrols > button[.close][:state] > image`
WINCTL_UP = re.compile(r"^windowcontrols > button(\.close)?(:\w+)? > image$")

WINCTL = """
/* ===== Mentha: tlačítka titulku — zaoblené čtverce 28x28 / radius 9 (DESIGN-verdict) ===== */
/* rozestup středů 38 px jako GTK3 (28 + 2x margin 2 + spacing headerbaru 6) */
windowcontrols { border-spacing: 10px; }
windowcontrols.end { margin-right: 2px; }
windowcontrols.start { margin-left: 2px; }
windowcontrols > button { min-width: 28px; min-height: 28px; padding: 0; }
windowcontrols > button > image {
  -gtk-icon-size: 16px; padding: 6px; border-radius: 9px;   /* nativní 16 px symbolika = ostré glyfy */
  background: none; color: @mentha_fg_muted;
  transition: background 120ms ease, color 120ms ease;
}
windowcontrols > button:hover > image { background-color: @sidebar_bg_color; color: @window_fg_color; }
windowcontrols > button:active > image { background-color: alpha(currentColor, 0.15); }
windowcontrols > button.close:hover > image, windowcontrols > button.close:active > image {
  background-color: @error_bg_color; color: @error_fg_color;
}
windowcontrols > button.close:active > image { filter: brightness(92%); }
windowcontrols > button:backdrop > image { opacity: 0.5; }
"""

GRAD = """
/* ===== Mentha: gradient jen na progress/scale/levelbar výplně (src/tokens.json rules) ===== */
progressbar.horizontal:not(.osd) > trough > progress:not(:disabled),
scale.horizontal:not(.osd) > trough > highlight:not(:disabled),
levelbar:not(.discrete).horizontal > trough > block.filled:not(.full):not(.low):not(.high) {
  background-image: linear-gradient(to right, @mentha_grad_from, @mentha_grad_to);
}
progressbar.vertical:not(.osd) > trough > progress:not(:disabled),
scale.vertical:not(.osd) > trough > highlight:not(:disabled),
levelbar:not(.discrete).vertical > trough > block.filled:not(.full):not(.low):not(.high) {
  background-image: linear-gradient(to top, @mentha_grad_from, @mentha_grad_to);
}
scale.horizontal:not(.osd):hover > trough > highlight:not(:disabled), scale.horizontal:not(.osd):active > trough > highlight:not(:disabled) {
  background-image: image(alpha(currentColor,0.1)), linear-gradient(to right, @mentha_grad_from, @mentha_grad_to);
}
scale.vertical:not(.osd):hover > trough > highlight:not(:disabled), scale.vertical:not(.osd):active > trough > highlight:not(:disabled) {
  background-image: image(alpha(currentColor,0.1)), linear-gradient(to top, @mentha_grad_from, @mentha_grad_to);
}
/* OSD (video přehrávače, loading bar prohlížeče) zůstává u upstream bílé výplně: .osd je na předku, ne na uzlu */
.osd progressbar.horizontal > trough > progress:not(:disabled), .osd progressbar.vertical > trough > progress:not(:disabled),
.osd scale.horizontal > trough > highlight:not(:disabled), .osd scale.vertical > trough > highlight:not(:disabled),
.osd levelbar:not(.discrete).horizontal > trough > block.filled:not(.full),
.osd levelbar:not(.discrete).vertical > trough > block.filled:not(.full) {
  background-image: none;
}
.osd scale.horizontal:hover > trough > highlight:not(:disabled), .osd scale.horizontal:active > trough > highlight:not(:disabled),
.osd scale.vertical:hover > trough > highlight:not(:disabled), .osd scale.vertical:active > trough > highlight:not(:disabled) {
  background-image: image(alpha(currentColor,0.1));
}
"""


OVERRIDES = """
/* ===== Mentha: doladění nad upstreamem (hodnoty jen z tokenů přes @mentha_*) ===== */

/* plná tlačítka: žádný 1px rámeček z obecného tlačítka; hover/pressed ze stavů akcentu */
button.suggested-action, button.destructive-action, button.opaque, button.osd,
menubutton.osd > button { box-shadow: none; }
button.suggested-action:hover { background-color: @mentha_accent_hover; }
button.suggested-action:active, button.suggested-action:checked { background-color: @mentha_accent_pressed; }
button.destructive-action:hover { background-color: @mentha_error_hover; }
button.destructive-action:active, button.destructive-action:checked { background-color: @mentha_error_pressed; }
button.suggested-action:focus:focus-visible, button.destructive-action:focus:focus-visible {
  outline-color: @mentha_focus; outline-offset: 2px;
}

/* ViewSwitcher: bez podkladu okolo, tlačítko 32 px stejného tvaru jako ostatní */
viewswitcher.wide button.toggle { min-height: 32px; border-radius: __SM__; }

/* pole: surface_alt + 1px okraj (jako GTK3); hover tmavší okraj; focus 2px outline z upstreamu */
entry, spinbutton { background-color: @mentha_surface_alt; box-shadow: inset 0 0 0 1px @mentha_border; }
entry:hover, spinbutton:hover { box-shadow: inset 0 0 0 1px @mentha_border_strong; }
entry:focus-within, spinbutton:focus-within { box-shadow: inset 0 0 0 1px @mentha_border; }
/* na kartě (surface_alt) by pole splynulo -> surface */
.boxed-list entry, .boxed-list spinbutton, row entry, row spinbutton { background-color: @mentha_surface; }
/* vyhledávací pilulka bez okraje */
searchbar entry, headerbar entry.search, entry.search {
  border-radius: __PILL__; background-color: @mentha_surface_alt; box-shadow: none;
}
searchbar entry:hover, headerbar entry.search:hover, entry.search:hover,
searchbar entry:focus-within, headerbar entry.search:focus-within, entry.search:focus-within { box-shadow: none; }

/* ukazatele: dráha track, výplň s přechodem (jen level/progress), 6 px */
levelbar > trough > block.empty, progressbar > trough, scale > trough { background-color: @mentha_track; }
levelbar.horizontal > trough > block, progressbar.horizontal > trough, progressbar.horizontal > trough > progress {
  min-height: 6px; border-radius: __PILL__;
}
levelbar.vertical > trough > block, progressbar.vertical > trough, progressbar.vertical > trough > progress {
  min-width: 6px; border-radius: __PILL__;
}
/* výplň s přechodem řeší GRAD; low/high/full plnou barvou z tokenů (jako GTK3), vyšší specificita než upstream block:not(.empty) */
levelbar > trough > block.filled.low { background-color: @mentha_level_low; background-image: none; }
levelbar > trough > block.filled.high, levelbar > trough > block.filled.full { background-color: @mentha_level_high; background-image: none; }

scale:hover > trough, scale:active > trough { background-color: @mentha_track; }
scale:disabled > trough { background-color: @mentha_track_soft; }

/* karty v dialogu/předvolbách: o stupeň nad podkladem dialogu (v Dark by jinak byly tmavší než okolí) */
window.dialog .card, window.dialog .boxed-list, dialog-host > dialog .card, dialog-host > dialog .boxed-list,
window.preferences .card, window.preferences .boxed-list,
window.dialog list.content, dialog-host > dialog list.content, window.preferences list.content { background-color: @mentha_card_raised; }

/* tlumený text: plná barva fg_muted místo opacity (opacity zhoršuje kontrast na kartě); selektory kopírují upstream,
   jinak by jejich vyšší specificita vyhrála */
.dim-label, .subtitle, row label.subtitle, row .subtitle, row.property > box.header > box.title > .title,
row.expander.property box > list > row > box.header > box.title > .title,
headerbar .subtitle, windowtitle .subtitle, scale > value, progressbar > text { opacity: 1; color: @mentha_fg_muted; }
/* na barevných plochách by šedá nebyla čitelná -> děděná barva s tlumením jako dřív */
button.suggested-action .dim-label, button.destructive-action .dim-label, button.opaque .dim-label,
button.suggested-action .subtitle, button.destructive-action .subtitle, .osd .dim-label, .osd .subtitle,
progressbar.osd > text { color: inherit; opacity: 0.7; }

/* segmenty (.linked): zapnutý segment = accent_soft výplň + obrys control_border jako GTK3 (ne akcentový obrys) */
.linked > button:checked { box-shadow: inset 0 0 0 1px @mentha_control_border; }

/* popover menu: hover/výběr jako GTK3 menuitem (selection token) */
popover.menu modelbutton:hover, popover.menu modelbutton:selected,
popover.menu list > row:hover, popover.menu listview > row:hover {
  background-color: @mentha_selection; border-radius: __XS__;
}
popover.menu modelbutton:active, popover.menu list > row:active, popover.menu listview > row:active {
  background-color: @mentha_selection_strong;
}

/* dialogy a předvolby: povýšená plocha (v Dark světlejší než hlavní okno), headerbar splývá s ní */
window.preferences, window.dialog { background-color: @dialog_bg_color; }
window.preferences headerbar, window.dialog headerbar { background-color: @dialog_bg_color; }

/* switch: shodně s GTK3 — dráha switch_off (Light světlá, Dark border_strong), jezdec z tokenu, zapnuto plný akcent bez přechodu.
   Selektory kopírují upstream (switch / :hover / :active / :checked), stavy upstreamu s alpha(currentColor) se tím přebijí. */
switch { background-color: @mentha_switch_off; background-image: none; }
/* geometrie jako GTK3: dráha 48x24, jezdec 18 px s okrajem 3 px. GtkSwitch dává jezdci polovinu šířky obsahu a výšku obsahu,
   proto padding 0 (jezdec 24x24) a okraj jako margin jezdce -> kruh 18 px */
switch { min-width: 48px; min-height: 24px; padding: 0; }
switch:hover:not(:checked) { background-color: @mentha_switch_off_hover; }
switch:active:not(:checked) { background-color: @mentha_switch_off_hover; }
switch:checked { background-color: @accent_bg_color; background-image: none; }
switch:checked:hover { background-color: @mentha_accent_hover; background-image: none; }
switch:checked:active { background-color: @mentha_accent_pressed; background-image: none; }
.card switch:not(:checked), list.boxed-list switch:not(:checked), list.content switch:not(:checked) { background-color: @mentha_switch_off_card; }
.card switch:hover:not(:checked), .card switch:active:not(:checked), list.boxed-list switch:hover:not(:checked),
list.boxed-list switch:active:not(:checked), list.content switch:hover:not(:checked), list.content switch:active:not(:checked) { background-color: @mentha_switch_off_hover; }
switch > slider, switch:hover > slider, switch:active > slider, switch:checked > slider {
  min-width: 18px; min-height: 18px; margin: 3px; background-color: @mentha_switch_knob; background-image: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}
switch:checked > slider, switch:checked:hover > slider, switch:checked:active > slider { background-color: @accent_fg_color; }   /* zapnuto: jezdec accent_fg (Dark tmavý ≈7:1, bílý měl 2,43:1) jako GTK3 */
switch > slider:disabled { box-shadow: none; }

/* scale: kulatý akcentový jezdec 18 px celkem (14 + 2px prstenec slider_ring: Light bílý, Dark o stupeň světlejší než plocha) — shodně s GTK3 */
scale > trough > slider {
  background-color: @accent_bg_color; background-image: none; min-width: 14px; min-height: 14px; margin: -7px;
  border: 2px solid @mentha_slider_ring; border-radius: 100%; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}
scale:hover > trough > slider { background-color: @mentha_accent_hover; box-shadow: 0 0 0 4px @mentha_accent_soft, 0 1px 3px rgba(0, 0, 0, 0.3); }
scale:active > trough > slider { background-color: @mentha_accent_pressed; box-shadow: 0 0 0 4px @mentha_accent_soft, 0 1px 3px rgba(0, 0, 0, 0.3); }
scale:disabled > trough > slider { background-color: @mentha_fg_disabled; box-shadow: none; }
/* kopie selektorů upstreamu pro značky (jinak by kapka/rotace vyhrála specificitou) */
scale.marks-before:not(.marks-after) > trough > slider, scale.marks-after:not(.marks-before) > trough > slider,
scale.marks-before:not(.marks-after) > trough > slider:disabled, scale.marks-after:not(.marks-before) > trough > slider:disabled {
  transform: none; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}
scale.marks-before:not(.marks-after) > trough > slider:disabled, scale.marks-after:not(.marks-before) > trough > slider:disabled {
  box-shadow: none;
}
scale.horizontal.marks-before > trough > slider, scale.horizontal.marks-after > trough > slider,
scale.vertical.marks-before > trough > slider, scale.vertical.marks-after > trough > slider,
scale.horizontal.marks-before.marks-after > trough > slider { border-radius: 100%; }
/* fokus: akcentový prstenec s mezerou, jinak by splynul s akcentovým jezdcem */
scale:focus:focus-visible > trough > slider { outline-color: @mentha_focus; outline-offset: 2px; }
scale.horizontal > marks, scale.vertical > marks { color: @mentha_fg_muted; }
scale > marks > mark > label { opacity: 1; color: @mentha_fg_muted; }
scale.horizontal > marks indicator, scale.vertical > marks indicator { background-color: @mentha_fg_muted; }

/* záhlaví sloupců (ColumnView, TreeView): fg_muted normálním řezem jako GTK3, tónovaná linka */
columnview > header > button > box, treeview.view > header > button > box,
window.print:not(.ssd-frame) treeview.dialog-action-box > header > button > box {
  color: @mentha_fg_muted; font-weight: 400; font-size: inherit; opacity: 1;
}
columnview > header > button:hover > box, treeview.view > header > button:hover > box,
window.print:not(.ssd-frame) treeview.dialog-action-box > header > button:hover > box { color: @window_fg_color; }
columnview > header > button:active > box, treeview.view > header > button:active > box { color: @window_fg_color; }
columnview > header { box-shadow: inset 0 -1px @mentha_border; }
treeview.view > header > button { border-bottom-color: @mentha_border; }
columnview.column-separators > header > button, treeview.column-separators.view > header > button { border-left-color: @mentha_border; }

/* ikonová tlačítka headerbaru: fg_muted jako ovládání okna, na hover plná barva; :checked zůstává accent_text */
headerbar button.image-button:not(.suggested-action):not(.destructive-action):not(:checked),
headerbar menubutton > button.image-button:not(:checked), headerbar menubutton.image-button > button:not(:checked),
headerbar splitbutton:not(.suggested-action):not(.destructive-action) > menubutton > button:not(:checked) { color: @mentha_fg_muted; }
headerbar button.image-button:hover:not(.suggested-action):not(.destructive-action):not(:checked),
headerbar button.image-button:active:not(.suggested-action):not(.destructive-action):not(:checked),
headerbar menubutton > button.image-button:hover:not(:checked), headerbar menubutton > button.image-button:active:not(:checked),
headerbar menubutton.image-button > button:hover:not(:checked), headerbar menubutton.image-button > button:active:not(:checked),
headerbar splitbutton:not(.suggested-action):not(.destructive-action) > menubutton > button:hover:not(:checked) { color: @window_fg_color; }

/* popover: obrys v tokenu border (upstream 14% černé je v Dark neviditelné); .osd má vlastní, vyšší specificitou */
popover > arrow, popover > contents { border-color: @mentha_border; }
popover.menu accelerator { color: @mentha_fg_muted; }
/* akcelerátor na hover/výběru: fg_muted na selection v Dark < 4.5:1 -> plná fg */
popover.menu modelbutton:hover accelerator, popover.menu modelbutton:selected accelerator,
popover.menu modelbutton:active accelerator { color: @mentha_fg; }
/* oddělovač menu: hairline jako GTK3 menu (upstream alpha(currentColor,.15) je tmavší) */
popover.menu separator { background-color: @mentha_hairline; }
/* výška položek jako GTK3 menuitem (min-height 20 + padding 4+4 = 28 px) */
popover.menu modelbutton, popover.menu list > row, popover.menu listview > row { min-height: 28px; }

/* hover řádků a dlaždic: tónovaný token hover, slabší než výběr. GtkTreeView sem nepatří: hover se tam kreslí stavem celého widgetu,
   takže by se tónovalo i záhlaví a podklad výběru */
row.activatable:hover:not(:selected), columnview > listview > row:hover:not(:selected),
gridview > child:hover:not(:selected), flowbox > flowboxchild:hover:not(:selected) { background-color: @mentha_hover; }
/* upstream pravidlo pro boxed-list/content (alpha 0.03) má vyšší specificitu; kopie selektorů, aby hover nebyl slabší než jinde */
list.boxed-list > row:not(:selected).activatable:hover, list.content > row:not(:selected).activatable:hover,
list.boxed-list > row.expander row.header:not(:selected).activatable:hover, list.content > row.expander row.header:not(:selected).activatable:hover,
row.expander list.nested > row:not(:selected).activatable:hover { background-color: @mentha_hover; }
list.boxed-list > row:not(:selected).activatable:active, list.content > row:not(:selected).activatable:active,
list.boxed-list > row.expander row.header:not(:selected).activatable:active, list.content > row.expander row.header:not(:selected).activatable:active,
row.expander list.nested > row:not(:selected).activatable:active { background-color: @mentha_active; }
/* dlaždice: radius md (12 px) jako ostatní povrchy; výběr/hover/fokus ho dědí */
flowbox > flowboxchild, gridview > child { border-radius: __MD__; }

/* focus ring karet s odstupem (řádky .boxed-list zůstávají -2px kvůli overflow) */
.card:focus:focus-visible, button.card:focus:focus-visible { outline-offset: 2px; }

/* váha písma tlačítek 600 jako GTK3/maketa (upstream bold); titulky a záhlaví sloupců mají vlastní pravidla */
button, buttoncontent > box > label, menubutton > button, splitbutton > button { font-weight: 600; }
/* hodnota dropdownu normálním řezem jako GTK3 button.combo */
dropdown > button, dropdown > button label, dropdown > button > box > label { font-weight: 400; }

/* radio a check v popover menu: 16 px jako GTK3 menu (upstream 18), obrys 2px fg_muted (>= 3:1 v L i D);
   check zaškrtnutý = plný akcent s accent_fg, radio zaškrtnuté = obrys 2px akcent + mezera + tečka (SVG z GTK3, jako GTK3 menu);
   selektory delší než upstream (popover.menu check/radio) */
popover.menu modelbutton radio, popover.menu modelbutton check {
  min-width: 16px; min-height: 16px; padding: 0; border: none; -gtk-icon-size: 16px;
  box-shadow: inset 0 0 0 2px @mentha_fg_muted; background-color: transparent; border-color: transparent;
}
popover.menu modelbutton check:checked, popover.menu modelbutton check:indeterminate {
  background-color: @accent_bg_color; color: @accent_fg_color; box-shadow: none;
}
popover.menu modelbutton radio:checked, popover.menu modelbutton radio:indeterminate {
  background-color: transparent; color: @accent_bg_color; box-shadow: none;
  -gtk-icon-source: -gtk-recolor(url("assets/mentha-radio-checked-symbolic.svg"));
}

/* tooltip: tokeny tooltip_bg/fg jako GTK3; v Dark obrys, aby nesplynul s tmavou plochou */
tooltip.background { background-color: @mentha_tooltip_bg; color: @mentha_tooltip_fg; border-radius: __SM__; border-color: @mentha_tooltip_border; }

/* výběr řádků a dlaždic: selection_strong jako seznamy GTK3 (sidebary .navigation-sidebar mají vlastní) */
columnview > listview:not(.navigation-sidebar) > row:selected, listview:not(.navigation-sidebar) > row:selected,
gridview > child:selected, flowbox > flowboxchild:selected, treeview.view:not(.navigation-sidebar):selected,
listview:not(.navigation-sidebar) > row.activatable:selected:hover, gridview > child:selected:hover,
flowbox > flowboxchild:selected:hover { background-color: @mentha_selection_strong; }

/* focus ring řádků boxed-list/list.content leží uvnitř karty (selektor jako upstream, -1px přetékal přes hranu); -4 px: každý řádek má border-bottom 1px, ring (2 px) tak končí 1 px nad oddělovačem a ne na něm) */
list.boxed-list > row:focus:focus-visible, list.content > row:focus:focus-visible,
list.boxed-list > row.expander row.header:focus:focus-visible, list.content > row.expander row.header:focus:focus-visible,
row.expander list.nested > row:focus:focus-visible { outline-offset: -4px; }
/* spin/entry řádky (AdwSpinRow, AdwEntryRow) mají vlastní pravidlo .focused s -1px */
row.entry.focused, row.spin.focused, row.entry.error.focused, row.spin.error.focused,
row.entry.warning.focused, row.spin.warning.focused, row.entry.success.focused, row.spin.success.focused { outline-offset: -4px; }

/* popover: radius lg jako GTK3; stín contents z tokenu (SHADOWS), šipka jen lehký stín (offset 12 px by u šipky nedával smysl) */
popover > contents { border-radius: __LG__; }
popover > arrow { box-shadow: 0 1px 5px 1px alpha(@mentha_shadow_tint, 0.09); }

/* GTK4 šipky: obrysový chevron jako GTK3. -gtk-icontheme (hicolor z install.sh) drží poměr 16x16; -gtk-recolor(url) by se roztáhlo do alokace uzlu arrow */
dropdown arrow, combobox arrow, menubutton arrow.down, splitbutton > menubutton > button > arrow.none {
  -gtk-icon-source: -gtk-icontheme("mentha-chevron-down-symbolic"); color: @mentha_fg_muted;
}
menubutton arrow.up { -gtk-icon-source: -gtk-icontheme("mentha-chevron-up-symbolic"); color: @mentha_fg_muted; }
menubutton arrow.left, popover.menu modelbutton arrow.left { -gtk-icon-source: -gtk-icontheme("mentha-chevron-left-symbolic"); }
menubutton arrow.right, popover.menu modelbutton arrow.right { -gtk-icon-source: -gtk-icontheme("mentha-chevron-right-symbolic"); }
menubutton arrow.left, menubutton arrow.right, popover.menu modelbutton arrow { color: @mentha_fg_muted; opacity: 1; }
popover.menu modelbutton arrow:disabled { opacity: 0.5; }
/* AdwComboRow: šipka je GtkImage s pevným icon-name (-gtk-icon-source se ignoruje) -> glyf skrýt filtrem a chevron kreslit jako pozadí */
row.combo image.dropdown-arrow {
  -gtk-icon-filter: opacity(0); min-width: 16px; min-height: 16px; color: @mentha_fg_muted;
  background-image: -gtk-recolor(url("assets/mentha-chevron-down-symbolic.svg")); background-repeat: no-repeat;
  background-position: center; background-size: 16px 16px;
}
expander, treeview.view.expander { -gtk-icon-source: -gtk-icontheme("mentha-chevron-right-symbolic"); color: @mentha_fg_muted; opacity: 1; }
expander:dir(rtl), treeview.view.expander:dir(rtl) { -gtk-icon-source: -gtk-icontheme("mentha-chevron-left-symbolic"); }
expander:checked, treeview.view.expander:checked { -gtk-icon-source: -gtk-icontheme("mentha-chevron-down-symbolic"); }
expander:hover, treeview.view.expander:hover { color: @window_fg_color; }
"""


SRC_ASSETS = ROOT / "src/gtk/assets"


def winctl_glyphs():
    """Glyfy tlačítek titulku shodné s GTK3 (assety mentha-win-* z gtk vrstvy; bez assetu se pravidlo nevygeneruje).
    Image má pevný icon-name, takže -gtk-icon-source by se ignoroval: nativní glyf se skryje filtrem a náš se kreslí jako pozadí."""
    have = lambda n: (SRC_ASSETS / f"mentha-win-{n}-symbolic.svg").exists()
    bg = lambda n: f'background-image: -gtk-recolor(url("assets/mentha-win-{n}-symbolic.svg"));'
    out = []
    if all(have(n) for n in ("minimize", "maximize", "close")):
        out.append("windowcontrols > button > image { -gtk-icon-filter: opacity(0); background-repeat: no-repeat; "
                   "background-position: center; background-size: 16px 16px; }")
        out += [f"windowcontrols > button.{n} > image {{ {bg(n)} }}" for n in ("minimize", "maximize", "close")]
        if have("restore"):
            out.append(f"window.maximized windowcontrols > button.maximize > image {{ {bg('restore')} }}")
    return "\n".join(out) + "\n" if out else ""


def overrides():
    return (OVERRIDES.replace("__SM__", RADIUS["sm"]).replace("__XS__", RADIUS["xs"])
            .replace("__PILL__", RADIUS["pill"]).replace("__LG__", RADIUS["lg"]).replace("__MD__", RADIUS["md"]))


# Stíny: upstream černé alpha stíny (neutrálně šedé na světlém podkladu) -> tón z tokenů. Přepisují se přímo v upstreamových
# pravidlech (selektor i pořadí zůstanou, takže .maximized/.tiled/.osd dál vyhrávají). (začátek pravidla, nový box-shadow)
SHADOWS = [
    ("shortcut > .keycap, list.boxed-list, list.content", "0 0 0 1px alpha(@mentha_shadow_tint, 0.04), "
     "0 1px 3px 1px alpha(@mentha_shadow_tint, 0.08), 0 2px 6px 2px alpha(@mentha_shadow_tint, 0.04)"),
    ("popover > arrow, popover > contents", "0 12px 28px @mentha_shadow_popup"),
    ("window.csd {", "0 16px 36px @mentha_shadow_window, 0 0 0 1px alpha(@mentha_shadow_tint, 0.06)"),
    ("window.csd:backdrop {", "0 8px 20px @mentha_shadow_window_backdrop, 0 0 0 1px alpha(@mentha_shadow_tint, 0.04)"),
    ("window.csd.dialog.message,", "0 8px 24px @mentha_shadow_popup, 0 0 0 1px alpha(@mentha_shadow_tint, 0.06)"),
]
SH_RE = re.compile(r"box-shadow:[^;]*;")


def shadows(text, label):
    lines = text.split("\n")
    for start, new in SHADOWS:
        idx = [i for i, l in enumerate(lines) if l.startswith(start) and "box-shadow:" in l]
        if len(idx) != 1:
            raise SystemExit(f"{label}: stín '{start}' nalezen {len(idx)}x, čekáno 1x (upstream se změnil?)")
        lines[idx[0]] = SH_RE.sub(lambda _m: f"box-shadow: {new};", lines[idx[0]], count=1)
    return "\n".join(lines)


def build():
    for theme in THEMES:
        for ver in VERSIONS:
            src, dst = UP / f"libadwaita-{ver}", DIST / theme / f"libadwaita-{ver}"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            for a in SRC_ASSETS.glob("mentha-*.svg"):   # chevrony a glyfy titulku sdílené s gtk-3.0/4.0 (jeden zdroj)
                shutil.copy(a, dst / "assets" / a.name)
            counts = {"btn": 0, "win": 0, "wc": 0, "state": 0, "focus": 0}
            for name in ("base.css", "base-hc.css"):
                txt = shadows(patch_base((src / name).read_text(), counts), f"{theme}/{ver}/{name}")
                (dst / name).write_text(txt.rstrip("\n") + "\n" + WINCTL + winctl_glyphs() + GRAD + overrides())
            for var in VARIANTS:
                f = f"defaults-{var}.css"
                (dst / f).write_text(recolor_defaults((src / f).read_text(), var, ver))
            print(f"{theme}/libadwaita-{ver}: radii změněno {counts['btn']}x (tlačítka/entry), "
                  f"okno {counts['win']}x, windowcontrols odstraněno {counts['wc']}x, "
                  f"stavy tlačítek {counts['state']}x, focus {counts['focus']}x")
            if counts["state"] < len(BTN_STATES):   # upstream se změnil -> upravit BTN_STATES, ne mlčet
                raise SystemExit(f"{theme}/{ver}: přepsáno {counts['state']} stavů tlačítek, čekáno >= {len(BTN_STATES)}")


# ---------- validace ----------
SKIP_AT = {"define-color", "keyframes", "media", "import", "charset", "supports"}


def names(text):
    return set(re.findall(r"@define-color\s+(\w+)", text))


def used(text):
    t = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return {n for n in re.findall(r"@([A-Za-z_][\w-]*)", t) if n not in SKIP_AT}


def check():
    ok = True
    # 1) reference
    for theme in THEMES:
        for ver in VERSIONS:
            d = DIST / theme / f"libadwaita-{ver}"
            for base in ("base.css", "base-hc.css"):
                for var in VARIANTS:
                    b, df = (d / base).read_text(), (d / f"defaults-{var}.css").read_text()
                    undef = (used(b) | used(df)) - (names(b) | names(df))
                    if undef:
                        ok = False
                        print(f"FAIL undefined @names {theme}/{ver} {base}+{var}: {sorted(undef)}")
    print("[1] reference @name: " + ("OK" if ok else "FAIL"))
    # 2) mint zelená
    pat = re.compile(r"35a854|rgb\(\s*53[ ,]+168[ ,]+84|\b53\s+168\s+84\b", re.I)
    bad = [str(p.relative_to(ROOT)) for t in THEMES for v in VERSIONS
           for p in (DIST / t / f"libadwaita-{v}").rglob("*.css") if pat.search(p.read_text())]
    if bad:
        ok = False
    print("[2] Mint green (#35A854): " + ("OK, žádná" if not bad else f"FAIL {bad}"))
    # 3) tabulka
    keys = ["accent_bg_color", "accent_color", "window_bg_color", "view_bg_color", "headerbar_bg_color",
            "sidebar_bg_color", "card_bg_color", "popover_bg_color", "window_fg_color", "error_bg_color",
            "success_color", "warning_color", "shade_color"]
    print("\n[3] klíčové barvy (libadwaita-1.5; 1.7 stejné kromě odkazů)")
    print(f"{'color':<20}{'defaults-light':<26}{'defaults-dark':<26}")
    vals = {}
    for var in VARIANTS:
        txt = (DIST / "Mentha-Light/libadwaita-1.5" / f"defaults-{var}.css").read_text()
        vals[var] = dict(re.findall(r"@define-color\s+(\w+)\s+(.*);", txt))
    for k in keys:
        print(f"{k:<20}{vals['light'].get(k, '-'):<26}{vals['dark'].get(k, '-'):<26}")
    # 4) Light a Dark složky shodné
    for ver in VERSIONS:
        r = shutil.which("diff") and __import__("subprocess").run(
            ["diff", "-rq", str(DIST / "Mentha-Light" / f"libadwaita-{ver}"),
             str(DIST / "Mentha-Dark" / f"libadwaita-{ver}")], capture_output=True)
        same = r.returncode == 0
        ok &= same
        print(f"[4] Light == Dark libadwaita-{ver}: {'OK' if same else 'FAIL'}")
    # 5) kontrasty
    print("\n[5] kontrast (>=4.5 text, >=3 UI)")
    for var in VARIANTS:
        t, p = TOK[var], palette(var)
        pairs = [("window_fg/window_bg", t["fg"], p["window_bg_color"], 4.5),
                 ("accent_fg/accent_bg", p["accent_fg_color"], p["accent_bg_color"], 4.5),
                 ("accent_color/window_bg", p["accent_color"], p["window_bg_color"], 4.5),
                 ("error_fg/error_bg", p["error_fg_color"], p["error_bg_color"], 4.5),
                 ("error_color/view_bg", p["error_color"], p["view_bg_color"], 4.5),
                 ("success_color/view_bg", p["success_color"], p["view_bg_color"], 4.5),
                 ("warning_color/view_bg", p["warning_color"], p["view_bg_color"], 4.5),
                 ("fg_muted/card", p["mentha_fg_muted"], p["card_bg_color"], 4.5),
                 ("fg_muted/card_raised", p["mentha_fg_muted"], p["mentha_card_raised"], 4.5),
                 ("track/card_raised (UI)", p["mentha_track"], p["mentha_card_raised"], 1.2),
                 ("track/window_bg (UI)", p["mentha_track"], p["window_bg_color"], 1.2),
                 ("track/view_bg (UI)", p["mentha_track"], p["view_bg_color"], 1.2),
                 ("track/card_bg (UI)", p["mentha_track"], p["card_bg_color"], 1.2),
                 ("track/dialog (UI)", p["mentha_track"], p["dialog_bg_color"], 1.2),
                 # výplně se měří proti ploše okna (>= 3:1), dráha je jen světlý tvar (kolo 8, CTRL-701); parita s gtk-validate.py
                 ("level_low/window_bg (UI)", p["mentha_level_low"], p["window_bg_color"], 3),
                 ("level_high/window_bg (UI)", p["mentha_level_high"], p["window_bg_color"], 3),
                 ("grad_from/window_bg (UI)", p["mentha_grad_from"], p["window_bg_color"], 3),
                 ("grad_to/window_bg (UI)", p["mentha_grad_to"], p["window_bg_color"], 3),
                 ("accent/track (UI)", p["accent_bg_color"], p["mentha_track"], 1.6),
                 ("grad_to/track (UI, info)", p["mentha_grad_to"], p["mentha_track"], 1.6),
                 ("switch_off_card/card_raised (UI)", p["mentha_switch_off_card"], p["mentha_card_raised"], 1.5),
                 ("border_strong/card (UI)", p["mentha_border_strong"], p["card_bg_color"], 3),
                 ("border_strong/view (UI)", p["mentha_border_strong"], p["view_bg_color"], 3),
                 ("switch_knob/border_strong", p["mentha_switch_knob"], p["mentha_border_strong"], 3),
                 ("accent_fg(knob)/accent (UI)", p["accent_fg_color"], p["accent_bg_color"], 3),
                 # hover vypnutého switche: bílý jezdec >= 3:1 jen v Dark; Light má vědomě světlou dráhu (kolo 8, PLSH-704: off 1,84:1, stav nese poloha jezdce)
                 ("switch_knob/switch_off_hover (UI)", p["mentha_switch_knob"], p["mentha_switch_off_hover"], 3 if var == "dark" else 1),
                 ("fg_muted/view_bg", p["mentha_fg_muted"], p["view_bg_color"], 4.5),
                 ("fg_muted/popover", p["mentha_fg_muted"], p["popover_bg_color"], 4.5),
                 ("control_border/surface", p["mentha_control_border"], p["mentha_surface"], 3)]
        for n, a, b, need in pairs:
            if a.startswith("rgba"):
                continue
            c = contrast(parse(a), parse(b))
            print(f"  {var:<5}{n:<26}{c:5.2f}  {'ok' if c >= need else 'LOW'}")
        # gradient výplní musí být okem vidět: odstín grad_from -> grad_to o >= 12° (parita s gtk-validate.py)
        h = lambda c: __import__("colorsys").rgb_to_hsv(*[x / 255 for x in parse(c)])[0] * 360
        dh = abs(h(p["mentha_grad_from"]) - h(p["mentha_grad_to"]))
        dh = min(dh, 360 - dh)
        good = dh >= 12
        ok &= good
        print(f"  {var:<5}{'grad ΔHue':<26}{dh:5.1f}° {'ok' if good else 'LOW (<12°)'}")
        # přechod se v obou variantách rozjasňuje do azurové (kolo 8, parita s gtk-validate.py)
        up = lum(parse(p["mentha_grad_to"])) > lum(parse(p["mentha_grad_from"]))
        ok &= up
        print(f"  {var:<5}{'grad zesvětluje':<26}{'ok' if up else 'FAIL (tmavne)'}")
    sys.exit(0 if ok else 1)


ACCENT = None
if __name__ == "__main__":
    ACCENT = SRC["default_accent"]
    import os
    ACCENT = os.environ.get("MENTHA_ACCENT") or ACCENT
    {"build": build, "check": check}[sys.argv[1] if len(sys.argv) > 1 else "build"]()
