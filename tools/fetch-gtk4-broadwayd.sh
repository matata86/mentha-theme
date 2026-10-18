#!/bin/bash
# Jednorázově: stáhne gtk4-broadwayd (balík libgtk-4-bin) ve verzi shodné se systémovým libgtk-4-1
# a rozbalí ho do ~/.cache/mentha-qa (bez apt/sudo, systém se nemění). SHA256 se ověřuje proti apt seznamům.
# Důvod: GTK4 broadway klient 4.14 nekomunikuje s gtk4-broadwayd z flatpak runtime (jiný protokol) -> prázdné okno.
set -euo pipefail
dest="$HOME/.cache/mentha-qa/gtk4"
[ -x "$dest/usr/bin/gtk4-broadwayd" ] && { echo "$dest/usr/bin/gtk4-broadwayd"; exit 0; }
ver=$(dpkg-query -W -f='${Version}' libgtk-4-1)
file=$(awk -v v="$ver" '/^Package: /{pk=$2} /^Version:/{vv=$2} /^Filename:/{f=$2} /^SHA256:/{if(pk=="libgtk-4-bin"&&vv==v&&f ~ /amd64/){print f" "$2; exit}}' /var/lib/apt/lists/*amd64_Packages || true)
[ -n "$file" ] || { echo "libgtk-4-bin $ver nenalezen v apt seznamech" >&2; exit 1; }
path=${file% *}; sha=${file#* }
mirror=http://archive.ubuntu.com/ubuntu
tmp=$(mktemp -d)
curl -fsSL "$mirror/$path" -o "$tmp/pkg.deb"
echo "$sha  $tmp/pkg.deb" | sha256sum -c - >&2
mkdir -p "$dest"
dpkg-deb -x "$tmp/pkg.deb" "$dest"
rm -rf "$tmp"
echo "$dest/usr/bin/gtk4-broadwayd"
