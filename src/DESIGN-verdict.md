# Mentha: posudek tří konceptů a výsledné doporučení

Vítěz je **Mentha (bold)**. Přebírá inženýrskou část konceptu pragmatic a několik nápadů z Opaliny. Všechny tři koncepty ale obsahují technické chyby, které jsem dnes na stroji ověřil. Nejzávažnější je, že **`metacity-1` Muffin 6.6 vůbec nečte**. Dále **Mint už sám přebarvuje libadwaita podle aktivního GTK motivu**, takže skript se symlinky ani systemd služba nejsou potřeba.

---

## 1. Co jsem dnes ověřil na stroji

| Tvrzení v konceptech | Skutečnost (Cinnamon 6.6.9, muffin 6.6.3) | Důkaz |
|---|---|---|
| Okna se SSD potřebují `metacity-1/metacity-theme-3.xml` (tvrdí všechny 3 koncepty) | **Chyba.** `libmuffin.so.0` neobsahuje žádný řetězec `metacity`, čte jen `gtk-theme-name`, `titlebar-font` a `button-layout`. Rámečky kreslí přes GTK CSS aktivního GTK motivu (`window.ssd headerbar.titlebar`, `.titlebar button.titlebutton`). Proto ZorinMatata bez `metacity-1` funguje. Klíč `wm.preferences theme` Muffin nečte. | `strings libmuffin.so.0` |
| libadwaita jde jen přes `~/.config/gtk-4.0` nebo Rewaitu (Opalina, pragmatic) | **Chyba.** Je nainstalovaný `libadwaita-1-0 1.5.0-2mint3+zara`, záplatovaný Mintem. Načítá `<aktivní gtk motiv>/libadwaita-%d.%d/{base,defaults-light,defaults-dark}.css`, a to i z `~/.themes`, a reaguje na `changed::gtk-theme` **za běhu**. Obsahuje i `base.css`, takže jde měnit tvar (radiusy), ne jen barvy. ZorinMatata tuto složku nemá, proto libadwaita aplikace dnes vypadají jako čistá Adwaita. | `strings libadwaita-1.so.0`, `/usr/share/themes/Mint-Y-Dark/libadwaita-1.5/` |
| Ostrovy přes `.panelLeft/.panelCenter/.panelRight` | Třídy existují. `margin` na nich ověřený není, musí se vyzkoušet. | `panel.js:2127-2129` |
| Dock jako plovoucí lišta | `grouped-window-list` sedí v zóně `left` panelu 1, cornerbar v zóně `right`. Zóna `.panelLeft.vertical` je tedy jen tak vysoká jako ikony a vznikne lišta, která roste s počtem aplikací. | `enabled-applets` |
| auto-dark-light umí příkazy | Ano: `*-mode_commands_list`, `_switch_enable`. Má položky applications, desktop, icons a mouse-pointer, ale **ne WM theme** (to nevadí, viz první řádek). Sám nastavuje `org.x.apps.portal color-scheme`. | JSON + `themes_handler.js` |
| `org.gnome.desktop.interface color-scheme` | Existuje (`'default'`). Klíč `accent-color` **neexistuje**. | gsettings |
| `font-feature-settings: "tnum"` v St | Pravděpodobně funguje. Vlastnost je v `libst.so`, stejně jako `box-shadow` a `transition-duration`. `backdrop-filter` tam není. | `strings libst.so` |
| OSD jako vodorovná pilulka | Jde čistě přes CSS. `.media-keys-osd` je hbox (ikona + vbox[popisek, `.level`]). | `osdWindow.js:51-71` |
| Indikátor docku přechodem (bold) | St neumí přechod v rámečku a GWL nemá samostatný actor pro indikátor. Spolehlivý je jen `border-left` na `.grouped-window-list-item-box.left` (dnešní řešení) a tlumené pozadí dlaždice. | `appGroup.js` |
| Kvantum z apt (Opalina, pragmatic) | `qt-style-kvantum` **nemá v repu kandidáta** (potřeboval by PPA). `qt5ct` 1.5, `qt6ct` 0.9, `sassc` 3.6.1 a `fonts-jetbrains-mono` dostupné jsou. Tvrzení Opaliny, že Mint 22 nemá qt5ct, je tedy mylné. | `apt-cache policy` |
| Mint-Y jako základ shellu | Na disku jsou `Mint-Y-Teal` a `Mint-Y-Dark-Teal` s `cinnamon/`, tedy referenční CSS pro selektory 6.6 (nové menu, odznaky). | `ls /usr/share/themes` |
| Kurzory, ikony | Bibata-Modern-Ice, Papirus, Papirus-Dark, Papirus-Light a Tela jsou nainstalované. Papirus je v `~/.local/share/icons` i v `/usr/share/icons` a uživatelská kopie má přednost. | ls |
| Dynamic wallpaper | Podporuje `source_folder` / `image_source`, takže vlastní sada tapet jde. | `settings-schema.json` |

