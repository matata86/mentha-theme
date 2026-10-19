#!/usr/bin/env python3
"""GTK3 galerie widgetů pro vizuální audit motivu Mentha.

Použití: gallery3.py --page NAME   (jedna stránka = jedno okno, obsah vyplní ~1400x1000)
Stránky: buttons entries toggles lists containers headerbar popovers menus typography
         dlg-message dlg-filechooser dlg-about dlg-color
Stavy (hover, active, focus, disabled, backdrop) se vynucují přes widget.set_state_flags
po zobrazení okna; každý řádek má štítek. Popovery a menu se otevírají programově po startu.
"""
import argparse
import os
import sys

os.environ.setdefault("GTK_OVERLAY_SCROLLING", "0")   # viditelné posuvníky
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

SF = Gtk.StateFlags
HOME = os.path.expanduser("~")
# (štítek, příznaky)
S_ALL = [("normal", SF.NORMAL), ("hover", SF.PRELIGHT), ("active", SF.ACTIVE),
         ("focus", SF.FOCUSED), ("disabled", SF.INSENSITIVE), ("backdrop", SF.BACKDROP)]
S_ENTRY = [("normal", SF.NORMAL), ("hover", SF.PRELIGHT), ("focus", SF.FOCUSED),
           ("disabled", SF.INSENSITIVE), ("backdrop", SF.BACKDROP)]
FORCED = []   # (widget, flags)
KBD = {}      # druh -> widget, který dostane skutečný fokus z klávesnice (--kbd-focus)
KEEP = []     # reference na pomocné widgety mimo okno (leader radio skupiny)


def kbd(name, w):
    KBD.setdefault(name, w)
    return w


def force(w, flags):
    if flags != SF.NORMAL:
        FORCED.append((w, flags))
    return w


def apply_forced():
    for w, f in FORCED:
        if f & SF.INSENSITIVE:
            w.set_sensitive(False)
        else:
            w.set_state_flags(f, False)
    return False


def lbl(text, cls=None, markup=False, xalign=0.0):
    l = Gtk.Label(xalign=xalign)
    if markup:
        l.set_markup(text)
    else:
        l.set_text(text)
    if cls:
        l.get_style_context().add_class(cls)
    return l


def small(text, wc=22):
    l = Gtk.Label(xalign=0.0)
    l.set_markup(f'<span size="small" alpha="70%">{GLib.markup_escape_text(text)}</span>')
    if wc:
        l.set_width_chars(wc)
    return l


def head(text):
    l = Gtk.Label(xalign=0.0)
    l.set_markup(f'<b>{GLib.markup_escape_text(text)}</b>')
    l.set_margin_top(10)
    return l


class Sheet(Gtk.Grid):
    """Mřížka: štítek řádku + buňky; hlavička sloupců se stavy."""

    def __init__(self):
        super().__init__(column_spacing=12, row_spacing=6, margin=16)
        self.r = 0

    def cols(self, names):
        self.attach(Gtk.Label(), 0, self.r, 1, 1)
        for i, n in enumerate(names):
            self.attach(small(n.upper(), 0), i + 1, self.r, 1, 1)
        self.r += 1

    def section(self, text):
        self.attach(head(text), 0, self.r, 8, 1)
        self.r += 1

    def row(self, label, widgets):
        self.attach(small(label), 0, self.r, 1, 1)
        for i, w in enumerate(widgets):
            w.set_halign(Gtk.Align.START)
            w.set_valign(Gtk.Align.CENTER)
            self.attach(w, i + 1, self.r, 1, 1)
        self.r += 1

    def wide(self, label, widgets):
        """Řádek s širokými widgety: vše v jednom boxu přes všechny sloupce (nerozšiřuje sloupce se stavy)."""
        self.attach(small(label), 0, self.r, 1, 1)
        box = Gtk.Box(spacing=24)
        for w in widgets:
            w.set_valign(Gtk.Align.CENTER)
            box.add(w)
        self.attach(box, 1, self.r, 6, 1)
        self.r += 1

    def states(self, label, factory, states=S_ALL, kbd_name=None):
        ws = [force(factory(), f) for _, f in states]
        if kbd_name:
            kbd(kbd_name, [w for w, (_, f) in zip(ws, states) if f & SF.FOCUSED][0])
        self.row(label, ws)


def icon_btn(name, cls=None):
    b = Gtk.Button.new_from_icon_name(name, Gtk.IconSize.BUTTON)
    if cls:
        b.get_style_context().add_class(cls)
    return b


def styled(w, *classes):
    for c in classes:
        w.get_style_context().add_class(c)
    return w


