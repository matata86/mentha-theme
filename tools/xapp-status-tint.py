#!/usr/bin/env python3
"""Lokální přepis appletu xapp-status@cinnamon.org: jednobarevné tray pixmapy kreslí barvou textu panelu.

Proč: Electron aplikace (Claude desktop, Discord) posílají do traye hotový bílý/černý obrázek (IconPixmap),
motiv ikon na ně nemá vliv -> na světlém panelu bílá ikona mizí. Claude navíc volí barvu obráceně
(Light = bílá, Dark = černá). Přepis z obrázku udělá masku (bílá i černá ikona) a obarví ji barvou
textu panelu, stejně jako symbolické ikony. Barevné ikony (Nextcloud, Syncthing...) nechá beze změny,
malý barevný odznak (nepřečtené v Discordu) zachová.

Cinnamon hledá applety nejdřív v ~/.local/share/cinnamon/applets, kopie tam přebije systémový.
Přepis se generuje ze systémového applet.js -> po aktualizaci Cinnamonu skript spustit znovu.
Návrat: rm -r ~/.local/share/cinnamon/applets/xapp-status@cinnamon.org a ReloadXlet (viz níž).

Použití: python3 tools/xapp-status-tint.py   (zapíše přepis a přenačte applet)
"""
import os, shutil, subprocess

UUID = "xapp-status@cinnamon.org"
SRC = f"/usr/share/cinnamon/applets/{UUID}"
DST = os.path.expanduser(f"~/.local/share/cinnamon/applets/{UUID}")

TINT_FN = r'''const GdkPixbuf = imports.gi.GdkPixbuf;

// Mentha: jednobarevná pixmapa -> maska obarvená barvou textu panelu (jako symbolická ikona).
// Vrací cestu k novému PNG, nebo null u barevné ikony. Barevné pixely (odznak) nechává.
let menthaTintSerial = 0;
function menthaTint(path, fg) {
    let pb;
    try { pb = GdkPixbuf.Pixbuf.new_from_file(path); } catch (e) { return null; }
    if (!pb.get_has_alpha() || pb.get_bits_per_sample() !== 8)
        return null;
    let w = pb.get_width(), h = pb.get_height(), rs = pb.get_rowstride(), px = pb.get_pixels();
    let isColor = i => Math.max(px[i], px[i + 1], px[i + 2]) - Math.min(px[i], px[i + 1], px[i + 2]) > 48;
    let lumOf = i => 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2];
    let grey = 0, color = 0, lum = 0;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            let i = y * rs + x * 4, a = px[i + 3];
            if (a < 32) continue;
            if (isColor(i)) { color += a; continue; }
            grey += a;
            lum += a * lumOf(i);
        }
    }
    if (grey === 0 || color > grey / 3)
        return null;
    // světlá ikona (bílá) -> kreslí světlé pixely; tmavá (černá) -> kreslí tmavé; obrys opačného tónu zmizí
    let light = lum / grey > 128;
    let out = new Uint8Array(px.length);
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            let i = y * rs + x * 4, a = px[i + 3];
            if (a >= 32 && isColor(i)) {
                out.set(px.subarray(i, i + 4), i);
                continue;
            }
            let m = lumOf(i) / 255;
            out[i] = fg.red; out[i + 1] = fg.green; out[i + 2] = fg.blue;
            out[i + 3] = Math.round(a * (light ? m : 1 - m));
        }
    }
    let file = `${GLib.get_user_runtime_dir()}/mentha-tray-${++menthaTintSerial}.png`;
    try {
        GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(out), GdkPixbuf.Colorspace.RGB, true, 8, w, h, rs)
            .savev(file, "png", [], []);
    } catch (e) {
        global.logError(`xapp-status (Mentha): ${e}`);
        return null;
    }
    return file;
}
'''

TINT_METHOD = r'''
    // Mentha: pixmapu z cesty obarvit barvou textu panelu (při změně motivu znovu, viz style-changed)
    _menthaTintIcon(path) {
        let node = this.actor.peek_theme_node();
        if (!node)
            return path;
        let c = node.get_foreground_color();
        this._menthaFg = `${c.red},${c.green},${c.blue}`;
        let out = menthaTint(path, c);
        if (this._menthaFile)
            GLib.unlink(this._menthaFile);
        this._menthaFile = out;
        return out || path;
    }

    setIconName(iconName) {'''

STYLE_HOOK = r'''this.actor.connect('enter-event', Lang.bind(this, this.onEnterEvent));
        this.actor.connect('style-changed', () => {
            let node = this.actor.peek_theme_node(), c = node && node.get_foreground_color();
            if (c && this.iconName && this.iconName.includes("/") && `${c.red},${c.green},${c.blue}` !== this._menthaFg)
                this.setIconName(this.iconName);
        });'''

LOAD_OLD = '''            if (iconName.includes("/") && type != St.IconType.SYMBOLIC) {
                this.icon_loader_handle = St.TextureCache.get_default().load_image_from_file_async(
                    iconName,'''
LOAD_NEW = '''            if (iconName.includes("/") && type != St.IconType.SYMBOLIC) {
                this.icon_loader_handle = St.TextureCache.get_default().load_image_from_file_async(
                    this._menthaTintIcon(iconName),'''


def patch(js):
    edits = [
        ("const Tooltips = imports.ui.tooltips;\n", "const Tooltips = imports.ui.tooltips;\n" + TINT_FN, 1),
        ("\n    setIconName(iconName) {", TINT_METHOD, None),
        ("this.actor.connect('enter-event', Lang.bind(this, this.onEnterEvent));", STYLE_HOOK, None),
        (LOAD_OLD, LOAD_NEW, 1),
    ]
    for old, new, _ in edits:
        n = js.count(old)
        # setIconName a enter-event mají i RecorderIcon? -> přepisujeme jen ve třídě XAppStatusIcon
        if n == 0:
            raise SystemExit(f"Kotva nenalezena (změnil se systémový applet?): {old.strip()[:60]}")
    head, sep, tail = js.partition("class XAppStatusIcon {")
    if not sep:
        raise SystemExit("Třída XAppStatusIcon nenalezena")
    head = head.replace(edits[0][0], edits[0][1], 1)
    for old, new, _ in edits[1:]:
        if tail.count(old) != 1:
            raise SystemExit(f"Kotva ve XAppStatusIcon není jednoznačná: {old.strip()[:60]}")
        tail = tail.replace(old, new, 1)
    return head + sep + tail


if __name__ == "__main__":
    js = open(f"{SRC}/applet.js").read()
    out = patch(js)
    os.makedirs(DST, exist_ok=True)
    shutil.copy(f"{SRC}/metadata.json", DST)
    with open(f"{DST}/applet.js", "w") as f:
        f.write("// Mentha: GENEROVÁNO z /usr/share/cinnamon/applets/xapp-status@cinnamon.org skriptem\n"
                "// ~/.local/src/mentha-theme/tools/xapp-status-tint.py — needitovat ručně.\n" + out)
    subprocess.run(["gdbus", "call", "--session", "--dest", "org.Cinnamon", "--object-path", "/org/Cinnamon",
                    "--method", "org.Cinnamon.ReloadXlet", UUID, "APPLET"], check=False, stdout=subprocess.DEVNULL)
    print(f"Zapsáno {DST}/applet.js, applet přenačten.")
