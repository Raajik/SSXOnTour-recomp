# SSX On Tour (Xbox) static recompilation: notes for coding agents

Read README.md (build steps) and docs/BRINGUP.md (addresses, problems found, tools) first.

- The project was copied from SSX3-recomp; SSX 3's game code was removed. Some names still say `ssx3_`
  (game-state hooks in `src/game_hooks.c`, the `SSX3_VULKAN` macro) because the shared code uses them.
- Toolkit: `../xboxrecomp-ssxot`, xboxrecomp at the base in `scripts/setup.sh` plus `patches/xboxrecomp-local.patch`.
  After changing the toolkit, regenerate the patch (tracked and untracked files; not `.venv` or `tools/*/output`)
  and check that `git apply --reverse --check` passes in the toolkit.
- Regen after a change to `src/ssxot_overrides.c`: `scripts/regen.sh lift` (about a minute). After a seed change:
  `scripts/regen.sh` (about 5 minutes). Write overrides out as `void sub_XXXXXXXX(void)`: the lifter does not see
  functions defined through macros.
- Never commit `src/recomp/gen/`, `decomp/`, `game/`, logs or builds: they are the game's code and data.
- Headless check: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy RECOMP_NO_HOST_PAD=1 timeout -s KILL 60
  build-linux/ssxot_recomp`, with `RECOMP_PAD_SCRIPT` for presses and `RECOMP_SNAP_TRIGGER` for screenshots.
  TRACE lines (peeks, kernel calls) only show with `RECOMP_LOG_LEVEL=trace`.