def label_icon_button(text, icon):
    b = Gtk.Button()
    box = Gtk.Box(spacing=6)
    box.add(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
    box.add(Gtk.Label(label=text))
    b.add(box)
    return b


def menu_model():
    m = Gio.Menu()
    m.append("Nový dokument", "g.new")
    m.append("Otevřít…", "g.open")
    s = Gio.Menu()
    s.append("Zobrazit skryté", "g.hidden")
    s.append("Řádkování", "g.spacing")
    m.append_section(None, s)
    m.append("Ukončit", "g.quit")
    return m


# --------------------------------------------------------------------------- stránky

def page_buttons(win):
    sh = Sheet()
    sh.cols([n for n, _ in S_ALL])
    sh.section("Tlačítka")
    sh.states("button", lambda: Gtk.Button(label="Tlačítko"), kbd_name="button")
    sh.states("suggested-action", lambda: styled(Gtk.Button(label="Uložit"), "suggested-action"), kbd_name="suggested")
    sh.states("destructive-action", lambda: styled(Gtk.Button(label="Smazat"), "destructive-action"))
    sh.states("flat", lambda: styled(Gtk.Button(label="Ploché"), "flat"))
    sh.states("ikona + text", lambda: label_icon_button("Otevřít", "document-open-symbolic"))
    sh.states("image (ikona)", lambda: icon_btn("edit-copy-symbolic"))
    sh.states("circular", lambda: icon_btn("list-add-symbolic", "circular"))
    sh.states("toggle (off)", lambda: Gtk.ToggleButton(label="Přepínač"))

    def tg():
        b = Gtk.ToggleButton(label="Zapnuto")
        b.set_active(True)
        return b
    sh.states("toggle checked", tg)

    def mb():
        b = Gtk.MenuButton()
        b.set_menu_model(menu_model())
        return b
    sh.states("menu button", mb)
    sh.states("link / font / color", lambda: Gtk.LinkButton.new_with_label("https://example.org", "Odkaz"))

    sh.section("Linked skupiny")

    def linked(*btns, vertical=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL)
        box.get_style_context().add_class("linked")
        for b in btns:
            box.add(b)
        return box

    def lk3():
        return linked(Gtk.Button(label="Levé"), Gtk.Button(label="Střední"), Gtk.Button(label="Pravé"))
    g1 = lk3(); kbd("linked", g1.get_children()[1])
    g2 = lk3(); force(g2.get_children()[1], SF.PRELIGHT)
    g3 = linked(Gtk.Button(label="Levé"), tg(), Gtk.Button(label="Pravé"))
    g4 = lk3(); force(g4.get_children()[2], SF.INSENSITIVE)
    g5 = linked(icon_btn("go-previous-symbolic"), icon_btn("go-next-symbolic"))
    g6 = linked(*[Gtk.ToggleButton(label=t) for t in ("Ikony", "Seznam", "Kompakt")])
    g6.get_children()[0].set_active(True)
    sh.wide("linked 3 / hover / checked / disabled", [g1, g2, g3, g4])
    sh.wide("linked ikony / toggle skupina", [g5, g6])

    def pathbar(active, hover=None):
        box = Gtk.Box()
        box.get_style_context().add_class("linked")
        names = ["matata", "System", "FNS projekty", "AAA_CLAUDE"]
        box.add(icon_btn("go-previous-symbolic"))
        for i, n in enumerate(names):
            b = Gtk.ToggleButton()
            inner = Gtk.Box(spacing=6)
            if i == 0:
                inner.add(Gtk.Image.new_from_icon_name("user-home-symbolic", Gtk.IconSize.BUTTON))
            inner.add(Gtk.Label(label=n))
            b.add(inner)
            b.set_active(i == active)
            if hover == i:
                force(b, SF.PRELIGHT)
            box.add(b)
        box.add(icon_btn("go-next-symbolic"))
        return box
    pb0 = pathbar(0); kbd("pathbar", pb0.get_children()[2])   # fokus na neaktivní segment (aktivní má vlastní styl)
    sh.wide("path-bar-like (aktivní 1.)", [pb0])
    sh.wide("path-bar-like (aktivní 4., hover 2.)", [pathbar(3, 1)])
    sh.wide("path-bar-like (backdrop/disabled)", [force(pathbar(0), SF.BACKDROP), force(pathbar(3), SF.INSENSITIVE)])

    tb = Gtk.Toolbar()
    tb.get_style_context().add_class("primary-toolbar")
    for ic in ("go-previous-symbolic", "go-next-symbolic", "go-up-symbolic"):
        tb.insert(Gtk.ToolButton(icon_name=ic), -1)
    tb.insert(Gtk.SeparatorToolItem(), -1)
    t = Gtk.ToggleToolButton(icon_name="view-grid-symbolic"); t.set_active(True); tb.insert(t, -1)
    tb.insert(Gtk.ToggleToolButton(icon_name="view-list-symbolic"), -1)
    tb.insert(Gtk.ToolButton(label="Text", icon_name="document-open-symbolic"), -1)
    tb.set_style(Gtk.ToolbarStyle.BOTH_HORIZ)
    tb.set_hexpand(False)
    sh.wide("Gtk.Toolbar", [tb])
    sh.wide("Color / Font button", [Gtk.ColorButton.new_with_rgba(Gdk.RGBA(0.93, 0.55, 0.15, 1)), Gtk.FontButton(), Gtk.VolumeButton()])
    return sh


def page_entries(win):
    sh = Sheet()
    sh.cols([n for n, _ in S_ENTRY])
    sh.section("Entry")

    def entry(text="Text ve vstupu", ph=None, cls=None, p=None, s=None, prog=None):
        e = Gtk.Entry()
        e.set_text(text)
        if ph:
            e.set_placeholder_text(ph)
        e.set_width_chars(15)
        if cls:
            e.get_style_context().add_class(cls)
        if p:
            e.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, p)
        if s:
            e.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, s)
        if prog is not None:
            e.set_progress_fraction(prog)
        return e
    sh.states("entry", entry, S_ENTRY, kbd_name="entry")
    sh.states("placeholder", lambda: entry("", "Zadejte text…"), S_ENTRY)
    sh.states("error", lambda: entry("Neplatná hodnota", cls="error"), S_ENTRY)
    sh.states("warning", lambda: entry("Pozor", cls="warning"), S_ENTRY)
    sh.states("ikony", lambda: entry("S ikonami", p="folder-symbolic", s="edit-clear-symbolic"), S_ENTRY)
    sh.states("progress", lambda: entry("Nahrávání", prog=0.45), S_ENTRY)

    def sr():
        e = Gtk.SearchEntry()
        e.set_text("hledaný výraz")
        e.set_width_chars(15)
        return e
    sh.states("search entry", sr, S_ENTRY)

    def sp():
        s = Gtk.SpinButton.new_with_range(0, 100, 1)
        s.set_value(42)
        return s
    sh.states("spinbutton", sp, S_ENTRY, kbd_name="spin")

    def spv():
        s = Gtk.SpinButton.new_with_range(0, 100, 1)
        s.set_value(7)
        s.set_orientation(Gtk.Orientation.VERTICAL)
        return s
    sh.states("spinbutton vert.", spv, S_ENTRY)

    def cb():
        c = Gtk.ComboBoxText()
        for t in ("Světlý", "Tmavý", "Automaticky"):
            c.append_text(t)
        c.set_active(0)
        return c
    sh.states("combobox", cb, S_ENTRY, kbd_name="combo")

    def cbe():
        c = Gtk.ComboBoxText.new_with_entry()
        for t in ("Inter", "Noto Sans", "Ubuntu"):
            c.append_text(t)
        c.set_active(0)
        return c
    sh.states("combobox + entry", cbe, S_ENTRY)

    def ro():
        e = entry("Jen pro čtení")
        e.set_editable(False)
        return e
    sh.states("read-only", ro, S_ENTRY)

    sh.section("Víceřádkový text")

    def tv(flags):
        t = Gtk.TextView()
        t.get_buffer().set_text("Víceřádkové pole\nDruhý řádek — Příliš žluťoučký kůň úpěl ďábelské ódy.")
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(220, 70)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(t)
        force(t if flags & SF.FOCUSED else sw, flags)   # fokus patří samotnému TextView, ostatní stavy rámu
        if flags & SF.FOCUSED:
            kbd("textview", t)
        return sw
    sh.row("textview", [tv(f) for _, f in S_ENTRY])
    return sh