Další drobnosti:
- Lokální `~/.local/share/cinnamon/applets/grouped-window-list@cinnamon.org` je dnes shodný se systémovým, ale **zakrývá ho**. Budoucí opravy z aktualizací Cinnamonu se proto nepoužijí. Doporučuji ho smazat.
- GTK3 i St nemají `text-transform`, takže popisky verzálkami (bold) jdou jen tam, kde je verzálkami už samotný text.
- Inter Display je navržený pro velikosti od zhruba 20 px. Na titulky oken v 10.5 pt (bold) se nehodí.

---

## 2. Hodnocení konceptů (1–10, u rizika znamená 10 nejnižší riziko)

| Koncept | Krása | Originalita | Soudržnost light/dark | Robustnost na 6.6 a GTK3/4/adw/Flatpak | Udržovatelnost | Riziko | Součet |
|---|---|---|---|---|---|---|---|
| **Opalina** (luminous) | 8 | 7 | 8 | 4 | 5 | 4 | **36** |
| **Mentha** (bold) | 9 | 9 | 7 | 7 | 6 | 6 | **44** |
| **Mentha** (pragmatic) | 6 | 6 | 8 | 6 | 8 | 8 | **42** |

**Opalina:**
- Plusy: nejlépe promyšlená světlá varianta, tokeny `*-text`, inverzní tooltip, kázeň v radiusech.
- Fialovo-azurový přechod působí jako typická „AI/SaaS“ estetika let 2024–26, takže v originalitě ztrácí.
- Inženýrsky je nejslabší:
  - `metacity-1`, které Muffin nečte;
  - systemd služba `gsettings monitor` a symlinky gtk-4.0, přestože to Mint řeší sám;
  - tvrzení, že libadwaita jde jen přebarvit (na Mintu neplatí);
  - Kvantum přes `/etc/environment` a balíček, který v repu není.
- Rozpětí radiusů 6 až 24 je široké a velká okna s radiusem 18 působí „bublinově“.

**Mentha bold:**
- Nejsilnější identita: inkoustová noc, neonová máta s tmavým textem (kontrast zhruba 10:1, přepočítáno) a ultrafialová jako barva fokusu.
- Je to pocta Mintu, ale vzhled, jaký Mint nikdy neměl. Nekopíruje Zorin ani Windows 11.
- Jako jediný správně našel Mint patch libadwaita.
- Chyby:
  - `metacity-1`;
  - položka „wm“ v appletu (applet ji nemá, ale nevadí to);
  - přechodový proužek v docku (St to neumí);
  - Colloid `cinnamon/` může mít mezery v selektorech 6.6;
  - tmavý shell v obou režimech je zvyk uživatele, ne chyba, ale světlý shell je jen naznačený.

**Mentha pragmatic:**
- Nejlepší inženýrství: upstream Orchis, kde se jen připojí vlastní vrstva (žádný merge), každá fáze vratná, pořadí kroků s rychlými výhrami na začátku.
- Vizuálně je „hezky bezpečná“: tyrkysová s korálovou nevyvolá wow efekt.
- Chyby:
  - `metacity-1`;
  - symlink gtk-4.0 (zbytečný);
  - „tečky, které se probudí“ nad skupinou tlačítek: GTK3 umí jen `headerbar:hover` a Muffin SSD jen hover jednotlivého tlačítka, takže výsledek bude nekonzistentní;
  - akcent `#13A594` s bílým textem má kontrast 3:1.

