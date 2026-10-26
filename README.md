# SSX On Tour (Xbox) — static recompilation for Linux

Runs SSX On Tour (NTSC-U, title ID `45410082`, XDK 5849) from your own Xbox disc rip as a native Linux program,
with [sp00nznet/xboxrecomp](https://github.com/sp00nznet/xboxrecomp). The runtime around the game (Vulkan
renderer for the NV2A, launcher, logging) comes from
[koenhendriks/SSX3-recomp](https://github.com/koenhendriks/SSX3-recomp); the game-specific code is new.

This repo holds no game code or data. `scripts/regen.sh` lifts your own `default.xbe` to C locally.

## Status (2026-10-25)

Boots to the title screen, menus, Quick Play races at 30 FPS, sound, pad and keyboard, saving and loading
options. Not yet play-tested by a person. Spec and findings: `~/specs/ssxot-recomp.md` (on the author's machines).

## Build (Fedora 44)

```bash
scripts/setup.sh                       # toolkit in ../xboxrecomp-ssxot at the pinned base + patches/xboxrecomp-local.patch
mkdir -p game && cp <rip>/default.xbe game/ && ln -s <rip>/data game/data   # an untouched default.xbe
scripts/regen.sh                       # ~5 min: lift the XBE to src/recomp/gen/
cmake -S . -B build-linux -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja -C build-linux
tools/play.sh                          # keyboard: Enter = Start, Z/X/A/S = A/B/X/Y, arrows = d-pad
```

Packages: see `docs/LINUX.md`. Saves go to `~/.local/share/xboxrecomp/UDATA/45410082/`.

## Settings this game needs (defaults in `src/main.c`)

- `RECOMP_HEAP_RECLAIM=1`: EA's heap setup frees and re-allocates a probed contiguous block.
- `RECOMP_CONTIG_AVOID_IMAGE=1`: keeps contiguous memory out of the image's physical pages (the USB pad).
- `RECOMP_SKIP_INTRO` (default on): the EA logo and intro movie are skipped through `RECOMP_EMPTY_FILES`.

## Bring-up tools

- `scripts/seed_loop.sh`: regen, build, headless run, and feed unresolved indirect calls back as seeds.
- `tools/imm_code_refs.py`: callbacks registered in code (immediates), which the disassembler misses.
- `tools/match_funcs.py`: find SSX 3's library functions in this XBE by bytes, addresses masked.
- `RECOMP_FS_TRACE=1`, `RECOMP_SAVE_TRACE=1`: EA archive opens and the save system's natives and results.

`docs/` is inherited from SSX3-recomp (see `docs/README.md`); much of it describes SSX 3.
