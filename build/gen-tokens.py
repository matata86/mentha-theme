#!/usr/bin/env python3
"""tokens.json -> build/gen/_mentha-tokens.scss (+ tokens-<variant>.json pro skripty).

Použití: gen-tokens.py [accent]   (výchozí z tokens.json / env MENTHA_ACCENT)
SCSS: `$variant` musí být nastaven před @import; pak `mt(accent)`, `mt-radius(md)`.
"""
import json, os, sys, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
t = json.loads((root / "src/tokens.json").read_text())
accent = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get("MENTHA_ACCENT") or t["default_accent"]
if accent not in t["accents"]:
    sys.exit(f"neznámý akcent {accent!r}, dostupné: {', '.join(t['accents'])}")

out = root / "build/gen"
out.mkdir(parents=True, exist_ok=True)

def scss_map(d):
    return "(\n" + "".join(f'  "{k}": {v},\n' for k, v in d.items()) + ")"

lines = [f"// GENEROVÁNO z src/tokens.json (akcent: {accent}) — needitovat"]
for var in ("light", "dark"):
    merged = {**t["base"][var], **t["accents"][accent][var]}
    (out / f"tokens-{var}.json").write_text(json.dumps(merged, indent=1))
    lines.append(f"$mt-{var}: {scss_map(merged)};")
lines.append(f"$mt-radius: {scss_map(t['radius'])};")
lines.append(f'$mt-font-ui: "{t["font"]["ui"]}";\n$mt-font-display: "{t["font"]["display"]}";\n$mt-font-mono: "{t["font"]["mono"]}";')
lines.append("""@function mt($key) {
  $m: if($variant == 'light', $mt-light, $mt-dark);
  @if not map-has-key($m, $key) { @error "mentha token '#{$key}' neexistuje"; }
  @return map-get($m, $key);
}
@function mt-radius($key) { @return map-get($mt-radius, $key); }""")
(out / "_mentha-tokens.scss").write_text("\n".join(lines) + "\n")
print(f"tokens -> {out} (akcent {accent})")
