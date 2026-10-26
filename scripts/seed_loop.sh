#!/usr/bin/env bash
# Bring-up loop: regen (with the seeds so far), build, a headless run, then
# feed the run's unresolved indirect calls and thread starts back into
# analysis/icall_seeds.json. Stops when a run adds no seed.
#   scripts/seed_loop.sh [seconds per run, default 60] [max rounds, default 5]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TK="$(dirname "$HERE")/xboxrecomp-ssxot"
SECS="${1:-60}"; ROUNDS="${2:-5}"
cd "$HERE"
mkdir -p logs
for ((r = 1; r <= ROUNDS; r++)); do
    nice -n 10 scripts/regen.sh > logs/regen.txt 2>&1 || { echo "regen failed (logs/regen.txt)"; exit 1; }
    nice -n 15 ninja -C build-linux -j6 > logs/build.txt 2>&1 || { echo "build failed (logs/build.txt)"; exit 1; }
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy RECOMP_NO_HOST_PAD=1 \
        timeout -s KILL "$SECS" nice build-linux/ssxot_recomp > logs/loop.out 2> logs/loop.err
    echo "round $r: exit $?, $(grep -c 'Failed to resolve' logs/loop.err) unresolved icalls, crash: $(grep -m1 -o "CRASH\] signal [0-9]* at pc=[^,]*" logs/loop.err)"
    before=$(grep -c '"start"' analysis/icall_seeds.json)
    (cd "$TK" && .venv/bin/python -m tools.seed_from_log "$HERE/logs/loop.err" "$HERE/game/default.xbe" \
        --functions tools/disasm/output/functions.json --seeds "$HERE/analysis/icall_seeds.json" | grep -E "^ +\+|^seeds:")
    after=$(grep -c '"start"' analysis/icall_seeds.json)
    [ "$after" -gt "$before" ] || { echo "no new seeds"; exit 0; }
done