---

## 3. Výsledné doporučení: **Mentha**

**Identita** pochází z konceptu bold: máta je barva akce, ultrafialová barva pozornosti, inkoustová noc a ostrovy.

**Inženýrství** pochází z pragmatic, upravené podle ověřených faktů:

| Vrstva | Řešení |
|---|---|
| GTK3/GTK4 | Orchis, k němu připojená vrstva |
| Shell | Systémový Mint-Y-Teal `cinnamon.css` s přebarvením a připojenou vrstvou |
| libadwaita | Složky `libadwaita-1.5/1.7` z Mint-Y, přebarvené |
| SSD okna | Přes GTK CSS |
| Skripty | Žádná služba ani symlinky |

**Z Opaliny se přebírá:**
- tokeny `*-text`;
- inverzní tooltip ve světlé variantě;
- ostrov s hodinami a počasím;
- vyhledávací pole jako pilulka s prstencem fokusu;
- světlý shell jako plnohodnotná volba, ne jen naznačená.

### 3.1 Paleta (jediný zdroj: `src/_mentha-tokens.scss`)

| Token | Light | Dark |
|---|---|---|
| `bg` | `#F4F5FB` | `#0E0F1A` |
| `surface` (okno, headerbar) | `#FFFFFF` | `#161827` |
| `surface-alt` (sidebar, entry) | `#ECEEF7` | `#1E2135` |
| `surface-raised` (popup, menu, notifikace) | `#FFFFFF` | `#23263D` |
| `hover` | `rgba(21,23,41,.06)` | `rgba(255,255,255,.07)` |
| `border` | `#DCDFEE` | `#2C3050` |
| `hairline` | `rgba(21,23,41,.08)` | `rgba(255,255,255,.07)` |
| `fg` | `#151729` | `#ECEEFB` |
| `fg-muted` | `#5B6185` (6.0:1) | `#9AA0C3` (6.9:1) |
| `fg-disabled` | `#A3A8C4` | `#5E6488` |
| `accent` (máta, výplně) | `#14C890` | `#2EE6A8` |
| `accent-hover` / `-pressed` | `#22D99F` / `#0FAE7C` | `#5BF0BD` / `#1FC890` |
| `accent-fg` (text na mátě) | `#052A1E` (7.2:1) | `#05261B` (10:1) |
| `accent-text` (máta jako text) | `#087A58` (5.3:1) | `#2EE6A8` |
| `accent-soft` | `rgba(20,200,144,.14)` | `rgba(46,230,168,.14)` |
| `focus` (ultrafialová) | `#6D5BF0` (s bílým textem 4.8:1) | `#8B7CFF` (s `#0E0B2E` 5.8:1) |
| `selection-bg` | `rgba(109,91,240,.18)` | `rgba(139,124,255,.28)` |
| `gradient` (jen na hrdinských místech) | `#14C890 → #6D5BF0` | `#2EE6A8 → #8B7CFF` |
| `success` | `#2FA84F` | `#7CE85A` |
| `warning` / `warning-text` | `#E08A00` / `#A15C00` | `#FFB547` |
| `error` | `#E5354F` | `#FF5C7A` |
| `info` | `#0E8FD6` | `#38C6FF` |
| `island` (bez blur / s blur) | `rgba(255,255,255,.86)` / `.62` | `rgba(22,24,39,.88)` / `.62` |
| `tooltip` | bg `#151729`, fg `#F4F5FB` (inverzní) | bg `rgba(10,11,20,.95)`, fg `#ECEEFB` |
| `shadow-popup` | `0 12px 28px rgba(28,30,70,.16)` | `0 12px 32px rgba(4,5,14,.55)` |
| `shadow-window` (aktivní / neaktivní) | `0 16px 36px rgba(28,30,70,.18)` / `0 6px 16px rgba(28,30,70,.10)` | `0 18px 40px rgba(0,0,0,.45)` / `0 8px 20px rgba(0,0,0,.28)` |