def page_toggles(win):
    sh = Sheet()
    sh.cols([n for n, _ in S_ALL])
    sh.section("Check / radio / switch")

    def _mk_check(active, inc):
        c = Gtk.CheckButton(label="Volba")
        c.set_active(active)
        c.set_inconsistent(inc)
        return c
    sh.states("check", lambda: _mk_check(False, False))
    sh.states("check checked", lambda: _mk_check(True, False))
    sh.states("check inconsistent", lambda: _mk_check(False, True))
    def radio(active):
        leader = Gtk.RadioButton(label="Leader")   # mimo okno; follower je tak ve skupině a nevybraný
        KEEP.append(leader)
        r = Gtk.RadioButton.new_with_label_from_widget(leader, "Možnost")
        r.set_active(active)
        return r
    sh.states("radio", lambda: radio(False))
    sh.states("radio checked", lambda: radio(True))

    def sw(on):
        s = Gtk.Switch()
        s.set_active(on)
        return s
    sh.states("switch off", lambda: sw(False))
    sh.states("switch on", lambda: sw(True))

    sh.section("Scale / progress / level / spinner")

    def scale(val=40, vertical=False, marks=True, draw=True):
        s = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        s.set_value(val)
        s.set_draw_value(draw)
        s.set_value_pos(Gtk.PositionType.TOP if not vertical else Gtk.PositionType.RIGHT)
        if marks:
            for v in (0, 25, 50, 75, 100):
                s.add_mark(v, Gtk.PositionType.BOTTOM if not vertical else Gtk.PositionType.LEFT, str(v) if v in (0, 100) else None)
        if vertical:
            s.set_size_request(-1, 110)
            s.set_inverted(True)
        else:
            s.set_size_request(150, -1)
        return s
    sh.states("scale h + marks + hodnota", lambda: scale())
    sh.states("scale h bez hodnoty", lambda: scale(70, marks=False, draw=False))
    sh.states("scale vertikální", lambda: scale(60, vertical=True))

    def pb(frac, text=None):
        p = Gtk.ProgressBar()
        p.set_fraction(frac)
        if text:
            p.set_show_text(True)
            p.set_text(text)
        p.set_size_request(150, -1)
        return p
    sh.states("progressbar", lambda: pb(0.6))
    sh.states("progressbar + text", lambda: pb(0.35, "35 %"))

    def lv(v, discrete=False):
        l = Gtk.LevelBar()
        l.set_min_value(0)
        l.set_max_value(1)
        l.set_value(v)
        if discrete:
            l.set_mode(Gtk.LevelBarMode.DISCRETE)
            l.set_max_value(4)   # Orchis: blok min-width 34 px, 5 bloků by pruh roztáhlo na ~178 px
            l.set_value(v * 4)
        l.set_size_request(150, -1)
        return l
    sh.row("levelbar 0.15 (low)", [force(lv(0.15), f) for _, f in S_ALL])
    sh.row("levelbar 0.50 (mid)", [force(lv(0.5), f) for _, f in S_ALL])
    sh.row("levelbar 0.85 (high)", [force(lv(0.85), f) for _, f in S_ALL])
    sh.row("levelbar 1.00 (full)", [force(lv(1.0), f) for _, f in S_ALL])
    sh.row("levelbar discrete 0.4/0.9", [force(lv(0.4, True), f) for _, f in S_ALL[:3]] + [force(lv(0.9, True), SF.NORMAL)])

    def spin():
        s = Gtk.Spinner()
        s.start()
        return s
    sh.row("spinner", [force(spin(), f) for _, f in S_ALL[:1]] + [force(spin(), SF.INSENSITIVE)])
    return sh


def _icon_pix(name, size=16):
    th = Gtk.IconTheme.get_default()
    try:
        return th.load_icon(name, size, 0)
    except GLib.Error:
        return None


FILES = [("folder", "Aplikace", "—", "Složka", "dnes 09:12"), ("folder", "Dokumenty", "—", "Složka", "včera 21:03"),
         ("text-x-generic", "poznamky.txt", "4,2 kB", "Prostý text", "2. 10. 2026"),
         ("image-x-generic", "foto-dovolena.jpg", "3,1 MB", "Obrázek JPEG", "28. 9. 2026"),
         ("application-pdf", "faktura-2026-014.pdf", "184 kB", "Dokument PDF", "21. 9. 2026"),
         ("audio-x-generic", "zvonek.ogg", "96 kB", "Zvuk Ogg", "3. 9. 2026"),
         ("package-x-generic", "zaloha.tar.gz", "812 MB", "Archiv", "1. 9. 2026"),
         ("text-x-script", "build.sh", "1,3 kB", "Skript shellu", "14. 8. 2026"),
         ("folder", "Videa", "—", "Složka", "10. 8. 2026"), ("folder", "Stažené", "—", "Složka", "10. 8. 2026"),
         ("text-x-generic", "README.md", "2,0 kB", "Markdown", "1. 8. 2026"), ("folder", "Hudba", "—", "Složka", "2. 7. 2026")]


def make_tree(selected=3, columns=True, expander=False):
    st = Gtk.ListStore(str, str, str, str, str, bool, int)
    for i, (ic, n, sz, ty, dt) in enumerate(FILES):
        st.append([ic, n, sz, ty, dt, i % 3 == 0, (i * 9) % 100])
    tv = Gtk.TreeView(model=st)
    tv.set_headers_visible(True)
    tv.set_grid_lines(Gtk.TreeViewGridLines.NONE)
    c = Gtk.TreeViewColumn("Název")
    c.set_resizable(True)
    c.set_min_width(180)
    c.set_expand(True)
    r1 = Gtk.CellRendererPixbuf()
    c.pack_start(r1, False)
    c.add_attribute(r1, "icon-name", 0)
    r2 = Gtk.CellRendererText()
    r2.set_property("ellipsize", Pango.EllipsizeMode.END)
    c.pack_start(r2, True)
    c.add_attribute(r2, "text", 1)
    c.set_sort_indicator(True)
    c.set_sort_order(Gtk.SortType.ASCENDING)
    c.set_clickable(True)
    tv.append_column(c)
    for i, t in ((2, "Velikost"), (3, "Typ"), (4, "Změněno")):
        col = Gtk.TreeViewColumn(t, Gtk.CellRendererText(), text=i)
        col.set_resizable(True)
        col.set_clickable(True)
        tv.append_column(col)
    tg = Gtk.CellRendererToggle()
    tv.append_column(Gtk.TreeViewColumn("Sdíleno", tg, active=5))
    pr = Gtk.CellRendererProgress()
    pc = Gtk.TreeViewColumn("Využití", pr, value=6)
    pc.set_min_width(90)
    tv.append_column(pc)
    tv.get_selection().select_path(Gtk.TreePath.new_from_indices([selected]))
    return tv


