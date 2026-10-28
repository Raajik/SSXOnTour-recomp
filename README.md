# SSX On Tour for Linux

Play SSX On Tour (Xbox, 2005) as a native Linux program, at up to 4K, with smooth edges and sharp textures. It is
not an emulator: the game's own code is translated to C on your machine and built into a normal Linux program.

![The same moment of a race at 480p, as on the Xbox, and at 1080p with anti-aliasing, anisotropic filtering and the upscaled textures mod](docs/images/compare-race.jpg)

**You need your own copy of the game.** This repository contains no game code or data. Everything made from your
copy (the translated code, the program, texture packs) stays on your machine; please don't share it.

## What you get

- **Sharp at any resolution:** 480p up to 4K, with up to 8x anti-aliasing and 16x anisotropic filtering.
- **Ink & Color** (optional): richer colours and black ink outlines on the 3D world, for a comic-book look.
- **CRT TV shader** (optional), for the old-television look.
- **Upscaled textures** (optional): an AI-upscaled copy of the game's textures, made from your own copy.
- **Shop preview** (optional): in the shops, highlighting an entry shows it on your rider without pressing A.
- Up to 4 controllers (any controller SDL knows), or the keyboard. Saving and loading work as on the Xbox.
- A settings window (the launcher) for all of the above.

![The rider up close: blocky at 480p, smooth at 1080p, and with ink outlines](docs/images/zoom-rider.jpg)

### Ink & Color

![A race start with Ink & Color off and on](docs/images/compare-ink.jpg)

### Upscaled textures

![The title logo with the original textures and with the upscaled textures mod, both at 1080p](docs/images/compare-textures.jpg)

### The launcher

<img src="docs/images/launcher.png" alt="The launcher: game files, display settings, Ink & Color, asset mods and controllers" width="420">

## What works

Tested on Fedora 44 with an AMD RX 6800 XT: the menus, The Tour, Quick Play races, the shops, controllers and
keyboard, music and sound, saving and loading.

Not supported yet:

- **Widescreen.** The game is 4:3 and shows black bars on a wide screen.
- **Other regions.** Only the North American (NTSC-U) version works. Another version has its code at other addresses
  and is refused; [docs/BRINGUP.md](docs/BRINGUP.md) explains what a port to it involves.
- **Windows, macOS, browser.** Linux x86-64 only. (The Windows and WebAssembly builds this project inherited have not
  been tried with this game.)

## Get started

### 1. Copy the game off your disc

You need SSX On Tour for Xbox, **NTSC-U** (title ID `45410082`): the `default.xbe` file and the `data/` folder from
the disc. If your copy came from a softmodded Xbox and has a `default.xbe_orig`, that is the untouched file; the
setup script uses it.

### 2. Build

```bash
git clone https://github.com/Raajik/SSXOnTour-recomp.git ssxot-recomp
cd ssxot-recomp
scripts/linux-setup.sh /path/to/your/game/files
```

The setup script checks that your system has the build tools (and tells you which packages to install for your
distribution), checks your game files, translates the game (about 5 minutes) and builds it.

### 3. Play

```bash
build-linux/launcher      # the settings window, then press Play
tools/play.sh             # or start the game straight away
```

## Playing

**Controllers:** plug them in before you press Play. Any controller SDL supports works.

**Keyboard** (player 1; the game window must have focus):

| Key | Button | Key | Button |
| --- | --- | --- | --- |
| Enter | Start | Backspace | Back |
| Z / X / A / S | A / B / X / Y | Q / E | White / Black |
| 1 / 3 | Left / right trigger | Arrow keys | D-pad |
| Numpad 8 4 2 6 | Left stick | I J K L | Right stick |
| F11 or Alt+Enter | Fullscreen | F3 | FPS counter |

**Saves** go to `~/.local/share/xboxrecomp/UDATA/45410082/`.

**Intro movies** are skipped. To watch them, untick "Skip the intro movies" in the launcher, or run
`RECOMP_SKIP_INTRO=0 tools/play.sh`.

**Something wrong?** The launcher's **Open logs** button opens the log folder. Set "Log detail" to "Detailed" and
include the newest log when you report a problem.

## Optional mods

Mods are folders in `mods/`. Turn them on and set their order in the launcher's **Asset mods** list. All of them
are off unless you turn them on. [docs/MODS.md](docs/MODS.md) has the details, and how to make your own.

### Upscaled textures

The game's textures, upscaled 4x with Real-ESRGAN. You make the pack yourself, from your own copy:

1. Play with `RECOMP_TEX_DUMP=texdump/ tools/play.sh` and visit everything you want covered (menus, courses,
   riders). Each texture the game shows is saved to `texdump/`.
2. Install [Real-ESRGAN ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan),
   [bc7enc_rdo](https://github.com/richgel999/bc7enc_rdo) and ImageMagick.
3. Run `REALESRGAN=<Real-ESRGAN folder> BC7ENC=<bc7enc binary> tools/upscale_pack.sh texdump mods/upscaled`.
   Add `realesrgan-x4plus` at the end for the general model; the default anime model is sharpest on menus and text.

### Shop preview on highlight

In the Barber, Clothing and Gear shops, highlighting an entry shows its first item on your rider straight away.
Nothing is bought or equipped, and B puts your old look back. Make it from your own game files:

```bash
python3 tools/shop_preview_mod.py game mods
```

## Play on another computer

`tools/portable/` builds one folder with the game, its libraries and start scripts, to copy to another Linux
computer. The folder needs glibc 2.29 or newer (tested on Fedora 44, Ubuntu 22.04 and 24.04) and a Vulkan driver.
It holds your game files, so keep it to yourself. The steps:

1. `prepare_spv.sh`
2. `build_portable.sh` (it builds in Valve's Steam Runtime "sniper" SDK, in podman)
3. `collect_libs.sh`, in the same image
4. `make_bundle.sh build-portable/out "<folder>"`

The folder has `Play SSX On Tour.sh`, `SSX On Tour Settings.sh` (the launcher), and `Play and collect textures.sh`
(for the upscaled textures above).

## Building by hand

`scripts/linux-setup.sh` does the following:

1. `scripts/setup.sh` fetches the xboxrecomp toolkit at the pinned version into `../xboxrecomp-ssxot` and applies
   `patches/xboxrecomp-local.patch`.
2. It copies `default.xbe` into `game/` and links `data/`.
3. `scripts/regen.sh` translates the game to C.
4. `cmake -S . -B build-linux -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C build-linux` builds it.

The build needs a C compiler, CMake, Ninja, SDL2, the Vulkan headers and glslc.

## How it was done

The game's x86 code (`default.xbe`) is translated to C with
[sp00nznet/xboxrecomp](https://github.com/sp00nznet/xboxrecomp), then built with the runtime from
[koenhendriks/SSX3-recomp](https://github.com/koenhendriks/SSX3-recomp): the Xbox kernel and libraries, audio,
input, and a Vulkan renderer for the Xbox GPU.

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

Screenshots are of the game running in this port. SSX On Tour is © 2005 Electronic Arts Inc.
