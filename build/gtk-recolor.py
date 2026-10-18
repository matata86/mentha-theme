#!/usr/bin/env python3
"""Mentha GTK helper: recolor Orchis accent in PNG assets and write the GTK2 gtkrc.

  gtk-recolor.py png  <variant> <src_dir> <dst_dir>   # recolor *.png (blue/green -> accent)
  gtk-recolor.py rc   <variant> <src_gtkrc> <dst_gtkrc>
Colors come from build/gen/tokens-<variant>.json (accent swappable via gen-tokens.py).
"""
import colorsys, json, os, re, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
# Orchis accent hexes (blue light/dark, green check light/dark): the only colors we replace
ORCHIS = ["#1A73E8", "#3281EA", "#0F9D58", "#81C995"]


def tok(variant):
    return json.load(open(os.path.join(HERE, "gen", f"tokens-{variant}.json")))


def hex_of(c):
    """'#RRGGBB' | 'rgba(r,g,b,a)' -> '#RRGGBB' (alpha dropped; GTK2 has no alpha colors)."""
    c = c.strip()
    if c.startswith("#"):
        return c.upper()
    r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", c)[:3]]
    return "#%02X%02X%02X" % (r, g, b)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def recolor_png(src, dst, accent):
    ha, la, sa = colorsys.rgb_to_hls(*rgb(accent))
    bases = [(colorsys.rgb_to_hls(*rgb(b)), b) for b in ORCHIS]
    im = Image.open(src).convert("RGBA")
    px = im.load()
    cache = {}
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0 or max(r, g, b) - min(r, g, b) < 24:
                continue                      # neutral (grey/white/black) stays
            key = (r, g, b)
            if key not in cache:
                h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
                (bh, bl, bs), _ = min(bases, key=lambda t: min(abs(t[0][0] - h), 1 - abs(t[0][0] - h)))
                nl = min(1.0, max(0.0, l + (la - bl)))
                ns = min(1.0, s * (sa / bs if bs else 1))
                cache[key] = tuple(int(round(v * 255)) for v in colorsys.hls_to_rgb(ha, nl, ns))
            px[x, y] = cache[key] + (a,)
    im.save(dst)


def cmd_png(variant, src_dir, dst_dir):
    accent = hex_of(tok(variant)["accent"])
    os.makedirs(dst_dir, exist_ok=True)
    for f in sorted(os.listdir(src_dir)):
        if f.endswith(".png"):
            recolor_png(os.path.join(src_dir, f), os.path.join(dst_dir, f), accent)


def cmd_rc(variant, src, dst):
    t = tok(variant)
    h = lambda k: hex_of(t[k])
    scheme = {
        "text_color": h("fg"), "base_color": h("surface"),
        "fg_color": h("fg"), "bg_color": h("surface"),
        "selected_fg_color": h("accent_fg"), "selected_bg_color": h("accent"),
        "titlebar_fg_color": h("fg"), "titlebar_bg_color": h("surface"),
        "menu_color": h("surface_raised"),
        "tooltip_fg_color": h("tooltip_fg"), "tooltip_bg_color": h("tooltip_bg"),
        "link_color": h("accent_text"), "visited_link_color": h("accent_pressed"),
    }
    out = []
    for line in open(src):
        if line.startswith("gtk-color-scheme"):
            def sub(m):
                k = m.group(1)
                return f"{k}:{scheme[k]}" if k in scheme else m.group(0)
            line = re.sub(r"(?:(?<=\")|(?<=\\n))([a-z_]+_color):#[0-9A-Fa-f]{6}", sub, line)
        out.append(line)
    text = "".join(out)
    for o in ORCHIS:                          # zbylé natvrdo psané akcenty
        text = text.replace(o, h("accent")).replace(o.lower(), h("accent"))
    open(dst, "w").write(text)


if __name__ == "__main__":
    {"png": cmd_png, "rc": cmd_rc}[sys.argv[1]](*sys.argv[2:])