def make_nemo_sidebar_tree(selected=1):
    """Nemo sidebar = GtkTreeView s více sloupci (ikona, text, vysunutí) + hlavičky skupin."""
    st = Gtk.TreeStore(str, str, str, int)
    g = st.append(None, ["", "Můj počítač", "", 1])
    for ic, t in (("user-home-symbolic", "Domov"), ("user-desktop-symbolic", "Pracovní plocha"),
                  ("folder-symbolic", "AAA_CLAUDE"), ("folder-documents-symbolic", "Dokumenty"),
                  ("folder-download-symbolic", "Stažené"), ("user-trash-symbolic", "Koš")):
        st.append(g, [ic, t, "", 0])
    g2 = st.append(None, ["", "Zařízení", "", 1])
    st.append(g2, ["drive-harddisk-symbolic", "Souborový systém", "media-eject-symbolic", 0])
    st.append(g2, ["drive-harddisk-symbolic", "SSD", "media-eject-symbolic", 0])
    tv = Gtk.TreeView(model=st)
    tv.get_style_context().add_class("sidebar")
    tv.set_headers_visible(False)
    c = Gtk.TreeViewColumn()
    ri = Gtk.CellRendererPixbuf()
    c.pack_start(ri, False)
    c.add_attribute(ri, "icon-name", 0)
    rt = Gtk.CellRendererText()
    rt.set_property("ellipsize", Pango.EllipsizeMode.END)
    c.pack_start(rt, True)
    c.add_attribute(rt, "text", 1)
    c.set_expand(True)
    tv.append_column(c)
    c2 = Gtk.TreeViewColumn()
    re = Gtk.CellRendererPixbuf()
    c2.pack_start(re, False)
    c2.add_attribute(re, "icon-name", 2)
    tv.append_column(c2)
    tv.expand_all()
    tv.set_level_indentation(0)
    tv.get_selection().select_path(Gtk.TreePath.new_from_indices([0, selected]))
    return tv


def framed(w, title, size=None):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.add(small(title))
    sw = Gtk.ScrolledWindow()
    sw.set_shadow_type(Gtk.ShadowType.IN)
    sw.add(w)
    if size:
        sw.set_size_request(*size)
    box.add(sw)
    return box


def page_lists(win):
    g = Gtk.Grid(column_spacing=18, row_spacing=14, margin=16)
    g.attach(framed(make_tree(), "TreeView 7 sloupců, hlavičky, vybraný řádek 4", (700, 300)), 0, 0, 1, 1)

    lb = Gtk.ListBox()
    lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
    for i, t in enumerate(("Síť", "Zvuk", "Displeje", "Bluetooth", "Klávesnice", "Energie")):
        row = Gtk.ListBoxRow()
        b = Gtk.Box(spacing=10, margin=8)
        b.add(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.LARGE_TOOLBAR))
        b.pack_start(Gtk.Label(label=t, xalign=0.0), True, True, 0)
        if i == 1:
            b.add(Gtk.Switch(active=True, valign=Gtk.Align.CENTER))
        if i == 3:
            b.add(Gtk.CheckButton())
        row.add(b)
        lb.add(row)
        if i == 2:
            lb.select_row(row)
        if i == 4:
            force(row, SF.PRELIGHT)
    g.attach(framed(lb, "ListBox: vybraný řádek 3, hover řádek 5", (340, 300)), 1, 0, 1, 1)

    pl = Gtk.PlacesSidebar()
    pl.set_show_desktop(True)
    pl.set_location(Gio.File.new_for_path(os.path.join(HOME, "Plocha")))
    iv_store = Gtk.ListStore(str, str)
    for n, ic in (("Dokumenty", "folder"), ("Obrázky", "folder-pictures"), ("Hudba", "folder-music"),
                  ("Videa", "folder-videos"), ("poznamky.txt", "text-x-generic"), ("foto.jpg", "image-x-generic"),
                  ("zaloha.zip", "package-x-generic"), ("skript.py", "text-x-python")):
        iv_store.append([n, ic])
    iv = Gtk.IconView(model=iv_store)
    iv.set_text_column(0)
    iv.set_item_orientation(Gtk.Orientation.VERTICAL)
    iv.set_item_width(90)
    # ikonu bereme ze sloupce 1 přes cell renderer s icon-name
    iv.clear()
    rp = Gtk.CellRendererPixbuf()
    rp.set_property("stock-size", Gtk.IconSize.DIALOG)
    iv.pack_start(rp, False)
    iv.add_attribute(rp, "icon-name", 1)
    rt = Gtk.CellRendererText()
    rt.set_property("alignment", Pango.Alignment.CENTER)
    iv.pack_start(rt, False)
    iv.add_attribute(rt, "text", 0)
    iv.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
    for i in (1, 2):
        iv.select_path(Gtk.TreePath.new_from_indices([i]))
    side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    side.add(framed(pl, "GtkPlacesSidebar (vybrána Plocha)", (250, 300)))
    side.add(framed(make_nemo_sidebar_tree(), "Sidebar jako Nemo: TreeView s více sloupci, vybraná Pracovní plocha", (250, 250)))
    g.attach(side, 2, 0, 1, 2)
    g.attach(framed(iv, "IconView: výběr 2 položek", (700, 260)), 0, 1, 2, 1)
    return g


