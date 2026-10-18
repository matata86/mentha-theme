#!/usr/bin/env python3
"""Mentha: generuje SVG/PNG assety Cinnamon shell motivu z tokenů (žádný hardcode akcentu).

Použití: gen-assets.py <light|dark> <výstupní cinnamon/ složka>
Čte build/gen/tokens-<variant>.json (vytváří build/gen-tokens.py).
Zapisuje jen assety, na které cinnamon.css odkazuje:
  common-assets/misc/*  (close, add-workspace, calendar-arrow, trash, corner-ripple)
  <variant>-assets/{checkbox,switch,misc}/*
a thumbnail.png (247x60).
"""
import json, pathlib, re, sys

root = pathlib.Path(__file__).resolve().parent.parent.parent
variant, out = sys.argv[1], pathlib.Path(sys.argv[2])
T = json.loads((root / f"build/gen/tokens-{variant}.json").read_text())


def parse(c):
    """'#RRGGBB' | 'rgba(r, g, b, a)' -> ('#rrggbb', alpha)"""
    c = c.strip()
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)", c)
    if m:
        r, g, b = (round(float(m.group(i))) for i in (1, 2, 3))
        return f"#{r:02x}{g:02x}{b:02x}", float(m.group(4) or 1)
    if re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        return c.lower(), 1.0
    raise ValueError(f"neznámá barva {c!r}")


def fill(tok, mult=1.0):
    h, a = parse(T[tok])
    a *= mult
    return f'fill="{h}"' + (f' fill-opacity="{a:.3f}"' if a < 1 else "")


def stroke(tok, w, mult=1.0):
    h, a = parse(T[tok])
    a *= mult
    return f'stroke="{h}" stroke-width="{w}"' + (f' stroke-opacity="{a:.3f}"' if a < 1 else "")


def hexof(tok):
    return parse(T[tok])[0]


def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'{("<defs>" + defs + "</defs>") if defs else ""}{body}</svg>\n')


def put(rel, text):
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


# ---------------------------------------------------------------- checkbox / radio (16x16)
CHECK = 'M4.2 8.4 L6.9 11 L11.9 5.2'
box = lambda fl, st: f'<rect x="1.5" y="1.5" width="13" height="13" rx="4.5" {fl} {st}/>'
tick = f'<path d="{CHECK}" fill="none" stroke="{hexof("accent_fg")}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
ring = lambda col: f'<rect x="0.5" y="0.5" width="15" height="15" rx="5.5" fill="none" {stroke(col, 1, 0.35)}/>'
cb = f"{variant}-assets/checkbox"
put(f"{cb}/checkbox-unchecked.svg", svg(16, 16, box('fill="none"', stroke("fg_muted", 1.5, 0.75))))
put(f"{cb}/checkbox-unchecked-focused.svg", svg(16, 16, box('fill="none"', stroke("focus", 2))))
put(f"{cb}/checkbox-checked.svg", svg(16, 16, box(fill("accent"), stroke("accent", 1.5)) + tick))
put(f"{cb}/checkbox-checked-focused.svg", svg(16, 16, ring("focus") + box(fill("accent_pressed"), stroke("accent_pressed", 1.5)) + tick))
put(f"{cb}/radio-unchecked.svg", svg(16, 16, f'<circle cx="8" cy="8" r="6.5" fill="none" {stroke("fg_muted", 1.5, 0.75)}/>'))
put(f"{cb}/radio-checked.svg", svg(16, 16,
    f'<circle cx="8" cy="8" r="7" {fill("accent")}/>'
    f'<circle cx="8" cy="8" r="2.8" fill="{hexof("accent_fg")}"/>'))

# ---------------------------------------------------------------- switch (44x24, vlastní plochý knob)
def switch(on):
    track = fill("accent") if on else fill("border")
    cx = 32 if on else 12
    return svg(44, 24,
        f'<rect x="0" y="0" width="44" height="24" rx="12" {track}/>'
        + ('' if on else f'<rect x="0.5" y="0.5" width="43" height="23" rx="11.5" fill="none" {stroke("fg_muted", 1, 0.35)}/>')
        + f'<circle cx="{cx}" cy="13" r="9" fill="#000" fill-opacity="0.18"/>'
        f'<circle cx="{cx}" cy="12" r="9" fill="#ffffff"/>')
