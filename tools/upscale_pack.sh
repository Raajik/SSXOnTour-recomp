#!/usr/bin/env bash
# Upscale the game's own textures into an asset mod (docs/MODS.md).
#
#   tools/upscale_pack.sh DUMP_DIR MOD_DIR [MODEL]
#
# DUMP_DIR: a RECOMP_TEX_DUMP folder (<key>_<w>x<h>_f<fmt>.tga). MOD_DIR: the mod
# to write, e.g. mods/upscaled (its textures/ is rebuilt). MODEL: a Real-ESRGAN
# model name (default realesrgan-x4plus-anime: sharpest on menus and text).
# Needs ImageMagick, Real-ESRGAN ncnn-vulkan (REALESRGAN=<its folder>) and bc7enc
# from bc7enc_rdo (BC7ENC=<the binary>). The pack is made from your copy's art:
# keep it to yourself, like the generated code.
set -euo pipefail

DUMP=${1:?dump dir}; MOD=${2:?mod dir}; MODEL=${3:-realesrgan-x4plus-anime}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOD=$(realpath -m "$MOD")
ESR=${REALESRGAN:-$HOME/Projects/tools/realesrgan}
BC7ENC=${BC7ENC:-$HOME/Projects/tools/bc7enc_rdo-src/build/bc7enc}
JOBS=${JOBS:-6}
[ -x "$ESR/realesrgan-ncnn-vulkan" ] || { echo "no realesrgan-ncnn-vulkan in $ESR" >&2; exit 1; }
[ -x "$BC7ENC" ] || { echo "no bc7enc at $BC7ENC" >&2; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/png" "$WORK/up" "$MOD"
rm -rf "$MOD/textures" && mkdir -p "$MOD/textures"

echo "1/3 TGA -> PNG"
for f in "$DUMP"/*.tga; do
    b=$(basename "$f" .tga)
    magick "$f" "$WORK/png/$b.png"
done

echo "2/3 upscale x4 ($MODEL)"
"$ESR/realesrgan-ncnn-vulkan" -i "$WORK/png" -o "$WORK/up" -m "$ESR/models" -n "$MODEL" -s 4 -f png > "$WORK/esr.log" 2>&1
# Real-ESRGAN ncnn upscales alpha softly, not with the model, and a font page's
# glyphs are only in its alpha (the colour is flat white): every menu word stayed
# blurry. So each texture that is not opaque also has its alpha, as a grey image,
# run through the model, and that replaces the soft one.
mkdir -p "$WORK/a" "$WORK/aup"
for f in "$WORK"/png/*.png; do
    b=$(basename "$f")
    [ "$(magick "$f" -format '%[opaque]' info:)" = True ] && continue
    magick "$f" -alpha extract -colorspace sRGB -type TrueColor "$WORK/a/$b"
done
if [ -n "$(ls "$WORK/a")" ]; then
    "$ESR/realesrgan-ncnn-vulkan" -i "$WORK/a" -o "$WORK/aup" -m "$ESR/models" -n "$MODEL" -s 4 -f png >> "$WORK/esr.log" 2>&1
    for f in "$WORK"/aup/*.png; do
        b=$(basename "$f")
        magick "$WORK/up/$b" -alpha off \( "$f" -colorspace gray \) -compose CopyOpacity -composite "PNG32:$WORK/up/$b"
    done
    echo "   alpha through the model too: $(ls "$WORK/aup" | wc -l) textures"
fi

echo "3/3 BC7 DDS with mip chains"
# One texture: halve with ImageMagick down to 1x1, BC7 each level, join the
# levels into one DDS (tools/dds_mips.py). Each channel is resized on its own:
# ImageMagick's RGBA resize weights colour by alpha, which turns the colour of
# alpha-0 pixels black, and some game textures (a glow drawn by a blend that
# ignores alpha) need that colour -- it showed as a black block in the distance.
encode_one() {
    png=$1; b=$(basename "$png" .png); dir=$(mktemp -d "$WORK/mip.XXXXXX")
    cp "$png" "$dir/l0.png"
    w=$(magick identify -format %w "$png"); h=$(magick identify -format %h "$png"); i=0
    while [ "$w" -gt 1 ] || [ "$h" -gt 1 ]; do
        w=$(( w > 1 ? w / 2 : 1 )); h=$(( h > 1 ? h / 2 : 1 )); i=$((i + 1))
        magick "$dir/l0.png" -separate -filter Box -resize "${w}x${h}!" -combine "$dir/l$i.png"
    done
    levels=()
    for n in $(seq 0 "$i"); do
        (cd "$dir" && "$BC7ENC" -q -g "l$n.png" "l$n.dds" > /dev/null) || return 1
        levels+=("$dir/l$n.dds")
    done
    python3 -I "$HERE/tools/dds_mips.py" "$WORK/up/$b.dds" "${levels[@]}"
    rm -rf "$dir"
}
export -f encode_one
export WORK BC7ENC HERE
ls "$WORK"/up/*.png | xargs -P "$JOBS" -I{} nice bash -c 'encode_one "$1"' _ {} > "$WORK/bc7.log" 2>&1 || true
cd "$WORK/up"
n_png=$(ls ./*.png | wc -l); n_dds=$(ls ./*.dds 2>/dev/null | wc -l)
if [ "$n_dds" -ne "$n_png" ]; then
    echo "$((n_png - n_dds)) of $n_png textures failed to encode; see the log:" >&2
    tail -20 "$WORK/bc7.log" >&2
    exit 1
fi

{
    echo "# Real-ESRGAN $MODEL x4 of the game's own textures (tools/upscale_pack.sh)"
    for d in ./*.dds; do
        b=$(basename "$d" .dds)
        key=${b%%_*}
        mv "$d" "$MOD/textures/$key.dds"
        echo "$key $key.dds"
    done
} > "$MOD/textures/ssx3_map.txt"
case $MODEL in *anime*) kind=anime ;; *) kind=general ;; esac
printf 'Upscaled textures (%s)\nReal-ESRGAN %s x4 of the game'"'"'s own textures (made locally, not shared)\n' "$kind" "$MODEL" > "$MOD/mod.txt"

n=$(grep -vc '^#' "$MOD/textures/ssx3_map.txt" || true)
echo "done: $n textures in $MOD/textures ($(du -sh "$MOD/textures" | cut -f1))"