def page_containers(win):
    g = Gtk.Grid(column_spacing=18, row_spacing=12, margin=16)

    def nb(pos, n=4):
        b = Gtk.Notebook()
        b.set_tab_pos(pos)
        for i in range(n):
            tl = Gtk.Box(spacing=6)
            tl.add(Gtk.Label(label=f"Záložka {i + 1}"))
            if i == 1:
                tl.add(icon_btn("window-close-symbolic", "flat"))
            tl.show_all()
            b.append_page(Gtk.Label(label=f"Obsah záložky {i + 1}", margin=20), tl)
        b.set_current_page(0)
        b.set_size_request(380, 130)
        return b
    g.attach(nb(Gtk.PositionType.TOP), 0, 0, 1, 1)
    g.attach(nb(Gtk.PositionType.LEFT), 1, 0, 1, 1)
    g.attach(nb(Gtk.PositionType.BOTTOM, 3), 2, 0, 1, 1)

    fr = Gtk.Frame(label="Frame s popiskem")
    fr.add(Gtk.Label(label="Obsah rámečku", margin=24))
    fr2 = Gtk.Frame()
    fr2.set_shadow_type(Gtk.ShadowType.IN)
    fr2.add(Gtk.Label(label="Frame IN bez popisku", margin=24))
    col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    col.add(fr)
    col.add(fr2)
    ex1 = Gtk.Expander(label="Rozbalené")
    ex1.set_expanded(True)
    ex1.add(Gtk.Label(label="Skrytý obsah", margin=8, xalign=0.0))
    ex2 = Gtk.Expander(label="Sbalené")
    col.add(ex1)
    col.add(ex2)
    g.attach(col, 0, 1, 1, 2)

    ibs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    for mt, txt in ((Gtk.MessageType.INFO, "Informace: synchronizace dokončena."),
                    (Gtk.MessageType.WARNING, "Varování: málo místa na disku."),
                    (Gtk.MessageType.QUESTION, "Otázka: chcete uložit změny?"),
                    (Gtk.MessageType.ERROR, "Chyba: soubor se nepodařilo otevřít.")):
        ib = Gtk.InfoBar()
        ib.set_message_type(mt)
        ib.set_show_close_button(True)
        ib.get_content_area().add(Gtk.Label(label=txt))
        ib.add_button("Akce", 1)
        ibs.add(ib)
    g.attach(ibs, 1, 1, 2, 2)

    def paned(orient):
        p = Gtk.Paned(orientation=orient)
        a = Gtk.Frame(); a.add(Gtk.Label(label="Panel A", margin=16))
        b = Gtk.Frame(); b.add(Gtk.Label(label="Panel B", margin=16))
        p.pack1(a, True, False)
        p.pack2(b, True, False)
        p.set_size_request(380, 110)
        return p
    g.attach(paned(Gtk.Orientation.HORIZONTAL), 0, 3, 1, 1)
    g.attach(paned(Gtk.Orientation.VERTICAL), 1, 3, 1, 1)

    sep = Gtk.Box(spacing=12)
    sep.add(Gtk.Label(label="Před"))
    sep.add(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    sep.add(Gtk.Label(label="Za"))
    sep.add(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    sep.add(Gtk.Label(label="Konec"))
    sbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    sbox.add(Gtk.Label(label="Oddělovače", xalign=0.0))
    sbox.add(Gtk.Separator())
    sbox.add(sep)
    g.attach(sbox, 2, 3, 1, 1)

    tv = Gtk.TextView()
    tv.set_wrap_mode(Gtk.WrapMode.NONE)
    tv.get_buffer().set_text("\n".join(f"Řádek {i}: " + "dlouhý text pro horizontální posuvník " * 6 for i in range(60)))
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
    sw.set_shadow_type(Gtk.ShadowType.IN)
    sw.set_overlay_scrolling(False)
    sw.add(tv)
    sw.set_size_request(-1, 200)
    sw.set_hexpand(True)
    g.attach(sw, 0, 4, 3, 1)
    return g


def page_headerbar(win):
    hb = Gtk.HeaderBar()
    hb.set_show_close_button(True)
    hb.set_title("Mentha galerie")
    hb.set_subtitle("Titulek + podtitulek")
    hb.pack_start(icon_btn("go-previous-symbolic"))
    lk = Gtk.Box()
    lk.get_style_context().add_class("linked")
    lk.add(icon_btn("view-list-symbolic"))
    t = Gtk.ToggleButton()
    t.add(Gtk.Image.new_from_icon_name("view-grid-symbolic", Gtk.IconSize.BUTTON))
    t.set_active(True)
    lk.add(t)
    hb.pack_start(lk)
    hb.pack_end(Gtk.MenuButton(menu_model=menu_model()))
    st = Gtk.ToggleButton()
    st.add(Gtk.Image.new_from_icon_name("edit-find-symbolic", Gtk.IconSize.BUTTON))
    hb.pack_end(st)
    hb.pack_end(styled(Gtk.Button(label="Uložit"), "suggested-action"))
    win.set_titlebar(hb)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=16)

    def mk(kind, backdrop=False):
        h = Gtk.HeaderBar()
        h.set_show_close_button(True)
        if kind == "switcher":
            stack = Gtk.Stack()
            for n in ("Přehled", "Aktivita", "Nastavení"):
                stack.add_titled(Gtk.Label(label=n), n, n)
            sw = Gtk.StackSwitcher()
            sw.set_stack(stack)
            h.set_custom_title(sw)
            h.pack_start(icon_btn("go-previous-symbolic"))
            sb = Gtk.ToggleButton()
            sb.add(Gtk.Image.new_from_icon_name("edit-find-symbolic", Gtk.IconSize.BUTTON))
            sb.set_active(True)
            h.pack_end(sb)
            h.pack_end(Gtk.MenuButton(menu_model=menu_model()))
        elif kind == "title":
            h.set_title("Název dokumentu")
            h.set_subtitle("/home/matata/Dokumenty")
            h.pack_start(styled(Gtk.Button(label="Zrušit"), "destructive-action"))
            h.pack_end(styled(Gtk.Button(label="Hotovo"), "suggested-action"))
        elif kind == "flat":
            h.set_title("Ploché záhlaví")
            h.get_style_context().add_class("flat")
            h.pack_start(Gtk.Button(label="Zpět"))
        if backdrop:
            force(h, SF.BACKDROP)
        return h
    for cap, kind, bd in (("HeaderBar + StackSwitcher + search toggle + menu button", "switcher", False),
                          ("HeaderBar title+subtitle, suggested/destructive", "title", False),
                          ("totéž v backdrop", "switcher", True), ("headerbar.flat", "flat", False)):
        outer.add(small(cap))
        outer.add(mk(kind, bd))

    ab = Gtk.ActionBar()
    ab.pack_start(Gtk.Button(label="Přidat"))
    ab.pack_start(icon_btn("list-remove-symbolic"))
    ab.pack_end(styled(Gtk.Button(label="Použít"), "suggested-action"))
    ab.set_center_widget(Gtk.Label(label="ActionBar"))
    outer.add(small("Gtk.ActionBar"))
    outer.add(ab)

    sbar = Gtk.SearchBar()
    ent = Gtk.SearchEntry()
    ent.set_text("hledání")
    sbar.add(ent)
    sbar.set_search_mode(True)
    outer.add(small("Gtk.SearchBar"))
    outer.add(sbar)

    side_stack = Gtk.Stack()
    for n in ("Obecné", "Vzhled", "Klávesnice", "Síť"):
        side_stack.add_titled(Gtk.Label(label=f"Stránka {n}"), n, n)
    ss = Gtk.StackSidebar()
    ss.set_stack(side_stack)
    hbx = Gtk.Box()
    hbx.add(ss)
    hbx.add(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    hbx.pack_start(side_stack, True, True, 0)
    hbx.set_size_request(-1, 170)
    outer.add(small("Gtk.StackSidebar"))
    outer.add(hbx)
    return outer


def _actions(win):
    ag = Gio.SimpleActionGroup()
    for n in ("new", "open", "quit"):
        ag.add_action(Gio.SimpleAction.new(n, None))
    ag.add_action(Gio.SimpleAction.new_stateful("hidden", None, GLib.Variant.new_boolean(True)))
    ag.add_action(Gio.SimpleAction.new_stateful("spacing", GLib.VariantType.new("s"), GLib.Variant.new_string("a")))
    win.insert_action_group("g", ag)


def page_popovers(win):
    _actions(win)
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20, margin=30)
    row = Gtk.Box(spacing=330)
    b1 = Gtk.Button(label="Popover s obsahem")
    b2 = Gtk.Button(label="PopoverMenu (ModelButton)")
    b3 = Gtk.MenuButton()
    b3.set_menu_model(menu_model())
    for b in (b1, b2, b3):
        row.add(b)
    outer.add(row)
    hint = Gtk.Label(label="Popovery se otevřou po startu (3 vedle sebe).", xalign=0.0, margin_top=380)
    outer.add(hint)

    def open_all():
        p1 = Gtk.Popover.new(b1)
        p1.set_modal(False)
        bx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)
        bx.add(lbl("<b>Nastavení</b>", markup=True))
        e = Gtk.Entry(text="Hodnota")
        bx.add(e)
        bx.add(Gtk.CheckButton(label="Zapamatovat"))
        sr = Gtk.Box(spacing=8)
        sr.add(Gtk.Label(label="Zapnout"))
        sr.pack_end(Gtk.Switch(active=True), False, False, 0)
        bx.add(sr)
        lk = Gtk.Box()
        lk.get_style_context().add_class("linked")
        lk.add(Gtk.Button(label="Zpět"))
        lk.add(Gtk.Button(label="Dál"))
        bx.add(lk)
        bx.add(styled(Gtk.Button(label="Použít"), "suggested-action"))
        bx.add(Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1))
        bx.show_all()
        p1.add(bx)
        p1.popup()

        p2 = Gtk.PopoverMenu()
        p2.set_relative_to(b2)
        p2.set_modal(False)
        mx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=10, spacing=0)

        def mbtn(text, icon=None, role=None, menu=None, active=False, sens=True):
            m = Gtk.ModelButton()
            m.set_property("text", text)
            if icon:
                m.set_property("icon", Gio.ThemedIcon.new(icon))
            if role == "check":
                m.set_property("role", Gtk.ButtonRole.CHECK)
                m.set_property("active", active)
            if role == "radio":
                m.set_property("role", Gtk.ButtonRole.RADIO)
                m.set_property("active", active)
            if menu:
                m.set_property("menu-name", menu)
            m.set_sensitive(sens)
            return m
        mx.add(mbtn("Nový dokument", "document-new-symbolic"))
        mx.add(mbtn("Otevřít…", "document-open-symbolic"))
        mx.add(mbtn("Zobrazit skryté", role="check", active=True))
        mx.add(mbtn("Řádkování", role="check"))
        mx.add(Gtk.Separator())
        mx.add(mbtn("Řazení A–Z", role="radio", active=True))
        mx.add(mbtn("Řazení Z–A", role="radio"))
        mx.add(Gtk.Separator())
        mx.add(mbtn("Další možnosti", menu="more"))
        mx.add(mbtn("Zakázaná položka", sens=False))
        mx.show_all()
        p2.add(mx)
        sub = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=10, spacing=0)
        back = Gtk.ModelButton()
        back.set_property("menu-name", "main")
        back.set_property("inverted", True)
        back.set_property("centered", True)
        back.set_property("text", "Další možnosti")
        sub.add(back)
        sub.add(mbtn("Podpoložka A"))
        sub.add(mbtn("Podpoložka B"))
        sub.show_all()
        p2.add(sub)
        p2.child_set_property(sub, "submenu", "more")
        p2.popup()

        pm = Gtk.Popover.new_from_model(b3, menu_model())
        pm.set_modal(False)
        pm.popup()
        return False
    GLib.timeout_add(700, open_all)
    return outer