put(f"{variant}-assets/switch/switch-on.svg", switch(True))
put(f"{variant}-assets/switch/switch-off.svg", switch(False))

# ---------------------------------------------------------------- message.svg (border-image 9px, notifikace v popupu)
put(f"{variant}-assets/misc/message.svg", svg(32, 32,
    f'<rect x="0.5" y="0.5" width="31" height="31" rx="9" {fill("surface_alt")} {stroke("hairline", 1)}/>'))

# ---------------------------------------------------------------- dock indikátor (svislý panel, 3x42)
# svislá linka přilepená k vnitřní hraně ostrova (levá strana rovná, pravá zaoblená: rect přesahuje viewBox doleva);
# 42 = výška dlaždice při ikoně 36 + padding podkladu 2x3. _mentha-shell.scss dává background-size: contain ->
# při jiné výšce dlaždice se SVG škáluje a linka zůstane ve středu.
def dock_line(tok, h):
    return svg(3, 42, f'<rect x="-2" y="{(42 - h) / 2:g}" width="5" height="{h}" rx="2" {fill(tok)}/>')
put(f"{variant}-assets/misc/dock-running.svg", dock_line("fg_muted", 10))
put(f"{variant}-assets/misc/dock-focused.svg", dock_line("accent", 20))

# ---------------------------------------------------------------- common: close (26x26)
def close(state):
    bg = {"n": fill("surface_raised"), "h": fill("error"), "a": fill("error", 0.8)}[state]
    border = stroke("border", 1) if state == "n" else 'stroke="none"'
    xcol = hexof("fg") if state == "n" else hexof("error_fg")
    return svg(26, 26,
        f'<circle cx="13" cy="13" r="12" {bg} {border}/>'
        f'<path d="M9 9 L17 17 M17 9 L9 17" stroke="{xcol}" stroke-width="2" stroke-linecap="round"/>')
put("common-assets/misc/close.svg", close("n"))
put("common-assets/misc/close-hover.svg", close("h"))
put("common-assets/misc/close-active.svg", close("a"))

# ---------------------------------------------------------------- common: add-workspace (35x200)
def addws(state):
    bg = {"n": fill("surface_raised", 0.9), "h": fill("accent_soft"), "a": fill("selection")}[state]
    pc = hexof("fg_muted") if state == "n" else hexof("accent_text")
    return svg(35, 200,
        f'<rect x="1" y="1" width="33" height="198" rx="16" {bg} {stroke("border", 1)}/>'
        f'<path d="M17.5 92 V108 M9.5 100 H25.5" stroke="{pc}" stroke-width="2.4" stroke-linecap="round"/>')
put("common-assets/misc/add-workspace.svg", addws("n"))
put("common-assets/misc/add-workspace-hover.svg", addws("h"))
put("common-assets/misc/add-workspace-active.svg", addws("a"))