**Pravidla:**
- Přechod se smí použít jen na: tlačítko menu, kolečko dnešního dne, výplň OSD, `suggested-action` a přepínač ve stavu ON.
- V shellu jen ve dvou zastávkách (`background-gradient-direction: vertical|horizontal`), diagonálně jen v GTK.
- Koralová barva se nepoužívá. Méně barev je silnější.
- LIMIT (kolo 7): v Light musí být konec výplně (`grad_to`) tmavší než `grad_from`, protože D2 vyžaduje ≥ 2,4:1 k `track` (max. luminance ~0,137; `grad_from` má 0,182 a jen 1,96:1), proto se přechod v Light dělá změnou odstínu modrá→azurová (`#2B6FF0→#006AB6`), ne zesvětlením jako v Dark.

### 3.2 Radiusy

Škála **6 / 10 / 12 / 16 / 22 / 999**. Vnořený prvek má radius rodiče minus vnitřní okraj.

| Radius | Kde |
|---|---|
| 6 | checkbox, tagy, položky kontextového menu plochy |
| 10 | tlačítka, entry, combo, spin, položky popupů a menu |
| 12 | okna (CSD; u SSD jen horní rohy), karty a boxed-list, dlaždice docku, položky Alt+Tab, náhledy v expo |
| 16 | popup menu (padding 6), kalendář, notifikace, lišta docku |
| 22 | hlavní menu (padding 12), Alt+Tab |
| 999 | ostrovy top baru, applet pilulky, vyhledávací pole, switch, progress, OSD, odznaky, scrollbar |

Maximalizovaná a dlaždicová okna mají radius 0. Spodní rohy SSD oken zůstanou hranaté.

### 3.3 Typografie

| Prvek | Písmo |
|---|---|
| UI | `Inter 10` |
| Dokumenty | `Inter 10.5` |
| Titulky oken (CSD i SSD) | `Inter Semi-Bold 10` (`titlebar-uses-system-font false`) |
| Hodiny | Inter 600 10.5 pt, `font-feature-settings: "tnum"` |
| Velké nadpisy (měsíc v kalendáři, hlavička menu, hodnota OSD, `.title-1..2`) | Inter Display 600–700, 13–20 pt, `letter-spacing: -0.02em` (jen GTK) |
| Tělo notifikace | 9.5 pt `fg-muted` |
| Monospace | JetBrains Mono 10 (`sudo apt install fonts-jetbrains-mono`) |

Vykreslování nechat beze změny: slight, rgba, rgb, 96 dpi, škálování textu 1.0.

### 3.4 Komponenty shellu

**Top bar (34 px)**
- `.panel-top` je průhledný. `.panelLeft`, `.panelCenter` a `.panelRight` jsou ostrovy:
  - výška 26 px, `margin 4px 6px`;
  - pozadí `island`, `border: 1px hairline`, radius 999;
  - stín `0 4px 14px rgba(0,0,0,.25)` (light `rgba(28,30,70,.10)`).
- Obsah ostrovů:
  - vlevo menu, combined-monitor, auto-dark-light a claude-usage;
  - uprostřed hodiny · počasí (`fg-muted`);
  - vpravo systray a stavové applety.
- `.applet-box`: pilulka, `padding 0 8px`, hover `hover`; otevřený applet `accent-soft` s textem `accent-text`.
- Tlačítko menu: dlaždice 26×26 s radiusem 9, svislý přechod a symbolická ikona Mint v `accent-fg`.
- **Záloha**, pokud zóny ignorují margin: plný panel `island` s 1px hairline dole.

**Dock (64 px)**
- `.panel-left` je průhledný. `.panelLeft.vertical` je plovoucí lišta:
  - šířka 52 px, margin 6 px, radius 16;
  - pozadí `island`, hairline.