def page_menus(win):
    ag = Gtk.AccelGroup()
    win.add_accel_group(ag)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    mb = Gtk.MenuBar()

    def acc(item, key, mods=Gdk.ModifierType.CONTROL_MASK):
        k, m = Gtk.accelerator_parse(key)
        item.add_accelerator("activate", ag, k, m, Gtk.AccelFlags.VISIBLE)

    def img(label, icon):
        it = Gtk.ImageMenuItem(label=label, use_underline=True)
        it.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
        it.set_always_show_image(True)
        return it
    file_menu = Gtk.Menu()
    n = img("_Nový", "document-new-symbolic"); acc(n, "<Control>N"); file_menu.append(n)
    o = img("_Otevřít…", "document-open-symbolic"); acc(o, "<Control>O"); file_menu.append(o)
    rec = Gtk.MenuItem(label="Nedávné")
    rm = Gtk.Menu()
    for t in ("poznamky.txt", "faktura.pdf", "foto.jpg"):
        rm.append(Gtk.MenuItem(label=t))
    rm.append(Gtk.SeparatorMenuItem())
    rm.append(Gtk.MenuItem(label="Vymazat seznam"))
    rec.set_submenu(rm)
    file_menu.append(rec)
    file_menu.append(Gtk.SeparatorMenuItem())
    c1 = Gtk.CheckMenuItem(label="Zobrazit skryté"); c1.set_active(True); acc(c1, "<Control>H"); file_menu.append(c1)
    c2 = Gtk.CheckMenuItem(label="Panel nástrojů"); file_menu.append(c2)
    c3 = Gtk.CheckMenuItem(label="Nejasný stav"); c3.set_inconsistent(True); file_menu.append(c3)
    file_menu.append(Gtk.SeparatorMenuItem())
    r1 = Gtk.RadioMenuItem(label="Řadit podle názvu"); r1.set_active(True); file_menu.append(r1)
    r2 = Gtk.RadioMenuItem(label="Řadit podle data", group=r1); file_menu.append(r2)
    file_menu.append(Gtk.SeparatorMenuItem())
    dis = Gtk.MenuItem(label="Zakázaná položka"); dis.set_sensitive(False); file_menu.append(dis)
    q = img("_Ukončit", "application-exit-symbolic"); acc(q, "<Control>Q"); file_menu.append(q)
    items = {}
    for name, menu in (("_Soubor", file_menu), ("_Úpravy", None), ("_Zobrazit", None), ("_Nápověda", None)):
        it = Gtk.MenuItem(label=name, use_underline=True)
        if menu is None:
            m = Gtk.Menu()
            m.append(Gtk.MenuItem(label="Položka 1"))
            m.append(Gtk.MenuItem(label="Položka 2"))
            menu = m
        it.set_submenu(menu)
        mb.append(it)
        items[name] = it
    box.pack_start(mb, False, False, 0)
    # Programové popup_at_* / select_item bez události shodí GTK3 v Broadway (assert width>=0, pixman),
    # proto otevírá menu až capture.sh skutečným klikem/klávesami (menubar Soubor, pravý klik do plochy).
    ev = Gtk.EventBox()
    ev.add(Gtk.Label(label="Menubar: klik na Soubor, Down x3, Right (submenu Nedávné). Pravý klik sem: kontextové menu."))
    ctx = Gtk.Menu()
    for t in ("Otevřít", "Otevřít v nové záložce", "Kopírovat", "Vložit"):
        ctx.append(Gtk.MenuItem(label=t))
    ctx.append(Gtk.SeparatorMenuItem())
    ctx.append(styled(Gtk.MenuItem(label="Přesunout do koše"), "destructive"))
    ctx.show_all()
    ev.connect("button-press-event", lambda w, e: ctx.popup_at_pointer(e) if e.button == 3 else None)
    box.pack_start(ev, True, True, 0)
    return box