# ---------------------------------------------------------------- common: calendar šipky (16x16)
def arrow(direction, hover):
    col = hexof("accent_text") if hover else hexof("fg_muted")
    d = "M10 3.5 L5.5 8 L10 12.5" if direction == "left" else "M6 3.5 L10.5 8 L6 12.5"
    return svg(16, 16, f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
for d in ("left", "right"):
    put(f"common-assets/misc/calendar-arrow-{d}.svg", arrow(d, False))
    put(f"common-assets/misc/calendar-arrow-{d}-hover.svg", arrow(d, True))

# ---------------------------------------------------------------- common: trash (400x120, zóna pro zavření okna v expo)
put("common-assets/misc/trash-icon.svg", svg(400, 120,
    f'<rect x="1" y="-30" width="398" height="149" rx="28" {fill("error", 0.16)} {stroke("error", 1.5, 0.6)}/>'
    f'<g transform="translate(176 36)" fill="none" stroke="{hexof("error")}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
    f'<path d="M4 12 H44 M18 12 V6 H30 V12 M10 12 L12 46 H36 L38 12 M20 22 V38 M28 22 V38"/></g>'))

# ---------------------------------------------------------------- common: hot-corner ripple (104x104)
put("common-assets/misc/corner-ripple.svg", svg(104, 104,
    f'<circle cx="0" cy="0" r="104" fill="url(#g)"/>',
    f'<radialGradient id="g" cx="0" cy="0" r="104" gradientUnits="userSpaceOnUse">'
    f'<stop offset="0" stop-color="{hexof("accent")}" stop-opacity="0.55"/>'
    f'<stop offset="1" stop-color="{hexof("accent")}" stop-opacity="0"/></radialGradient>'))

# ---------------------------------------------------------------- hot-corner ikona (neutrální šedá, beze změny z upstreamu)
import shutil
up = root / "upstream/mint-themes/src/Mint-Y/cinnamon/common-assets/misc"
for f in ("overview.png", "overview-hover.png"):
    (out / "common-assets/misc").mkdir(parents=True, exist_ok=True)
    shutil.copy(up / f, out / "common-assets/misc" / f)

# ---------------------------------------------------------------- thumbnail.png (247x60), kreslí PIL, 2x supersampling
from PIL import Image, ImageDraw

S = 3
W, H = 247 * S, 60 * S
rgba = lambda tok, mult=1.0: (*[int(parse(T[tok])[0][i:i + 2], 16) for i in (1, 3, 5)], int(255 * parse(T[tok])[1] * mult))
img = Image.new("RGBA", (W, H), rgba("bg"))
d = ImageDraw.Draw(img, "RGBA")
# jemný akcentový přechod pozadí (jen náhled)
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([W * 0.55, -H * 1.4, W * 1.25, H * 0.9], fill=rgba("accent", 0.22))
gd.ellipse([-W * 0.25, H * 0.3, W * 0.35, H * 2.0], fill=rgba("grad_to", 0.16))
img.alpha_composite(glow)
d = ImageDraw.Draw(img, "RGBA")
rr = lambda box, r, **kw: d.rounded_rectangle([v * S for v in box], radius=r * S, **kw)
isl = rgba("island")
isl = (*isl[:3], 235)  # náhled bez průhlednosti, ať je čitelný
line = rgba("hairline")
# horní lišta: tři ostrovy
rr((6, 5, 62, 21), 8, fill=isl, outline=line, width=S)
rr((9, 8, 21, 18), 4, fill=rgba("accent"))
rr((26, 11, 36, 15), 2, fill=rgba("fg_muted"))
rr((40, 11, 56, 15), 2, fill=rgba("fg_muted"))
rr((97, 5, 150, 21), 8, fill=isl, outline=line, width=S)
rr((104, 11, 143, 15), 2, fill=rgba("fg"))
rr((177, 5, 241, 21), 8, fill=isl, outline=line, width=S)
for i in range(4):
    rr((184 + i * 14, 9, 192 + i * 14, 17), 4, fill=rgba("fg_muted"))
# dock vlevo
rr((6, 27, 28, 56), 8, fill=isl, outline=line, width=S)
rr((9, 30, 25, 40), 4, fill=rgba("accent_soft"))
rr((8, 32, 10, 38), 1, fill=rgba("accent"))
rr((10, 43, 24, 53), 4, fill=rgba("hover"))
# popup menu
rr((40, 28, 120, 56), 8, fill=rgba("surface_raised"), outline=line, width=S)
rr((46, 33, 114, 40), 3, fill=rgba("selection"))
rr((46, 44, 100, 48), 2, fill=rgba("fg_muted", 0.6))
# notifikace
rr((150, 28, 241, 56), 8, fill=rgba("surface_raised"), outline=line, width=S)
rr((150, 28, 153, 56), 1, fill=rgba("accent"))
rr((160, 34, 200, 38), 2, fill=rgba("fg"))
rr((160, 42, 228, 45), 1, fill=rgba("fg_muted", 0.6))
rr((160, 48, 184, 53), 3, fill=rgba("accent"))
img = img.resize((247, 60), Image.LANCZOS).convert("RGB")
out.mkdir(parents=True, exist_ok=True)
img.save(out / "thumbnail.png")
print(f"assets {variant} -> {out}")