- Dlaždice 44×44 s radiusem 12, ikony Papirus 32 px, hover `hover`.
- Běžící okno: `border-left: 3px` v `fg-muted` na 50 %.
- Fokusované okno: dlaždice `accent-soft` a `border-left: 3px` v `accent`.
- Odznak notifikací 6.6 (`.grouped-window-list-notifications-badge`): kolečko 16 px ve `focus` s tmavým číslem.
- Dnešní override `0 14px 14px 0` se zahodí.

**Hlavní menu (stock 6.6)**
- Karta `surface-raised` s radiusem 22, padding 12, hairline, `shadow-popup`.
- Vyhledávání: pilulka 36 px na `surface-alt`, při fokusu `border 2px focus`.
- Kategorie: vybraná je pilulka `selection-bg`.
- Aplikace: hover `hover`, vybraná `selection-bg`, radius 10.
- Systémová tlačítka: kroužky 32 px bez pozadí, vypnutí při hoveru `error`.

**Popupy**
- `surface-raised`, radius 16, padding 6.
- Položky: výška 32 px, radius 10, hover `hover`.
- Oddělovač: 1px `hairline`, margin `6px 10px`.
- Přepínač: SVG assety z Mint-Y přebarvené sedem na `accent`.

**Kalendář**
- Dnešní den: kolečko 30 px se svislým přechodem a číslem v `accent-fg`.
- Víkendy `fg-muted`, události mají levý okraj 3px `accent`.
- Měsíc v Inter Display 600 13 pt.

**Notifikace (`#notification`)**
- Šířka 360, radius 16, `surface-raised`, `shadow-popup`.
- Levý okraj 3px podle naléhavosti: `accent`, `warning` nebo `error`.
- Tlačítka akcí jsou pilulky, primární v `accent` s `accent-fg`.

**OSD (`.media-keys-osd`)**
- Vodorovná pilulka zhruba 260×56, radius 999, `surface-raised`.
- `.level` má výšku 6 px, radius 999, stopa `border` a výplň vodorovným přechodem.

**Alt+Tab (`.switcher-list`)**
- Radius 22, `island` s alfou .92, padding 14.
- Vybraná položka: `selection-bg` a `border 2px focus`, radius 12.
- Název okna Inter 600.

**Expo**
- Pozadí `bg` s alfou .85.
- Okna radius 12, hover `border 2px` v `selection-bg`, vybrané okno `focus`.

**Tooltip**: radius 8, padding `6px 10px`, inverzní barvy.

**Animace**: Nastavení → Efekty, otevření a zavření okna „scale“, minimalizace „traditional“. Easing křivky 6.6 jsou zdarma.

### 3.5 Okna a GTK widgety

**Headerbar**
- Splývá s obsahem: `surface`, bez dělicí čáry, výška 46 px (CSD), u SSD zhruba 36 px.
- Neaktivní okno: titulek `fg-muted`.

**SSD**
- Stejné pravidla v `gtk-3.0` pod `window.ssd headerbar.titlebar` a `.titlebar button.titlebutton`, horní radius 12. Muffin je převezme z GTK motivu sám, žádné `metacity-1`.

**Tlačítka titulku** (`:minimize,maximize,close`)
- Zaoblené čtverce 28×28 s radiusem 9, symbolický glyf 14 px `fg-muted`, v klidu bez pozadí.
- Hover: minimize a maximize `surface-alt`, close plné `error` s glyfem `#2A0710`.
- Neaktivní okno: opacita 0.5. Mezera 4 px.

**Podpisový detail (volitelný)**
- Mátová čárka 24×2 px v levém horním rohu headerbaru aktivního okna:

  ```
  background-image: linear-gradient(to right, accent, focus);
  background-size: 24px 2px;
  background-position: 14px 0;
  background-repeat: no-repeat;
  ```
- Platí pro `headerbar:not(:backdrop)`. Jestli ho vykreslí i Muffin SSD, je třeba ověřit.

**Ostatní widgety**

