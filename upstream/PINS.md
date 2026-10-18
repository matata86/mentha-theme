# Upstream sources

Mentha is built on top of two GPL-3.0 projects. Only the parts the build reads are kept here, unmodified
(the build copies them to `build/work/` and never edits this directory).

| Directory | Project | Commit | Used paths |
|-----------|---------|--------|------------|
| `mint-themes/` | https://github.com/linuxmint/mint-themes (Clement Lefebvre, GPL-3+) | `984fced9da446f90750421fda9a56ef0a5a5b881` | `src/Mint-Y/cinnamon`, `src/Mint-Y/libadwaita-1.5`, `src/Mint-Y/libadwaita-1.7`, `debian/copyright` |
| `Orchis-theme/` | https://github.com/vinceliuice/Orchis-theme (Vince Liuice, GPL-3.0) | `a4c48a425e63808345e824495964bd9c2f462e04` | `src/_sass`, `src/gtk`, `src/gtk-2.0`, `COPYING` |

To update: replace the paths above from a checkout of the new commit, update this table and rebuild
(`build/libadwaita-recolor.py` stops with an error when an upstream pattern it patches has changed).
