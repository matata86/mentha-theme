#!/usr/bin/env python3
"""Barevné varianty akcentu podle Tela-circle (vinceliuice, install.sh): z modré sady v tokens.json
odvodí sady dalších barev a zapíše je do tokens.json → accents.<barva>.

Každý token modré sady se převede do OKLCH, odstín se otočí na odstín barvy Tela (gradient se otáčí
o vlastní posun, viz GRAD), sytost se ořízne do gamutu sRGB a světlost se dopočítá tak, aby relativní
luminance (WCAG) byla stejná jako u modré. U průhledných tokenů (rgba) se shoduje luminance výsledku
přes surface_alt. Kontrasty vůči base tokenům proto drží jako u modré; ověřuje je build/gtk-validate.py
(prochází všechny akcenty).

Použití: build/gen-accents.py   (přepíše accents kromě blue)
"""
import json, math

TELA = {   # Tela-circle install.sh: theme_color
    "green": "#66bb6a", "teal": "#16a085", "purple": "#7e57c2", "pink": "#f06292",
    "red": "#ef5350", "orange": "#ff9800", "yellow": "#ffca28", "grey": "#bdbdbd",
}
GRAD = {   # posun odstínu grad_to proti grad_from (modrá: −25° do azurové); teplé barvy jdou k oranžové, oranžová k červené (ke žluté je konec olivový)
    "green": 25, "teal": -25, "purple": -25, "pink": 25, "red": 30, "orange": 28, "yellow": -20, "grey": -25,
}
# tmavá oranžová: začátek přechodu o kus k červené, jinak je změna odstínu k zlaté v HSV pod prahem 12°
GRAD_FROM = {"orange": (0, -14)}
CHROMA = {"grey": 0.22}   # násobek sytosti modré (šedá = břidlicová, jen nádech modré)
# odstín místo Tela: Tela grey je neutrální; oranžová a žlutá Tela jsou při luminanci modré (bílý text 4,5:1)
# hnědé/olivové, posun k červené dává pálenou oranžovou a zlatou; v tmavé variantě (světlý akcent) odstín Tela drží
HUE = {"grey": (255, 255), "orange": (48, 62), "yellow": (78, 88)}
# rezerva: modrá leží těsně nad prahy validátoru, zaokrouhlení u jiných odstínů je shazovalo pod ně;
# ve světlé variantě se text a výplně o kousek ztmaví (vyšší kontrast vůči surface i výběru)
MARGIN = {"accent_text": 0.97, "selection_text": 0.97, "grad_from": 0.98, "grad_to": 0.98, "disk_fill": 0.98}

def s2l(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def l2s(c): return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
def to_oklch(rgb):
    r, g, b = (s2l(x / 255) for x in rgb)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360
def from_oklch(L, C, h):   # -> lineární RGB (může být mimo gamut)
    A, B = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
def lum(rgb): return sum(k * s2l(x / 255) for k, x in zip((0.2126, 0.7152, 0.0722), rgb))
def in_gamut(rgb): return all(-1e-6 <= x <= 1 + 1e-6 for x in rgb)
def to255(lin): return tuple(round(255 * l2s(min(1, max(0, x)))) for x in lin)
def over(rgb, alpha, bg): return tuple(round(c * alpha + b * (1 - alpha)) for c, b in zip(rgb, bg))

def match(Y, C, h, f=lum):
    """Barva s odstínem h a sytostí nejvýš C, pro kterou f(barva) = Y (ořez do gamutu snižuje sytost)."""
    while True:
        lo, hi = 0.0, 1.0
        for _ in range(50):   # světlost, při které f dává cílovou luminanci
            mid = (lo + hi) / 2
            if f(to255(from_oklch(mid, C, h))) < Y: lo = mid
            else: hi = mid
        if in_gamut(from_oklch(hi, C, h)) or C < 1e-3: return to255(from_oklch(hi, C, h))
        C *= 0.97

def hx(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def parse(v):
    if v.startswith("#"): return hx(v), None
    n = [x.strip() for x in v[v.index("(") + 1:-1].split(",")]
    return tuple(int(x) for x in n[:3]), n[3]
def fmt(rgb, alpha):
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}" if alpha is None else f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha})"

def derive(blue, base, name):
    h_ref = to_oklch(hx(blue["light"]["accent"]))[2]
    g_ref = to_oklch(hx(blue["light"]["grad_to"]))[2] - to_oklch(hx(blue["light"]["grad_from"]))[2]
    out = {}
    for var in ("light", "dark"):
        out[var] = {}
        under = hx(base[var]["surface_alt"])
        h_new = HUE[name][var == "dark"] if name in HUE else to_oklch(hx(TELA[name]))[2]
        for k, v in blue[var].items():
            rgb, alpha = parse(v)
            if rgb == (255, 255, 255): out[var][k] = v; continue   # bílý text na akcentu
            _, C, h = to_oklch(rgb)
            h2 = h - h_ref + h_new
            if k == "grad_to": h2 += GRAD[name] - g_ref
            if k == "grad_from": h2 += GRAD_FROM.get(name, (0, 0))[var == "dark"]
            C *= CHROMA.get(name, 1.0)
            if alpha is None:
                m = MARGIN.get(k, 1.0) if var == "light" else 1.0
                out[var][k] = fmt(match(lum(rgb) * m, C, h2), None)
            else:
                a = float(alpha)
                f = lambda c: lum(over(c, a, under))
                out[var][k] = fmt(match(f(rgb), C, h2, f), alpha)
    return out

if __name__ == "__main__":
    p = "src/tokens.json"
    t = json.load(open(p))
    t["accents"] = {"blue": t["accents"]["blue"], **{n: derive(t["accents"]["blue"], t["base"], n) for n in TELA}}
    with open(p, "w") as fh:
        json.dump(t, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for n, a in t["accents"].items():
        print(f"{n:7} light {a['light']['accent']} {a['light']['accent_fg']}  dark {a['dark']['accent']} {a['dark']['accent_fg']}")
