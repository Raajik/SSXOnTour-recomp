#!/usr/bin/env bash
# From your own SSX On Tour rip to a playable Linux build, in one command:
#
#   scripts/linux-setup.sh <rip folder | disc image .iso>
#
# 1. checks the tools and libraries the build needs, and says what to install
#    (it never runs sudo itself),
# 2. puts the game in game/: from a folder, default.xbe is copied and the rest
#    linked (regen writes beside the XBE, never into your rip); an ISO is
#    extracted (extract-xiso or xdvdfs),
# 3. checks default.xbe is SSX On Tour, the build this project was made for,
# 4. runs scripts/setup.sh, scripts/regen.sh and the CMake/Ninja build.
#
# Safe to re-run: an existing game/ is kept, setup.sh skips what is done.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-}"
if [ -z "$SRC" ] || [ ! -e "$SRC" ]; then
    echo "usage: scripts/linux-setup.sh <rip folder with default.xbe and data/ | disc image .iso>" >&2
    exit 2
fi
SRC="$(realpath "$SRC")"

# ── 1. dependencies ─────────────────────────────────────────────────────
missing=()
for c in git python3 cmake ninja cc glslc pkg-config; do
    command -v "$c" >/dev/null || missing+=("$c")
done
if command -v pkg-config >/dev/null; then
    for m in sdl2 epoxy openssl vulkan; do
        pkg-config --exists "$m" || missing+=("lib:$m")
    done
    for m in SDL2_ttf fontconfig; do
        pkg-config --exists "$m" || echo "note: $m not found: the game builds, the launcher is skipped"
    done
fi
if [ ${#missing[@]} -gt 0 ]; then
    echo "missing: ${missing[*]}" >&2
    id=$(. /etc/os-release 2>/dev/null && echo "${ID:-} ${ID_LIKE:-}")
    case " $id " in
        *" fedora "*|*" rhel "*)
            echo "  sudo dnf install gcc gcc-c++ cmake ninja-build git python3 sdl2-compat-devel SDL2_ttf-devel \\" >&2
            echo "      fontconfig-devel libepoxy-devel openssl-devel vulkan-headers vulkan-loader-devel glslc" >&2 ;;
        *" arch "*)
            echo "  sudo pacman -S --needed base-devel cmake ninja git python sdl2 sdl2_ttf fontconfig libepoxy \\" >&2
            echo "      openssl vulkan-headers vulkan-icd-loader shaderc" >&2 ;;
        *" debian "*|*" ubuntu "*)
            echo "  sudo apt-get install build-essential cmake ninja-build git python3 pkg-config libsdl2-dev \\" >&2
            echo "      libsdl2-ttf-dev libfontconfig-dev libepoxy-dev libssl-dev libvulkan-dev glslc" >&2 ;;
        *)
            echo "  a C toolchain, cmake, ninja, pkg-config, SDL2, SDL2_ttf, fontconfig, libepoxy, OpenSSL," >&2
            echo "  the Vulkan headers and loader, and glslc (all with headers)" >&2 ;;
    esac
    exit 1
fi

# ── 2. the game files ───────────────────────────────────────────────────
GAME="$HERE/game"
if [ -L "$GAME" ] && [ ! -e "$GAME" ]; then
    echo "game/ is a link to a folder that is gone ($(readlink "$GAME")): remove it or remount, then re-run" >&2
    exit 1
elif [ -e "$GAME/default.xbe" ] || [ -e "$GAME/DEFAULT.XBE" ]; then
    echo "game/: already there, kept"
elif [ -d "$SRC" ]; then
    xbe=default.xbe
    [ -e "$SRC/$xbe" ] || xbe=DEFAULT.XBE
    # A softmodded console patches header bytes of default.xbe and keeps the
    # original beside it: use the original.
    orig=""
    [ -e "$SRC/default.xbe_orig" ] && orig="$SRC/default.xbe_orig"
    [ -e "$SRC/$xbe" ] || {
        echo "$SRC has no default.xbe: pick the folder that holds default.xbe and data/" >&2; exit 1; }
    [ -e "$GAME" ] && { echo "game/ exists but has no default.xbe: move it away first" >&2; exit 1; }
    # The XBE is copied (3 MB) because regen writes its analysis beside it; the
    # rest (2 GB of data/) is linked, so your rip is read, never written.
    mkdir "$GAME"
    cp "${orig:-$SRC/$xbe}" "$GAME/$xbe"
    for f in "$SRC"/*; do
        case "$(basename "$f")" in "$xbe"|default.xbe_orig) continue ;; esac
        ln -s "$f" "$GAME/$(basename "$f")"
    done
    echo "game/: ${orig:+default.xbe_orig as }$xbe copied, the rest linked from $SRC"
else
    mkdir -p "$GAME"
    if command -v extract-xiso >/dev/null; then
        extract-xiso -x "$SRC" -d "$GAME"
    elif command -v xdvdfs >/dev/null; then
        xdvdfs unpack "$SRC" "$GAME"
    else
        rmdir "$GAME"
        echo "to read a disc image, install extract-xiso or xdvdfs, or extract it and pass the folder" >&2
        exit 1
    fi
fi
XBE="$GAME/default.xbe"
[ -e "$XBE" ] || XBE="$GAME/DEFAULT.XBE"

# ── 3. is it this build of SSX On Tour? ─────────────────────────────────
python3 -I - "$XBE" <<'EOF2'
import struct, sys
d = open(sys.argv[1], "rb").read()
if d[:4] != b"XBEH":
    sys.exit(f"{sys.argv[1]} is not an Xbox executable")
base, cert = struct.unpack_from("<I", d, 0x104)[0], struct.unpack_from("<I", d, 0x118)[0]
tid = struct.unpack_from("<I", d, cert - base + 8)[0]
name = d[cert - base + 0xC:cert - base + 0xC + 80].decode("utf-16-le", "replace").split("\0")[0]
if tid != 0x45410082:
    sys.exit(f"this is {name or 'another game'} (title {tid:08X}), not SSX On Tour (45410082)")
n, at = struct.unpack_from("<II", d, 0x11C)
for i in range(n):
    _, va, _, raw, size, _ = struct.unpack_from("<IIIIII", d, at - base + i * 56)
    if va == 0x11000:
        h = 0xCBF29CE484222325
        for b in d[raw:raw + size]:
            h = ((h ^ b) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        if size != 0x2A0310 or h != 0xB8FA3A4C454898A5:
            sys.exit("this is another build of SSX On Tour than the NTSC-U disc this project was made for "
                     "(docs/BRINGUP.md says how to find the addresses for another build)")
print(f"default.xbe: {name}, title {tid:08X}, NTSC-U build")
EOF2

# ── 4. toolkit, lift, build ─────────────────────────────────
"$HERE/scripts/setup.sh"
XBE="$XBE" "$HERE/scripts/regen.sh"
cmake -S "$HERE" -B "$HERE/build-linux" -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja -C "$HERE/build-linux"

echo
echo "Done. Play: build-linux/launcher (settings window), or tools/play.sh"