| Widget | Styl |
|---|---|
| Tlačítka | 34 px, radius 10; výchozí ploché tlačítko s rámečkem |
| `suggested-action` | Přechod, `accent-fg`, `box-shadow 0 4px 14px rgba(46,230,168,.30)` (jen dark) |
| `destructive-action` | `error` |
| Entry | `surface-alt`, při fokusu `border 2px focus` |
| Switch | 44×24, ON = přechod, jezdec bílý |
| Checkbox, radio | ON `accent` s glyfem `accent-fg` |
| Scrollbar | overlay 4 px, při hoveru 8 px |
| Sidebar (Nemo) | `surface-alt`, výběr jako pilulka `selection-bg` |

**libadwaita**
- `libadwaita-1.5` a `1.7` z Mint-Y, v `defaults-*.css` přebarvené na tokeny:
  - `mint_accent`, `accent_bg_color`, `accent_fg_color`;
  - `window_bg_color`, `view_bg_color`, `headerbar_bg_color`, `card_bg_color`, `popover_bg_color`.
- Radiusy volitelně v `base.css`.

### 3.6 Stack

| Vrstva | Volba | URL / zdroj |
|---|---|---|
| GTK3/GTK4 | Orchis, `-t teal -c light dark --tweaks solid --round 12px` (bez `-l`), přebarvení a připojená vrstva `_mentha-gtk.scss` | https://github.com/vinceliuice/Orchis-theme |
| Shell | `/usr/share/themes/Mint-Y{,-Dark}-Teal/cinnamon/` (zkopírovat včetně assetů), sed teal hex na tokeny, připojit `_mentha-shell.scss`. Plán B: Orchis `cinnamon/` | https://github.com/linuxmint/mint-themes |
| libadwaita | `Mint-Y{,-Dark}/libadwaita-1.5` a `-1.7`, přebarvené | lokálně |
| Sass | `sudo apt install sassc` (3.6.1), nebo shim `~/.local/bin/sassc`, který volá `exec npx --yes sass --no-source-map "$@"` | – |
| Ikony | Papirus / Papirus-Dark a papirus-folders `-C teal` | https://github.com/PapirusDevelopmentTeam/papirus-folders |
| Kurzor | Bibata-Modern-Classic (light) a Bibata-Modern-Ice (dark), přes položku mouse-pointer v appletu | https://github.com/stanio/Bibata_Cursor |
| Písma | Inter a Inter Display (nainstalované), JetBrains Mono (apt) | – |
| Tapeta | Vlastní „Mentha Aurora“ z ImageMagick, do `source_folder` dynamic wallpaper | – |
| Blur (volitelně) | BlurCinnamon 2.6.1 (už stažený), jen panely a popupy, Dual Kawase | https://github.com/klangman/BlurCinnamon |
| Login | slick-greeter, motiv zkopírovaný do `/usr/share/themes` | `man slick-greeter` |
| Qt (jen pokud je potřeba) | `qt5ct`/`qt6ct` se stylem Fusion a schématem Mentha. **Ne** Kvantum (není v repu) | apt |
| Flatpak | Jen `flatpak override --user --filesystem=~/.themes:ro` kvůli Inkscape (GTK3) | – |

GIMP 3 má vlastní motivy a Telegram, Discord a Stremio GTK motiv nepoužívají, takže tam se nic neřeší. libadwaita ve Flatpaku zůstane na čisté Adwaitě podle color-scheme a s tím se počítá.

Vynechané kvůli YAGNI: GRUB, Plymouth, Kvantum, systemd služba, symlinky gtk-4.0 a Rewaita.

**Struktura repa** `~/Projekty/mentha-theme` (cesta bez mezer, kvůli skriptům vinceliuice):

