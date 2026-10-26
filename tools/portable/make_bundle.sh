#!/usr/bin/env bash
# Make the one-click SSX On Tour folder (docs/LINUX.md) from a portable
# build (build_portable.sh, then bin/ + lib/ with the bundled libraries).
#
#   tools/portable/make_bundle.sh BUILD_OUT DEST
#
# BUILD_OUT holds bin/ssxot_recomp, bin/launcher and lib/. DEST becomes the folder.
# It holds your own game files: for your own machines only, never to publish.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT=${1:?build output with bin/ and lib/}; DEST=${2:?destination folder}
[ -x "$OUT/bin/ssxot_recomp" ] && [ -x "$OUT/bin/launcher" ] || { echo "no binaries in $OUT/bin" >&2; exit 1; }
[ -e "$HERE/game/default.xbe" ] || { echo "no game/default.xbe in $HERE" >&2; exit 1; }
mkdir -p "$DEST"
DEST=$(realpath "$DEST")

echo "binaries and libraries"
# A folder made before keeps its launcher.ini (the player's settings).
ini_keep=
[ -f "$DEST/bin/launcher.ini" ] && { ini_keep=$(mktemp); cp "$DEST/bin/launcher.ini" "$ini_keep"; }
rm -rf "$DEST/bin" "$DEST/lib" && cp -r "$OUT/bin" "$OUT/lib" "$DEST/"

echo "game files (a real copy, ~2 GB)"
mkdir -p "$DEST/game"
cp "$HERE/game/default.xbe" "$DEST/game/"
[ -e "$DEST/game/data" ] || cp -rL "$HERE/game/data" "$DEST/game/data"

echo "mods, keys"
mkdir -p "$DEST/mods"
for m in "$HERE"/mods/*/; do
    [ -d "$m" ] && { rm -rf "$DEST/mods/$(basename "$m")"; cp -rL "$m" "$DEST/mods/"; }
done
# A folder made before keeps its load order (the mods the player ticked).
[ -f "$HERE/mods/load-order.txt" ] && [ ! -f "$DEST/mods/load-order.txt" ] && cp "$HERE/mods/load-order.txt" "$DEST/mods/"
cp "$HERE/keys.example.ini" "$DEST/"
[ -f "$HERE/keys.ini" ] && cp "$HERE/keys.ini" "$DEST/"
# The launcher's settings, without the game folder path: it then finds game/ itself.
if [ -n "$ini_keep" ]; then mv "$ini_keep" "$DEST/bin/launcher.ini"
elif [ -f "$HERE/build-linux/launcher.ini" ]; then grep -v '^game_dir=' "$HERE/build-linux/launcher.ini" > "$DEST/bin/launcher.ini"
fi

# Start scripts: bundled libraries first. The launcher saves the game folder as a full path, so a moved
# folder would point at the old place: a saved path with no default.xbe is dropped, and game/ is found again.
start_script() {   # $1 file, $2 launcher argument
    cat > "$1" <<EOS
#!/bin/sh
here=\$(cd "\$(dirname "\$0")" && pwd)
ini="\$here/bin/launcher.ini"
gd=\$(sed -n 's/^game_dir=//p' "\$ini" 2>/dev/null)
[ -n "\$gd" ] && [ ! -f "\$gd/default.xbe" ] && sed -i '/^game_dir=/d' "\$ini"
export LD_LIBRARY_PATH="\$here/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
cd "\$here/bin" && exec ./launcher $2
EOS
    chmod +x "$1"
}
start_script "$DEST/Play SSX On Tour.sh" "--play"
start_script "$DEST/SSX On Tour Settings.sh" ""
cat > "$DEST/Play and collect textures.sh" <<'EOS'
#!/bin/sh
# As "Play SSX On Tour.sh", and each texture the game shows for the first time is saved to
# texdump/, to build the upscaled packs from (tools/upscale_pack.sh in ssxot-recomp).
here=$(cd "$(dirname "$0")" && pwd)
RECOMP_TEX_DUMP="$here/texdump" exec "$here/Play SSX On Tour.sh"
EOS
chmod +x "$DEST/Play and collect textures.sh"

cat > "$DEST/install-shortcuts.sh" <<'EOS'
#!/bin/sh
# App-menu entries for "Play SSX On Tour" and "SSX On Tour Settings", pointing at this folder.
here=$(cd "$(dirname "$0")" && pwd)
# Exec= field codes: % is %%, and " ` $ \ are escaped inside the quotes.
exec_here=$(printf '%s' "$here" | sed -e 's/%/%%/g' -e 's/[\\"`$]/\\\\&/g')
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$apps"
for e in "play:Play SSX On Tour:Play SSX On Tour.sh" "settings:SSX On Tour Settings:SSX On Tour Settings.sh"; do
    id=${e%%:*}; rest=${e#*:}; name=${rest%%:*}; script=${rest#*:}
    cat > "$apps/ssxot-$id.desktop" <<EOD
[Desktop Entry]
Type=Application
Name=$name
Exec="$exec_here/$script"
Path=$here
Icon=applications-games
Categories=Game;
Terminal=false
EOD
done
echo "Added \"Play SSX On Tour\" and \"SSX On Tour Settings\" to the app menu."
echo "Steam: Games > Add a Non-Steam Game > Browse > $here/Play SSX On Tour.sh"
EOS
chmod +x "$DEST/install-shortcuts.sh"

cat > "$DEST/README.txt" <<'EOS'
SSX On Tour -- native Linux (static recompilation), your own copy
================================================================

Start it one of these ways:

  Play SSX On Tour.sh      the game, straight away, with the settings you last
                           chose. Works with only a controller: use this one in Steam.
  SSX On Tour Settings.sh  the settings window (resolution, Ink & Color, mods,
                           controllers); its Play button starts the game.
  Play and collect textures.sh
                           as Play, and saves each texture the game shows to
                           texdump/, for making the upscaled packs cover more.
  install-shortcuts.sh     puts both in your app menu, and shows how to add
                           "Play SSX On Tour" to Steam (Games > Add a Non-Steam Game).

In Steam's gaming mode, add "Play SSX On Tour.sh" as a non-Steam game; Steam shows it
fullscreen.

Needs: a Vulkan GPU driver and the usual desktop libraries (X11 or Wayland,
ALSA or PulseAudio, libXtst); a desktop Linux has them. Everything else is in
this folder. After moving the folder, run install-shortcuts.sh again. Saves are in
~/.local/share/xboxrecomp/UDATA/45410082/ (copy that too when you move the
game to another machine). Logs: logs/ next to game/.

This folder holds your own game files.
Keep it for your own machines; don't share it.
EOS

echo "done: $DEST ($(du -sh "$DEST" | cut -f1))"
