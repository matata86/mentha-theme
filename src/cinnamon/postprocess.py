#!/usr/bin/env python3
"""Mentha: úprava zkompilovaného cinnamon.css pro St (libcroco).
 - rgb(12.3%, ...) / rgba(1.5, ...) -> celá čísla 0-255 (St umí jen celá čísla a procenta bez desetin není jisté)
 - odstraní deklarace opacity (St je nezná), @charset a sourcemap komentáře
Použití: postprocess.py in.css out.css
"""
import re, sys

src = open(sys.argv[1], encoding="utf-8").read()


def chan(v):
    v = v.strip()
    if v.endswith("%"):
        return max(0, min(255, round(float(v[:-1]) * 2.55)))
    return max(0, min(255, round(float(v))))


def fix(m):
    name, args = m.group(1), m.group(2)
    if "/" in args or " " in args.strip() and "," not in args:
        raise SystemExit(f"nepodporovaná syntaxe barvy: {m.group(0)}")
    parts = [p.strip() for p in args.split(",")]
    rgb = [str(chan(p)) for p in parts[:3]]
    if len(parts) == 4:
        a = parts[3]
        a = float(a[:-1]) / 100 if a.endswith("%") else float(a)
        return f"rgba({', '.join(rgb)}, {round(a, 3):g})"
    return f"rgb({', '.join(rgb)})"


src = re.sub(r"\b(rgba?)\(([^()]*)\)", fix, src)
# upstream nechává opacity (St ho ignoruje) -> pryč
src = re.sub(r"^[ \t]*opacity:[^;]*;\n", "", src, flags=re.M)
src = re.sub(r"@charset[^;]*;\s*", "", src)
src = re.sub(r"/\*# sourceMappingURL=.*?\*/", "", src)
open(sys.argv[2], "w", encoding="utf-8").write(src)