```
upstream/Orchis-theme/          # klon, needitovat
src/_mentha-tokens.scss         # jediný zdroj barev, radiusů a písem
src/_mentha-gtk.scss            # headerbar, titlebuttons, window.ssd, suggested-action
src/_mentha-shell.scss          # ostrovy, lišta docku, menu, popupy, OSD, alt-tab, notifikace, overrides 3rd-party appletů
libadwaita/recolor.sh           # sed nad kopií Mint-Y libadwaita-1.5/1.7
wallpaper/gen.sh
check-contrast.py               # assert WCAG >= 4.5 pro páry tokenů
build.sh                        # Orchis build -> recolor -> připojení vrstev -> shell z Mint-Y-Teal -> dist/Mentha-{Light,Dark}
install.sh                      # rsync dist -> ~/.themes, přepnutí motivu tam a zpět kvůli reloadu
```

`index.theme` obsahuje `ButtonLayout=:minimize,maximize,close`.

### 3.7 Postup implementace

**Krok 0: zálohy (před jakoukoli změnou)**

```bash
sudo timeshift --create --comments "pred Mentha" --tags O   # systém: /usr/share/themes, /etc/lightdm (home Timeshift standardně nezálohuje)
mkdir -p ~/zaloha-mentha && cd ~/zaloha-mentha
dconf dump /org/cinnamon/ > cinnamon.ini
dconf dump /org/x/ > x.ini
dconf dump /org/gnome/desktop/interface/ > gnome-iface.ini
tar czf home-theme.tgz -C ~ .themes .config/cinnamon/spices .config/gtk-3.0 .local/share/cinnamon
```

**Kroky 1 až 10**

1. **Rychlé výhry** (oddíl 4). Okamžitý efekt a nic se nestaví.
2. **Repo a tokeny.** Vytvořit repo a `_mentha-tokens.scss`. `check-contrast.py` musí projít.
3. **GTK3/GTK4.** Build Orchis s přebarvením a připojenou vrstvou. Nasadit **jen** `gtk-theme=Mentha-Light`, shell zatím zůstává ZorinMatata. Zkontrolovat Nemo, Xed, dialogy a Firefox s titlebarem (SSD jde přes `window.ssd`).
4. **libadwaita.** Zkopírovat `libadwaita-1.5/1.7`, přebarvit. Test na libadwaita aplikaci (pomůže `ADW_DEBUG_THEMES=1`). Přepnout gtk-theme na Dark a ověřit, že se aplikace za běhu přebarví.
5. **Shell Dark.** Kopie Mint-Y-Dark-Teal, přebarvení a vrstva Mentha. Nejdřív záložní plný panel, pak ostrovy a lišta docku. Ověřit na **obou monitorech** a se všemi 17 applety (weather, combined-monitor, claude-usage, autoclicker).
6. **Shell Light** ze stejného zdroje (dnes ho žádný režim nepoužívá).
7. **auto-dark-light:**
   - světlý režim: aplikace `Mentha-Light`, desktop `Mentha-Dark` (zvyk), nebo `Mentha-Light` k vyzkoušení;
   - tmavý režim: obojí `Mentha-Dark`;
   - ikony: `Papirus` (tmavý shell) / `Papirus-Dark` / `Papirus-Light` (světlý shell);
   - kurzor: Classic / Ice;
   - příkazy:

     ```
     gsettings set org.gnome.desktop.interface color-scheme default|prefer-dark
     ```

   Nic dalšího není potřeba.
8. **Tapety Aurora.** Den a noc do `source_folder` dynamic wallpaper, případně přes background v appletu.
9. **Volitelně:**
   - BlurCinnamon (jen panely a popupy, alfa ostrovů .62). Měřit `top` a plynulost, při zasekávání vypnout.
   - slick-greeter (`sudo cp -r ~/.themes/Mentha-Dark /usr/share/themes/`, `[Greeter] theme-name=Mentha-Dark`, `background=…`, `draw-grid=false`).
   - Flatpak override pro Inkscape.
   - qt5ct pouze pokud přibudou nativní Qt aplikace.
10. **Dokumentace.** Doplnit `Infrastruktura/Asus/dokumentace.md` (sekce motiv) a zápis do `HISTORIE.md`. Smazat lokální kopii `grouped-window-list@cinnamon.org` (je shodná se systémovou a zakrývá aktualizace).

