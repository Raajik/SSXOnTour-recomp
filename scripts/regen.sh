#!/usr/bin/env bash
# Regenerate everything derived from the XBE: analysis, the per-function asm
# split (decomp/) and the lifted C (src/recomp/gen/). Neither output is in git
# -- both are the game's code -- so run this after cloning and whenever an
# override is added to src/ssxot_overrides.c (it excludes those bodies).
#
#   scripts/regen.sh                 # all steps
#   scripts/regen.sh lift            # only the C lift (after adding an override)
#
# XBE defaults to game/default.xbe; set XBE=... otherwise. The analysis JSON
# must sit beside the XBE, so the parse step writes there: keep game/ a real
# folder, never a link to the backup.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TK="${TK:-$(dirname "$HERE")/xboxrecomp-ssxot}"
PY="${PY:-$TK/.venv/bin/python}"
XBE="$(realpath "${XBE:-$HERE/game/default.xbe}")"
ANALYSIS="$(dirname "$XBE")/default_analysis.json"
# DOLBY is DSP56300 microcode for the audio chip, not x86: never disassemble it.
SECTIONS=(--text-only --extra-sections D3D,D3DX,XGRPH,DSOUND,XPP)
# Entry points only reached through function pointers, measured at runtime
# ([ICALL] Failed to resolve VA ...). Both disasm and the split need them.
SEEDS=(--seed-functions "$HERE/analysis/icall_seeds.json")

cd "$TK"
if [ "${1:-all}" = all ]; then
    "$PY" -m tools.xbe_parser "$XBE" --json "$ANALYSIS" > /dev/null
    "$PY" -m tools.disasm "$XBE" "${SECTIONS[@]}" "${SEEDS[@]}"
    "$PY" -m tools.func_id "$XBE"
    "$PY" -m tools.abi_analysis "$XBE"
    # tools.split ignores names in functions.json; split_named.py does not.
    "$PY" "$HERE/tools/split_named.py" --xboxrecomp "$TK" "$XBE" --out "$HERE/decomp" "${SECTIONS[@]}" "${SEEDS[@]}"
fi
"$PY" -m tools.recomp "$XBE" --all --split 250 --game-name "SSX On Tour" \
    --gen-dir "$HERE/src/recomp/gen" \
    --exclude-manual "$HERE/src/ssxot_overrides.c"
# Stores through MEMn become explicit STn(addr, value), as SSX 3 does for its
# wasm build (see the script). Same meaning natively.
python3 "$HERE/tools/explicit_stores.py" "$HERE"/src/recomp/gen/*.c
