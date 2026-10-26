# SSX On Tour (Xbox) for Linux, by static recompilation

Play SSX On Tour from your own Xbox disc as a native Linux program: no emulator. The game's x86 code
(`default.xbe`) is lifted to C on your machine with [sp00nznet/xboxrecomp](https://github.com/sp00nznet/xboxrecomp),
then built with the runtime from [koenhendriks/SSX3-recomp](https://github.com/koenhendriks/SSX3-recomp): the
Xbox kernel and libraries, audio, input, and a Vulkan renderer for the Xbox GPU.

**This repository contains no game code or data.** You need your own copy of the game. The lifted C, the build
and your game files stay on your machine; please don't share them.

## Status

Tested on Fedora 44 (AMD RX 6800 XT, RADV): boot, menus, The Tour and Quick Play races, controller and keyboard,
music and sound, saving and loading. Linux x86-64 only so far. The Windows and WebAssembly builds inherited from
SSX3-recomp have not been tried with this game.

## What you need

- SSX On Tour for Xbox, **NTSC-U** (title ID `45410082`), copied off the disc: `default.xbe` and `data/`. Another
  region or build has other code addresses and will be refused; [docs/BRINGUP.md](docs/BRINGUP.md) explains
  what a port to it involves. If your copy came from a softmodded console and has a `default.xbe_orig`, that is
  the untouched file and the setup script uses it.
- Build tools, SDL2, Vulkan headers and glslc. The setup script lists the packages for your distribution.

## Build and play

```bash
git clone https://github.com/Raajik/SSXOnTour-recomp.git ssxot-recomp && cd ssxot-recomp
scripts/linux-setup.sh /path/to/your/rip      # checks packages and the disc, lifts (~5 min) and builds
tools/play.sh                                  # or build-linux/launcher for the settings window
```

By hand, the script does: `scripts/setup.sh` (fetches xboxrecomp at the pinned version into `../xboxrecomp-ssxot`
and applies `patches/xboxrecomp-local.patch`), copies `default.xbe` into `game/` and links `data/`, runs
`scripts/regen.sh`, then `cmake -S . -B build-linux -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C build-linux`.

Saves go to `~/.local/share/xboxrecomp/UDATA/45410082/`. Controls: any SDL game controller, or the keyboard
(Enter = Start, Z/X/A/S = A/B/X/Y, arrows = d-pad; the full map is at the top of `tools/play.sh`). The intro
movies are skipped; `RECOMP_SKIP_INTRO=0 tools/play.sh` plays them.

To play on another machine, `tools/portable/` makes one folder with the game, its libraries and start scripts (it
needs glibc 2.29 or newer; tested on Fedora 44 and in Ubuntu 22.04 and 24.04 containers): `prepare_spv.sh`, `build_portable.sh` (Valve's Steam Runtime "sniper" SDK in
podman), `collect_libs.sh` inside the same image, then `make_bundle.sh build-portable/out "<folder>"`. The folder
holds your game files: keep it to yourself. It needs a Vulkan driver and the usual desktop libraries.

## How it was done

[docs/BRINGUP.md](docs/BRINGUP.md) lists every problem found on the way (memory layout, GPU, timers, USB, audio),
its cause and its fix, and the tools that found them. The toolkit fixes are in `patches/xboxrecomp-local.patch`;
the ones xboxrecomp does not have yet are offered upstream
([#265](https://github.com/sp00nznet/xboxrecomp/pull/265) timers,
[#266](https://github.com/sp00nznet/xboxrecomp/pull/266) audio).

## Credits

- [sp00nznet/xboxrecomp](https://github.com/sp00nznet/xboxrecomp): the recompiler and runtime this rests on.
- [koenhendriks/SSX3-recomp](https://github.com/koenhendriks/SSX3-recomp) and its contributors: the project this
  one was copied from, with its renderer, launcher and toolkit work.
- [xemu](https://github.com/xemu-project/xemu): the reference for the Xbox GPU and audio hardware.

## License

GPL-2.0-or-later, as SSX3-recomp (see [LICENSE](LICENSE)). The xboxrecomp toolkit, fetched separately, is under its
own licenses (MIT, and LGPL-2.1 for parts from xemu).
