# Bring-up: how SSX On Tour was made to run

What it took to get SSX On Tour (Xbox, NTSC-U) from a fresh lift to a playable game, for anyone porting another
build or another game. Each fact says how it is known: **Verified** (checked by a test or a run), **Observed**
(seen in a trace, a log or the disassembly) or **Unknown**.

## The disc

- Title ID `45410082`, "SSX™ On Tour", region NTSC-U, built 2005-09-02, XDK 5849 for every library. Entry point
  `0x001A2C40`. `.text` at `0x11000`, `0x2A0310` bytes, FNV-1a 64 hash `0xB8FA3A4C454898A5` (`src/main.c` and
  `scripts/linux-setup.sh` check it). Observed.
- A softmodded console's `default.xbe` has 4 header bytes patched; `default.xbe_orig` beside it is the original.
  Use the original. Observed.
- Another build (PAL, another region) has other addresses: everything below that names an address is this
  build's. Unknown whether the PAL disc differs in code; SSX 3's PAL and NTSC discs did.

## Starting point

- The project is a copy of SSX3-recomp (its runtime, Vulkan renderer, launcher, logging) with SSX 3's game code
  removed. `src/game_hooks.c` answers the renderer's game-state questions neutrally. Observed.
- The toolkit is xboxrecomp at 193e299 (v0.13.1) with `patches/xboxrecomp-local.patch`: SSX 3's toolkit changes
  plus this game's. `scripts/setup.sh` checks it out next to this repo as `../xboxrecomp-ssxot`. Observed.
- XDK library fixes SSX 3 needed carry over by byte match with addresses masked (`tools/match_funcs.py`): CRT
  `exp` `0x00286B50` and `fmod` `0x00286C84`, DirectSound effects download `0x002E2AA1`, D3D gamma ramp
  `0x002C0886`, D3D PGRAPH interrupt `0x002C2730`. The D3D device pointer is at `0x002D1DE8`, the D3D section's
  most-read global. Observed. There is no XAPI media check in this build (no test of cert+0x1D8). Observed.

## Seeds (functions reached only through pointers)

- `scripts/seed_loop.sh`: regen, build, a headless run, then feed `[ICALL] Failed to resolve VA` targets and
  thread starts back into `analysis/icall_seeds.json`. Verified (the game runs with no unresolved calls).
- Some callbacks are set as immediates in code (XPP's driver tables, APT natives), so they only appear when the
  game reaches that code (the pad, the menus). `tools/imm_code_refs.py` lists them; keep only callback-shaped
  uses (`push imm`, `mov [mem], imm`) and drop constants (round numbers such as `0x000F4240`): a seed in the
  middle of an instruction splits a real function. Observed (a careless filter crashed boot).

## Problems found and their fixes (all in the toolkit patch unless noted)

| Symptom | Cause | Fix | How known |
|---|---|---|---|
| Crash 0.2 s in, every register `0xA1A1A1A1` | EA's heap setup probes the largest contiguous block, frees it, allocates it less 1.375 MB, fills it with `0xA1`; frees did nothing, so the fill went through a NULL pointer | `RECOMP_HEAP_RECLAIM=1` (default in `src/main.c`) | Verified |
| Pad never enumerates | XPP's OHCI HCCA was allocated at physical `0x00202000`, inside the image's range, and the USB model read `.text` as the table | `RECOMP_CONTIG_AVOID_IMAGE=1` (default): contiguous memory starts above the image | Verified |
| Hang after the legal screen in a D3D loop at `0x002BB570` | D3D 5849 reads its GPU progress marker from `PGRAPH_PATT_COLOR0` (0x400B10), written by NV044 `SET_MONOCHROME_COLOR0` (method 0x0310, subchannel 5), which the executor dropped | the executor emulates it for the subchannel whose object (from the title's RAMHT) is class 0x44 | Verified |
| Intro movie stuck on its first frame; "Saving Options" never ends | `NtSetTimerEx` was a stub: the game's 60 Hz clock (thread `0x00222E71`, counter `0x003EBFD4`) waits on a waitable timer and never ticked; the movie player and the save screen's 3 s minimum use it | `NtSetTimerEx` arms the timer; `NtCreateTimer` honours the timer type; POSIX periodic timers (`tests/win32_waitable_timer`) | Verified |
| Crash ~5 s into the first tour race | D3D's `EndVisibilityTest` asks for report pages below 16 MB (`GET_REPORT` offsets are 24 bits); the range was ignored, and the report writes landed on a game object | `MmAllocateContiguousMemoryEx` honours its range and 15-16 MB is kept for such requests (as upstream 13d9637) | Verified |
| Music is noise | voices played at 48 kHz whatever their pitch (upstream 148431d); DirectSound turns the APU setup engine off and on about every 10 ms, a microsecond window on the console that takes 5-10 ms here, and the frame thread emitted silence through it | resampler backport; an off window under 50 ms counts as running; upstream 7fe4d49 | Verified (recorded output; the player confirmed) |
| A short freeze at the first race start with a texture pack, music distorted | the pack's BC7 textures share the 32 MB per-frame upload buffer with the draws; a race start loading many filled it, and ~800 draws were dropped (`[VKR] upload buffer full`). Most of the freeze was first-time shader compiles (451 ms), which RADV keeps on disk | a full buffer submits what is recorded, waits, and starts again (`buf_room` in `vkr.c`) | Verified (`vkr_selftest`: four 16 MB textures and a draw in one frame) |

Ink & Color (`RECOMP_INK`, the scene pass inherited from SSX 3) needs the frame's camera, fitted from the terrain's
vertex program. This game's terrain is `BF72911C`: drawn in every race frame, all its draws giving one camera; it
is the default for `RECOMP_SCENE_VSH`. `C4F7A68E` looks plausible but draws objects with their own model matrices: each draw
gives a different camera, and the ink lines came and went. Verified with `RECOMP_CAMFIT_TRACE=1` and
`tools/camfit_score.py` in a headless race (other programs agree too, but appear in fewer frames), and screenshots with Ink on.

`RECOMP_SKIP_INTRO` (default on) skips the EA logo and intro movie through `RECOMP_EMPTY_FILES`, which serves
matching game files as empty (`tests/kernel_mods`). Verified.

## Tools that found these

- gdb on the running game: guest memory is at `0x100000000000 + VA`; thread samples
  (`thread apply all bt`); hardware watchpoints on a guest word (`watch *(unsigned int*)0x1000…`) with
  `handle SIGSEGV nostop noprint pass` (the runtime uses SIGSEGV for MMIO).
- `RECOMP_PEEK=0x…` + `RECOMP_PEEK_EVERY_MS=…` at `RECOMP_LOG_LEVEL=trace` to watch a variable.
- rizin reads XBEs: `rizin -2 -qc 'pD 0x80 @ 0x…' game/default.xbe`.
- `RECOMP_PAD_SCRIPT` (button presses at times) and `RECOMP_SNAP_TRIGGER` (screenshots) for headless runs.
- Audio: `SDL_AUDIODRIVER=disk SDL_DISKAUDIOFILE=out.raw` records what is played; `RECOMP_APU_VOICE_TRACE=<file>`
  (`_V=<voice>` for one voice every frame) shows voice formats and play positions.
- `RECOMP_CAMFIT_TRACE=1` + `tools/camfit_score.py`: which vertex program draws the world, for the scene pass.
- `RECOMP_FS_TRACE=1` (EA archive opens), `RECOMP_SAVE_TRACE=1` (save natives and the storage thread's results).