def page_typography(win):
    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=24)
    pangram = "Příliš žluťoučký kůň úpěl ďábelské ódy. 0123456789 — „citace“ © €"
    for size in (8, 9, 10, 11, 12, 14, 18, 24):
        l = Gtk.Label(xalign=0.0)
        l.set_markup(f'<span size="{size * 1024}">{size} pt  {GLib.markup_escape_text(pangram)}</span>')
        b.add(l)
    b.add(Gtk.Separator())
    for cls, t in (("title", "class title"), ("subtitle", "class subtitle"), ("dim-label", "class dim-label — tlumený text"),
                   ("title-1", "title-1"), ("heading", "heading")):
        b.add(lbl(t, cls))
    b.add(lbl("<b>Tučné</b> <i>kurzíva</i> <u>podtržené</u> <tt>monospace 0Oo1lI</tt> <a href='https://x.y'>odkaz</a>", markup=True))
    sel = Gtk.Label(label="Vybratelný text (selectable)", xalign=0.0)
    sel.set_selectable(True)
    sel.select_region(0, 8)
    b.add(sel)
    tip = Gtk.Button(label="Tlačítko s tooltipem")
    tip.set_tooltip_text("Nápověda k tlačítku")
    b.add(tip)
    return b


def page_hist(win):
    """Okno Historie aktualizací z mintUpdate: obyčejné okno, VBox 12, ScrolledWindow IN (can_focus), TreeView rules_hint."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, border_width=12)
    st = Gtk.TreeStore(str, str, str, str, str)
    for i in range(40):
        st.append(None, ["2026-10-%02d - 22:56:%02d" % (18 - i // 4, 22 - i % 5), "flatpak-runtime", "org.gnome.Platform",
                         "fcd9f49e...", "c3f351792c3b9937a01191ad5a03c1206fb7a8b5"])
    tv = Gtk.TreeView(model=st, reorderable=True, rules_hint=True, enable_search=False)
    for i, t in enumerate(("Datum", "Typ", "Aktualizace", "Stará verze", "Nová verze")):
        c = Gtk.TreeViewColumn(t, Gtk.CellRendererText(), text=i)
        c.set_sort_column_id(i); c.set_resizable(True)
        tv.append_column(c)
    sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN, can_focus=True)
    sw.add(tv)
    box.pack_start(sw, True, True, 0)
    bb = Gtk.ButtonBox(layout_style=Gtk.ButtonBoxStyle.END, spacing=15)
    bb.add(Gtk.Button(label="Zavřít"))
    box.pack_start(bb, False, True, 0)
    box.set_size_request(1000, 500)
    return box


def page_upd(win):
    """Hlavní okno mintUpdate: Paned, nahoře ScrolledWindow IN + TreeView, dole Notebook se třemi stránkami ScrolledWindow(border 2)+TextView."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    pn = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
    st = Gtk.ListStore(bool, str, str)
    st.append([True, "claude-desktop", "2.42304.2"])
    tv = Gtk.TreeView(model=st)
    tv.append_column(Gtk.TreeViewColumn("Přejít na novější verzi", Gtk.CellRendererToggle(), active=0))
    tv.append_column(Gtk.TreeViewColumn("Název", Gtk.CellRendererText(), text=1))
    tv.append_column(Gtk.TreeViewColumn("Nová verze", Gtk.CellRendererText(), text=2))
    sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN, can_focus=True); sw.add(tv)
    pn.pack1(sw, True, False)
    nb = Gtk.Notebook(height_request=150)
    for t in ("Informace", "Balíčky", "Seznam změn"):
        s2 = Gtk.ScrolledWindow(can_focus=True, border_width=2)
        s2.add(Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD, left_margin=6))
        nb.append_page(s2, Gtk.Label(label=t))
    pn.pack2(nb, False, False)
    box.pack_start(pn, True, True, 0)
    box.pack_start(Gtk.Statusbar(), False, True, 0)
    box.set_size_request(1000, 520)
    return box


