#!/usr/bin/env python3
"""Validace GTK výstupu: parse gtk-3.0 (Gtk 3 CssProvider) a gtk-4.0 (libgtk-4 přes ctypes, gi typelib 4.0
není nainstalován), dále WCAG kontrast textu na akcentu/chybové barvě z tokens.json. Padne na jakoukoli chybu."""
import sys, glob, json, subprocess, ctypes
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

bad = 0

def report(f, errs):
    global bad
    print(f"{f}: {'OK' if not errs else str(len(errs)) + ' ERRORS'}")
    for e in errs[:15]:
        print("   ", e)
    bad += bool(errs)

# ---- gtk-3.0
files3 = sorted(glob.glob("dist/Mentha-*/gtk-3.0/gtk*.css"))
for f in files3:
    errs = []
    p = Gtk.CssProvider()
    p.connect("parsing-error", lambda prov, sec, err: errs.append(f"{sec.get_start_line()+1}:{sec.get_start_position()}: {err.message}"))
    try:
        p.load_from_path(f)
    except Exception as e:
        errs.append(str(e))
    report(f, errs)

# ---- gtk-4.0: vlastní proces (Gtk 3 a 4 nelze v jednom), ctypes nad libgtk-4
G4 = r'''
import ctypes, sys
gtk = ctypes.CDLL("libgtk-4.so.1"); gob = ctypes.CDLL("libgobject-2.0.so.0")
gtk.gtk_css_provider_new.restype = ctypes.c_void_p
gtk.gtk_css_section_get_start_location.restype = ctypes.POINTER(ctypes.c_size_t * 5)
gtk.gtk_css_section_get_start_location.argtypes = [ctypes.c_void_p]
gtk.gtk_css_provider_load_from_path.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
gob.g_signal_connect_data.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
class GErr(ctypes.Structure): _fields_ = [("d", ctypes.c_uint32), ("c", ctypes.c_int), ("m", ctypes.c_char_p)]
CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GErr), ctypes.c_void_p)
errs = []
def cb(p, s, e, d):
    loc = gtk.gtk_css_section_get_start_location(s).contents   # bytes, chars, lines, line_bytes, line_chars
    errs.append(f"{loc[2]+1}:{loc[4]}: {e.contents.m.decode()}")
cbp = CB(cb)
p = gtk.gtk_css_provider_new()
gob.g_signal_connect_data(p, b"parsing-error", ctypes.cast(cbp, ctypes.c_void_p), None, None, 0)
gtk.gtk_css_provider_load_from_path(p, sys.argv[1].encode())
print("\n".join(errs))
'''
for f in sorted(glob.glob("dist/Mentha-*/gtk-4.0/gtk*.css")):
    r = subprocess.run([sys.executable, "-c", G4, f], capture_output=True, text=True)
    errs = [l for l in r.stdout.splitlines() if l.strip()]
    if r.returncode != 0:
        errs.append(f"validátor gtk-4.0 spadl ({r.returncode}): {r.stderr.strip()[-200:]}")
    report(f, errs)

