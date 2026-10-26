#!/usr/bin/env bash
# Play: the keyboard is player 1 (merged with any pad); output goes to
# play_stdout.txt / play_stderr.txt.
#   tools/play.sh          play
#   tools/play.sh diag     with frame, GPU and audio diagnostics
# Keyboard (the game window must have focus):
#   Enter START   Backspace BACK   Z X A S = A B X Y   Q E = white / black
#   1 3 = left / right trigger   arrows = d-pad   numpad 8/4/2/6 = left stick
#   I J K L = right stick   Shift / Ctrl = stick clicks   F3 FPS counter
#   F11 / Alt+Enter fullscreen
cd "$(dirname "$0")/.." || exit 1
export RECOMP_KEYBOARD="${RECOMP_KEYBOARD:-1}"
if [ "${1:-}" = diag ]; then
    export RECOMP_FRAME_STATS=1 RECOMP_SLOW_STACKS=50 RECOMP_VKR_STATS=1 \
           RECOMP_GUESTCPU_STATS=1 RECOMP_APU_LEVEL=1 RECOMP_VKR_GPUPROF=25 \
           RECOMP_FPS_OVERLAY=1
fi
exec build-linux/ssxot_recomp > play_stdout.txt 2> play_stderr.txt
