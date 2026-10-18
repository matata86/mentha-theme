#!/usr/bin/env python3
"""Motiv launcheru Albert (widgetsboxmodel, Albert 35) z tokenů Menthy.

Vyrobí „Mentha Light.ini“ a „Mentha Dark.ini“ ze šablony src/albert/theme.ini.in
(barvy jen přes $token) a do configu Alberta zapíše geometrii ze src/albert/geometry.ini.in.

Použití: tools/albert-theme.py [--accent blue] [--themes DIR] [--config FILE | --no-config]
Akcent: --accent, jinak $MENTHA_ACCENT, jinak tokens.json default_accent.
Albert config čte jen při startu: po změně geometrie Albert restartovat.
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
HOME = os.path.expanduser("~")
RGBA = re.compile(r"rgba\(\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\)")
SHADOW = re.compile(r"^\s*0\s+(\d+)px\s+(\d+)px\s+(rgba\(.*\))\s*$")


def argb(value):
    """'#RRGGBB' nebo 'rgba(r, g, b, a)' -> Qt '#RRGGBB' / '#AARRGGBB'."""
    if value.startswith("#") and len(value) == 7:
        return value.upper()
    m = RGBA.fullmatch(value.strip())
    if not m:
        raise ValueError(f"neznámý formát barvy: {value}")
    r, g, b, a = int(m[1]), int(m[2]), int(m[3]), float(m[4])
    return f"#{round(a * 255):02X}{r:02X}{g:02X}{b:02X}"


def mix(c1, c2, w):
    """Sass mix() pro neprůhledné barvy: w podílu c1."""
    a, b = (int(c1[i:i + 2], 16) for i in (1, 3, 5)), (int(c2[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(x * w + y * (1 - w)):02X}" for x, y in zip(a, b))


def shadow(value):
    m = SHADOW.match(value)
    if not m:
        raise ValueError(f"neznámý formát stínu: {value}")
    return int(m[1]), int(m[2]), argb(m[3])


def palette(tokens, variant, accent):
    t = dict(tokens["base"][variant])
    t.update(tokens["accents"][accent][variant])
    out = {k: argb(v) for k, v in t.items() if v.startswith(("#", "rgba("))}
    out["shadow_popup"] = shadow(t["shadow_popup"])[2]
    # vybraný text v poli = $mt-text-sel-entry z _mentha-gtk.scss
    out["text_sel_entry"] = mix(out["accent"], out["surface_alt"], 0.34)
    return out


def render_theme(template, colors, name):
    used = sorted(set(re.findall(r"^\w+=\$(\w+)$", template, re.M)))
    missing = [u for u in used if u not in colors]
    if missing:
        raise KeyError(f"šablona odkazuje na neexistující tokeny: {missing}")
    head = [f"; {name} — generováno tools/albert-theme.py z src/tokens.json, needitovat ručně.", ""]
    head += [f"{u}={colors[u]}" for u in used]
    return "\n".join(head) + "\n\n" + template


def merge_config(path, values):
    """Přepíše/doplní klíče v sekci [widgetsboxmodel]; ostatní řádky nechá beze změny."""
    lines = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []
    if "[widgetsboxmodel]" not in lines:
        lines += ["", "[widgetsboxmodel]"]
    start = lines.index("[widgetsboxmodel]") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("[")), len(lines))
    todo = dict(values)
    for i in range(start, end):
        key = lines[i].split("=", 1)[0]
        if key in todo:
            lines[i] = f"{key}={todo.pop(key)}"
    while end > start and not lines[end - 1].strip():
        end -= 1
    lines[end:end] = [f"{k}={v}" for k, v in sorted(todo.items())]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    assert argb("rgba(43, 111, 240, 0.125)") == "#202B6FF0" and argb("#2b6ff0") == "#2B6FF0"
    assert mix("#FF0000", "#0000FF", 0.25) == "#4000BF"
    assert shadow("0 12px 28px rgba(24, 40, 80, 0.16)") == (12, 28, "#29182850")

    tokens = json.load(open(os.path.join(SRC, "tokens.json"), encoding="utf-8"))
    ap = argparse.ArgumentParser(description="Motiv Albert z tokenů Menthy")
    ap.add_argument("--accent", default=os.environ.get("MENTHA_ACCENT", tokens["default_accent"]))
    ap.add_argument("--themes", default=os.path.join(HOME, ".local/share/albert/widgetsboxmodel/themes"))
    ap.add_argument("--config", default=os.path.join(HOME, ".config/albert/config"))
    ap.add_argument("--no-config", action="store_true", help="geometrii do configu nezapisovat")
    args = ap.parse_args()

    template = open(os.path.join(SRC, "albert/theme.ini.in"), encoding="utf-8").read()
    suffix = "" if args.accent == tokens["default_accent"] else f" {args.accent}"
    names = {}
    os.makedirs(args.themes, exist_ok=True)
    for variant in ("light", "dark"):
        name = f"Mentha {variant.title()}{suffix}"
        path = os.path.join(args.themes, name + ".ini")
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_theme(template, palette(tokens, variant, args.accent), name))
        names[variant] = name
        print(path)

    if args.no_config:
        return
    shadows = [shadow(tokens["base"][v]["shadow_popup"]) for v in ("light", "dark")]
    fill = {f"radius_{k}": int(v.rstrip("px")) for k, v in tokens["radius"].items() if v.endswith("px")}
    fill["shadow_offset"] = max(s[0] for s in shadows)
    fill["shadow_blur"] = 3 * max(s[1] for s in shadows)  # Albert blur ≈ CSS blur / 3
    values = {}
    for line in open(os.path.join(SRC, "albert/geometry.ini.in"), encoding="utf-8"):
        if "=" in line and not line.startswith(";"):
            key, val = line.rstrip("\n").split("=", 1)
            values[key] = val.format(**fill)
    values["lightTheme"], values["darkTheme"] = names["light"], names["dark"]
    merge_config(args.config, values)
    print(args.config)


if __name__ == "__main__":
    main()