**Rollback**
- **Jeden krok:** v appletu vrátit ZorinMatata, nebo `gsettings set org.cinnamon.desktop.interface gtk-theme ZorinMatata-Light` a `gsettings set org.cinnamon.theme name ZorinMatata-Dark`. ZorinMatata zůstává v `~/.themes`, nic se nemaže.
- **Celé nastavení:**

  ```bash
  dconf reset -f /org/cinnamon/ && dconf load /org/cinnamon/ < ~/zaloha-mentha/cinnamon.ini
  ```

  Totéž pro `/org/x/`. Potom Ctrl+Alt+Esc (restart Cinnamonu).
- **Systém (greeter, `/usr/share/themes`):** obnova z Timeshiftu, případně z TTY.
- **Soubory:** `tar xzf home-theme.tgz -C ~`.

**Hlavní rizika:**
- `margin` na zónách panelu (záloha je připravená);
- 3rd-party applety s natvrdo danými barvami;
- čitelnost ostrovů bez blur nad rušným oknem (alfa .88, doladit);
- obrázek přechodu v headerbaru u Electron aplikací.

Nic jsem nevykresloval kromě testu tapety. Hex hodnoty a rozměry je nutné doladit podle screenshotů.

---

## 4. Rychlé výhry bez nového motivu (asi 10 minut)

1. **Inter místo Ubuntu**

   ```bash
   gsettings set org.cinnamon.desktop.interface font-name 'Inter 10'
   gsettings set org.cinnamon.desktop.wm.preferences titlebar-font 'Inter Semi-Bold 10'
   gsettings set org.gnome.desktop.interface font-name 'Inter 10'
   ```

2. **Papirus s barevnými složkami místo ZorinBlue**
   - Stáhnout skript z https://github.com/PapirusDevelopmentTeam/papirus-folders.
   - Spustit `./papirus-folders -C teal --theme Papirus`, a totéž pro `Papirus-Dark`. Pozor, platí uživatelská kopie v `~/.local/share/icons`.
   - Pak nastavit:

     ```bash
     gsettings set org.cinnamon.desktop.interface icon-theme Papirus
     ```

   - Totéž zadat do položky icons v auto-dark-light.

3. **Kurzor podle režimu:** v auto-dark-light nastavit dark → `Bibata-Modern-Ice`.

4. **Jeden akcent místo dvou modrých** (záloha přes `cp`):

   ```bash
   cp ~/.themes/ZorinMatata-Dark/cinnamon/cinnamon.css{,.bak}
   sed -i 's/#0c75de/#15a6f0/gI' ~/.themes/ZorinMatata-Dark/cinnamon/cinnamon.css
   ```

   Potom přepnout motiv shellu tam a zpět.

5. **Klidnější lišta:** ze 17 appletů dát pryč nebo skrýt to, co nepotřebuješ vidět stále (autoclicker, printers, removable-drives). Méně šumu je největší „prémiový“ krok zdarma.

6. **Efekty:** Nastavení → Efekty, otevření a zavření okna „Scale“.

7. **Tapeta „Mentha Aurora night“** (otestováno dnes, trvá 5 s):

   ```bash
   convert -size 480x270 xc:'#0E0F1A' -fill '#2EE6A8' -draw 'circle 95,215 95,120' \
     -fill '#8B7CFF' -draw 'circle 390,55 390,-40' -blur 0x60 -resize 1920x1080\! \
     -attenuate 0.25 +noise Gaussian -depth 8 ~/Obrázky/mentha-night.png
   ```

   Měkké plochy navíc zlepší čitelnost poloprůhledného panelu.

8. **Úklid:**

   ```bash
   rm -r ~/.local/share/cinnamon/applets/grouped-window-list@cinnamon.org
   ```

   Je shodný se systémovým, ale blokuje jeho aktualizace. Potom Ctrl+Alt+Esc.

Náhled testovací tapety: `/tmp/claude-1000/-home-matata-System-FNS-projekty-AAA-CLAUDE-Infrastruktura-Asus/67be24cf-43e2-4b8a-937e-576e3a4bbbca/scratchpad/mentha-night.png`