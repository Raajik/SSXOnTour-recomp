# SSX On Tour (Xbox) static recompilation — agent notes

Read `~/specs/ssxot-recomp.md` (spec, decisions, addresses found, open items) and
`~/specs/xbox-recomp-playbook.md` first. README.md has the build steps.

- Started 2026-10-25 as a copy of SSX3-recomp c05700d; SSX 3's game code was removed. Some names still say
  `ssx3_` (game-state hooks in `src/game_hooks.c`, the `SSX3_VULKAN` macro): the shared code uses them.
- Toolkit: `../xboxrecomp-ssxot`, a git worktree of `../xboxrecomp` at 193e299 with
  `patches/xboxrecomp-local.patch` (SSX 3's patch plus this game's fixes). Never edit `../xboxrecomp`: that is
  SSX3-recomp's toolkit. After a toolkit change, regenerate the patch (untracked files included, `.venv` and
  `tools/*/output` excluded) and check `git apply --reverse --check`.
- Regen after a change to `src/ssxot_overrides.c`: `scripts/regen.sh lift` (1 min). After a seed change:
  `scripts/regen.sh` (5 min). Overrides must be written out as `void sub_XXXXXXXX(void)`; the lifter does not
  see functions defined through macros.
- Never commit `src/recomp/gen/`, `decomp/`, `game/`, logs or builds. Never write to `~/xbox-backup`.
- Headless check: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy RECOMP_NO_HOST_PAD=1 timeout -s KILL 60
  build-linux/ssxot_recomp`, with `RECOMP_PAD_SCRIPT` for presses and `RECOMP_SNAP_TRIGGER` for screenshots.
  TRACE lines (peeks, kernel calls) only show with `RECOMP_LOG_LEVEL=trace`.