# ---- kontrast (WCAG 2.x), 4.5:1
def lum(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
T = json.load(open("src/tokens.json"))
errs = []
for var in ("light", "dark"):
    base = T["base"][var]
    for name, acc in T["accents"].items():
        a = acc[var]
        pairs = [("accent_fg", a["accent_fg"], k, a[k]) for k in ("accent", "accent_hover", "accent_pressed")]
        pairs += [("error_fg", base["error_fg"], k, base[k]) for k in ("error", "error_hover", "error_pressed")]
        for fgn, fg, bgn, bg in pairs:
            r = ratio(fg, bg)
            if r < 4.5:
                errs.append(f"{name}/{var}: {fgn} na {bgn} = {r:.2f}:1 (<4.5)")
report("kontrast tokenů (>= 4.5:1)", errs)

# ---- hrany, dráhy (>= 3:1 / 2:1 / 1.8:1) a výběr textu (mix akcentu na surface)
def hx(h):
    h = h.lstrip("#"); return [int(h[i:i+2], 16) for i in (0, 2, 4)]
def mix(a, b, pct):   # Sass mix(a, b, pct): pct % barvy a
    w = pct / 100
    return "#" + "".join(f"{round(x * w + y * (1 - w)):02X}" for x, y in zip(hx(a), hx(b)))
def rgba(v):   # "rgba(r, g, b, a)" -> (r, g, b, a)
    n = [float(x) for x in v[v.index("(") + 1:-1].split(",")]
    return n[0], n[1], n[2], n[3]
def over(rgb, alpha, bg):   # průhledná barva přes plochu
    return "#" + "".join(f"{round(c * alpha + b * (1 - alpha)):02X}" for c, b in zip(rgb, hx(bg)))
errs = []
for var in ("light", "dark"):
    base = T["base"][var]
    def chk(name, fg, bgs, mn):
        for bn in bgs:
            r = ratio(fg, base[bn])
            if r < mn:
                errs.append(f"{var}: {name} na {bn} = {r:.2f}:1 (<{mn})")
    chk("border_strong", base["border_strong"], ("surface", "surface_alt", "dialog_bg"), 3.0)
    # dráha je jen světlý tvar (kolo 8, CTRL-701/PLSH-704): hranu ukazatele nese výplň vůči ploše (>= 3:1) a jezdec
    chk("track", base["track"], ("surface", "surface_alt", "dialog_bg", "surface_raised", "bg"), 1.2)
    if var == "dark":   # karta v libadwaita = mix(surface_raised, fg, 4 %)
        card = mix(base["fg"], base["surface_raised"], 4)
        if ratio(base["track"], card) < 1.2:
            errs.append(f"{var}: track na card_raised = {ratio(base['track'], card):.2f}:1 (<1.2)")
    # levelbar .low/.full: plná výplň (ne text) -> >= 3:1 vůči ploše okna (WCAG 1.4.11), ne vůči dráze
    chk("level_low", base["level_low"], ("surface", "dialog_bg"), 3.0)
    chk("level_high", base["level_high"], ("surface", "dialog_bg"), 3.0)
    chk("switch_off_hover", base["switch_off_hover"], ("switch_off",), 1.2)   # hover o krok výraznější než klid
    if var == "dark":   # prstenec jezdce scale = mezera v barvě plochy (CTRL-713): odliší jezdec od výplně i dráhy
        chk("slider_ring", base["slider_ring"], ("track",), 1.5)
    chk("track_soft", base["track_soft"], ("surface", "surface_alt", "dialog_bg"), 1.1)   # světlá dráha ukazatelů, jen tvar
    chk("control_border", base["control_border"], ("surface", "dialog_bg"), 1.8)
    for name, acc in T["accents"].items():
        a = acc[var]
        sel = mix(a["accent"], base["surface"], 33)          # výběr textu v entry/label/textview
        if ratio(sel, base["surface"]) < 1.5:
            errs.append(f"{name}/{var}: výběr textu vůči surface = {ratio(sel, base['surface']):.2f}:1 (<1.5)")
        if ratio(base["fg"], sel) < 4.5:
            errs.append(f"{name}/{var}: fg na výběru textu = {ratio(base['fg'], sel):.2f}:1 (<4.5)")
        for k in ("grad_from",):   # text přes výplň začíná na grad_from; konec (azur) nese jen tvar
            if ratio(a["grad_fg"], a[k]) < 4.5:
                errs.append(f"{name}/{var}: grad_fg na {k} = {ratio(a['grad_fg'], a[k]):.2f}:1 (<4.5)")
        # kolo 8 (CTRL-701, A11Y-701): výplň se měří proti ploše okna, ne proti dráze; >= 3:1 musí držet
        # celá výplň včetně konce gradientu (Light grad_to = nejbližší azur s 3:1 vůči surface)
        for k in ("grad_from", "grad_to", "disk_fill"):
            for bn in ("surface", "dialog_bg"):
                if ratio(a[k], base[bn]) < 3.0:
                    errs.append(f"{name}/{var}: {k} na {bn} = {ratio(a[k], base[bn]):.2f}:1 (<3.0)")
        # gradient musí být okem vidět jako změna odstínu, ne jen ztmavení (kolo 7, D2)
        import colorsys
        hue = lambda c: colorsys.rgb_to_hsv(*[x / 255 for x in hx(c)])[0] * 360
        dh = abs(hue(a["grad_from"]) - hue(a["grad_to"]))
        dh = min(dh, 360 - dh)
        print(f"  {name}/{var}: ΔHue grad_from->grad_to = {dh:.1f}°")
        if dh < 12:
            errs.append(f"{name}/{var}: ΔHue grad_from->grad_to = {dh:.1f}° (<12)")
        # parita L/D (kolo 8, PLSH-702): přechod se v obou variantách rozjasňuje do azurové, netmavne
        if lum(a["grad_to"]) <= lum(a["grad_from"]):
            errs.append(f"{name}/{var}: grad_to není světlejší než grad_from (přechod tmavne)")
        if var == "dark" and ratio(base["slider_ring"], a["grad_to"]) < 3.0:
            errs.append(f"{name}/{var}: slider_ring na grad_to = {ratio(base['slider_ring'], a['grad_to']):.2f}:1 (<3.0)")
        if var == "dark":   # jezdec vůči kartě nese sám akcent (prstenec je mezera v barvě plochy)
            card = mix(base["fg"], base["surface_raised"], 4)
            if ratio(a["accent"], card) < 3.0:
                errs.append(f"{name}/{var}: accent (jezdec) na card = {ratio(a['accent'], card):.2f}:1 (<3.0)")
        for k in ("accent", "grad_from"):
            if ratio(a[k], base["track"]) < 1.6:
                errs.append(f"{name}/{var}: {k} na track = {ratio(a[k], base['track']):.2f}:1 (<1.6)")
        # výběr sidebaru (Nemo, Terminál): text >= 5:1, nad hoverem >= 1,1:1, vůči podkladu >= 1,2:1
        sr, sg, sb, sa = rgba(a["selection_sidebar"])
        hr, hg, hb, ha = rgba(base["sidebar_hover"])
        for bn in ("surface_alt", "surface"):
            ss = over((sr, sg, sb), sa, base[bn])
            hh = over((hr, hg, hb), ha, base[bn])
            for what, r, mn in (("selection_text na selection_sidebar", ratio(a["selection_text"], ss), 5.0),
                                ("selection_sidebar vůči sidebar_hover", ratio(ss, hh), 1.10),
                                ("selection_sidebar vůči podkladu", ratio(ss, base[bn]), 1.2)):
                if r < mn:
                    errs.append(f"{name}/{var}: {what}/{bn} = {r:.2f}:1 (<{mn})")
        # sidebar: fg na výběru (selection přes surface_alt) >= 4.5, hover zřetelně slabší než výběr
        sr, sg, sb, sa = rgba(a["selection"])
        selr = over((sr, sg, sb), sa, base["surface_alt"])
        if ratio(base["fg"], selr) < 4.5:
            errs.append(f"{name}/{var}: fg na selection/surface_alt = {ratio(base['fg'], selr):.2f}:1 (<4.5)")
        # vybraný řádek sidebaru má text accent_text (D2, P5-30)
        if ratio(a["accent_text"], selr) < 4.5:
            errs.append(f"{name}/{var}: accent_text na selection/surface_alt = {ratio(a['accent_text'], selr):.2f}:1 (<4.5)")
        hr, hg, hb, ha = rgba(base["sidebar_hover"])
        hov = over((hr, hg, hb), ha, base["surface_alt"])   # $mt-sidebar-hover
        rs, rh = ratio(selr, base["surface_alt"]), ratio(hov, base["surface_alt"])
        if rs - rh < 0.07:
            errs.append(f"{name}/{var}: sidebar výběr {rs:.3f} - hover {rh:.3f} < 0.07")
        # silný výběr řádku (rgba přes plochu): vůči surface_alt i surface >= 1.5:1, fg na něm >= 7:1
        sr, sg, sb, sa = rgba(a["selection_strong"])
        for bn in ("surface", "surface_alt"):
            sel = over((sr, sg, sb), sa, base[bn])
            if ratio(sel, base[bn]) < 1.5:
                errs.append(f"{name}/{var}: selection_strong na {bn} = {ratio(sel, base[bn]):.2f}:1 (<1.5)")
            if ratio(base["fg"], sel) < 7:
                errs.append(f"{name}/{var}: fg na selection_strong/{bn} = {ratio(base['fg'], sel):.2f}:1 (<7)")
        # vybraný text v entry s výplní surface_alt (mix 34 % akcentu)
        sel = mix(a["accent"], base["surface_alt"], 34)
        if ratio(sel, base["surface_alt"]) < 1.5:
            errs.append(f"{name}/{var}: výběr textu vůči surface_alt = {ratio(sel, base['surface_alt']):.2f}:1 (<1.5)")
        if ratio(base["fg"], sel) < 4.5:
            errs.append(f"{name}/{var}: fg na výběru textu/surface_alt = {ratio(base['fg'], sel):.2f}:1 (<4.5)")
        # progress buňka v treeview: výplň = mix 55 % akcentu na surface, text fg přes výplň i dráhu
        cell = mix(a["accent"], base["surface"], 55)
        if ratio(base["fg"], cell) < 4.5:
            errs.append(f"{name}/{var}: fg na výplni progress buňky = {ratio(base['fg'], cell):.2f}:1 (<4.5)")
        if ratio(cell, base["surface"]) < 2.0:
            errs.append(f"{name}/{var}: výplň progress buňky vůči ploše = {ratio(cell, base['surface']):.2f}:1 (<2.0)")
        # dráha buňky = surface s obrysem control_border (P5-19)
        if ratio(base["fg"], base["surface"]) < 4.5:
            errs.append(f"{var}: fg na dráze progress buňky = {ratio(base['fg'], base['surface']):.2f}:1 (<4.5)")
        if ratio(base["control_border"], base["surface"]) < 1.8:
            errs.append(f"{var}: obrys dráhy progress buňky = {ratio(base['control_border'], base['surface']):.2f}:1 (<1.8)")
report("hrany, dráhy, výběr textu, grad_fg", errs)

sys.exit(1 if bad or not files3 else 0)