def page_spin(win):
    box = Gtk.Box(spacing=40, border_width=40, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
    for px in (16, 32, 96):
        sp = Gtk.Spinner(width_request=px, height_request=px); sp.start(); box.add(sp)
    return box


PAGES = {"upd": page_upd, "spin": page_spin, "hist": page_hist, "buttons": page_buttons, "entries": page_entries, "toggles": page_toggles, "lists": page_lists,
         "containers": page_containers, "headerbar": page_headerbar, "popovers": page_popovers,
         "menus": page_menus, "typography": page_typography}


def dialog_page(kind):
    """Rodičovské okno s jednoduchým obsahem + modální dialog nad ním."""
    parent = Gtk.Window(title="Mentha galerie: rodič dialogu")
    parent.set_default_size(1400, 1000)
    parent.add(Gtk.Label(label="Obsah okna pod dialogem (dialog se otevře klávesou F5 nebo po 20 s)"))
    parent.show_all()

    opened = []

    def open_dlg(*_):
        if opened:
            return False
        opened.append(1)
        if kind.startswith("dlg-message"):
            d = Gtk.MessageDialog(transient_for=parent, modal=True, message_type=Gtk.MessageType.QUESTION,
                                  buttons=Gtk.ButtonsType.NONE, text="Smazat vybraný soubor?")
            d.format_secondary_text("Soubor „faktura-2026-014.pdf“ bude trvale odstraněn a nelze jej obnovit.")
            d.add_button("Zrušit", Gtk.ResponseType.CANCEL)
            b = d.add_button("Smazat", Gtk.ResponseType.OK)
            b.get_style_context().add_class("destructive-action")
        elif kind == "dlg-filechooser":
            d = Gtk.FileChooserDialog(title="Otevřít soubor", transient_for=parent, action=Gtk.FileChooserAction.OPEN)
            d.add_button("Zrušit", Gtk.ResponseType.CANCEL)
            d.add_button("Otevřít", Gtk.ResponseType.ACCEPT).get_style_context().add_class("suggested-action")
            d.set_default_size(900, 600)
            d.set_current_folder(HOME)
            f = Gtk.FileFilter(); f.set_name("Všechny soubory"); f.add_pattern("*"); d.add_filter(f)
            f2 = Gtk.FileFilter(); f2.set_name("Obrázky"); f2.add_mime_type("image/*"); d.add_filter(f2)
        elif kind == "dlg-about":
            d = Gtk.AboutDialog(transient_for=parent, modal=True)
            d.set_program_name("Mentha")
            d.set_version("1.0")
            d.set_comments("Modrý motiv pro Linux Mint — Cinnamon, GTK 3 a 4.")
            d.set_website("https://example.org")
            d.set_website_label("Domovská stránka")
            d.set_license_type(Gtk.License.GPL_3_0)
            d.set_authors(["Martin Procházka"])
            d.set_copyright("© 2026 FNS")
            d.set_logo_icon_name("preferences-desktop-theme")
        else:
            d = Gtk.ColorChooserDialog(title="Vyberte barvu", transient_for=parent)
            d.set_use_alpha(True)
        d.show()
        if kind == "dlg-message-focus":
            # jako Nemo (eel): výchozí odpověď Zrušit + viditelný klávesnicový fokus na ní
            d.set_default_response(Gtk.ResponseType.CANCEL)
            GLib.timeout_add(500, lambda: (d.get_widget_for_response(Gtk.ResponseType.CANCEL).grab_focus(), d.set_focus_visible(True), False)[2])
            return False
        # F5 je klávesa, GTK3 by dialogu zapnul viditelný fokus; snímek má odpovídat otevření myší
        # puštění F5 (key-release) zapne focus-visible znovu: potlačit i po zpoždění
        # focus-in okna (Broadway) zapne focus-visible i později: opakovat do snímku
        for ms in (0, 300, 800, 1600, 2200, 3000, 4000):
            GLib.timeout_add(ms, lambda: (d.set_focus_visible(False), d.set_focus(None), False)[2])
        return False
    # Dialog se otevírá až po maximalizaci rodiče (capture.sh pošle F5), jinak se centruje na špatné místo.
    parent.connect("key-press-event", lambda w, e: open_dlg() if e.keyval == Gdk.KEY_F5 else None)
    GLib.timeout_add(20000, open_dlg)
    return parent


def clear_selection(w):
    if isinstance(w, Gtk.Editable):
        w.select_region(0, 0)
    if isinstance(w, Gtk.Container):
        for c in w.get_children():
            clear_selection(c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    # skutečný fokus z klávesnice (viditelný outline) na prvním prvku sloupce FOCUS; bez flagu žádný
    ap.add_argument("--kbd-focus", choices=("check", "radio", "scale", "switch", "button", "suggested", "linked", "pathbar", "entry", "combo", "spin", "textview"))
    a = ap.parse_args()
    if a.page.startswith("dlg-"):
        win = dialog_page(a.page)
    else:
        win = Gtk.Window(title=f"Mentha galerie: {a.page}")
        win.set_default_size(1400, 1000)
        content = PAGES[a.page](win)
        win.add(content)
        win.show_all()
    win.connect("destroy", Gtk.main_quit)
    GLib.timeout_add(300, lambda: (win.set_focus(None), clear_selection(win), False)[2])   # první widget nesmí mít skutečný focus
    GLib.timeout_add(900, apply_forced)
    GLib.timeout_add(2500, apply_forced)   # po případném relayoutu po maximalizaci
    if a.kbd_focus:
        # outline kreslí GTK3 jen při viditelném fokusu (po klávese); bez flagu snímek odpovídá ovládání myší
        kind = {"check": lambda w: isinstance(w, Gtk.CheckButton) and not isinstance(w, Gtk.RadioButton),
                "radio": lambda w: isinstance(w, Gtk.RadioButton),
                "scale": lambda w: isinstance(w, Gtk.Scale),
                "switch": lambda w: isinstance(w, Gtk.Switch)}.get(a.kbd_focus)
        def _kbd_focus():
            if kind is None:
                ws = [KBD[a.kbd_focus]] if a.kbd_focus in KBD else []
                for w, f in FORCED:   # stav FOCUSED nastavený příznakem by s fokusem kolidoval
                    if w in ws:
                        w.unset_state_flags(SF.FOCUSED)
            else:
                ws = [w for w, f in FORCED if f & SF.FOCUSED and kind(w)]
            if ws:
                ws[0].grab_focus()
                win.set_focus_visible(True)
                if isinstance(ws[0], Gtk.Editable):
                    ws[0].select_region(0, 0)
            return False
        GLib.timeout_add(2700, _kbd_focus)
    Gtk.main()


if __name__ == "__main__":
    main()
