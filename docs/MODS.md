# Asset mods

A mod is a folder in `mods/`, next to `hd-textures/` (the game's working directory; `RECOMP_MODS_DIR` points
elsewhere). Turn mods on and order them in the launcher's **Asset mods** list, or by hand in
`mods/load-order.txt`: one folder name per line, `#` starts a comment, and a **later line wins** when two mods
change the same file. A mod that is not listed is off. The launcher rewrites this file when you press Play, so
comments in it do not survive that.

```text
mods/
├── load-order.txt
└── my-mod/
    ├── mod.txt              # line 1: the mod's name; line 2: what it does (shown in the launcher)
    ├── data/...             # replaces the game file at the same path under game/data/
    └── textures/            # a texture pack, same format as hd-textures/
        ├── ssx3_map.txt     # <texture key> <file.dds> [a2]
        └── *.dds            # BC7 (DXGI 98/99), DX10 header
```

- **Files**: whole files only. When the game opens `data/char/anm.big`, it gets `mods/my-mod/data/char/anm.big`
  if an enabled mod has it, else the game's own. Names match without regard to case. SSX 3 does not write to its
  game folder, so mod files are only read; the layer itself does not block a write.
  The SSX modding community's tools (for example SSXModding/SSXTools) read and write SSX 3's formats.
- **Textures**: a texture key is the hash of the original texture's pixels. `RECOMP_TEX_DUMP=<dir>` writes every
  texture the game decodes as `<key>_<w>x<h>_f<format>.tga`, so you can find the key of the one you want to change.
  A surface redrawn every frame is written for its first 8 frames only: from an address's 9th new set of pixels, each
  less than a second after the last, nothing more is written. Up to 8 palettes of one texture are all kept; a texture
  first drawn at such an address within that second is missed. **Verified**
  (`tests/hdtex_dump_test.c`; before it, a 23-minute play wrote 17,794 files, 4 GB, about 15,300 of them the rider's
  shadow, the pillarbox frame and other surfaces redrawn every frame, **Observed** in the user's collect run).
  The enabled mods' packs come before the HD pack, in the same order as the files; `RECOMP_HDTEX=0` turns off only
  the HD pack.
- The session log says which mods are on (`[SETTINGS] asset mods: ...`); `xbox_kernel.log` names each file a mod
  replaced, once.

Mods ship only their own work: no files from the game.

## Upscaled textures

`tools/upscale_pack.sh DUMP MOD [MODEL]` turns a `RECOMP_TEX_DUMP` folder into a texture mod: Real-ESRGAN
(ncnn-vulkan, x4) on each texture, then BC7 with bc7enc (bc7enc_rdo) and a full mip chain. `MODEL` is
`realesrgan-x4plus-anime` (default, sharpest on menus and text) or `realesrgan-x4plus` (the general model). Each
mip level is resized one channel at a time: ImageMagick's alpha-weighted resize turned the colour of a glow texture
with near-zero alpha black, which showed as a black block. A texture that is not opaque also has its alpha run
through the model as a grey image: Real-ESRGAN ncnn upscales alpha softly, and font pages keep their glyphs only in
alpha (flat white colour), so every menu word stayed blurry. **Observed** (one font page, old and new alpha side by
side, 2026-10-26). Dump while playing every mode you want covered; the
pack covers only the textures in the dump. A pack is made from your copy's art: keep it to yourself.

## Shop preview on highlight

`tools/shop_preview_mod.py GAME_DIR MODS_DIR` makes `shop-preview` from your own `screens.viv`. On, highlighting a
shop menu entry (Barber Shop > Hair Style: Mohawk, Caesar, ...; Clothing Shop: Boots; Gear Shop: Tricks) shows that
entry's first item on the rider, as A does on entering it; nothing is bought or equipped, and B puts the old look
back. The shipped game already previews inside an item list (Facial Hair, a style's colours). Off, the game plays
as shipped. **Verified** (headless on save copies, mod on and off, 2026-10-27: Hair Style Down shows Caesar, Short
Shaved, Dyed, B restores the mohawk; Boots shows its first boots; money unchanged; leaving and coming back shows
the equipped look; `tests/shop_preview_mod_test.py`).
- The game opens `screens.viv|<member>` as a loose file before the archive, so a mod file at
  `data/fe/screens/screens.viv|data/fe/screens/ssx/fe/shops/<shop>.big` replaces that member. **Verified** (the
  kernel log's "asset mod shop-preview replaces ...", and the patched screen ran).
- The shop screens are EA APT: RefPack-compressed, Flash-like bytecode with a constant pool. The loader relocates
  each code stream in order, so a patch is made in place, the same size: here the input handler's dead debug branch
  (`extern.Debug` + CIRCLE) and its default call. A jump from the handler into another function's dead body never
  ran. **Observed** (headless, natives traced).
- In a menu the patch calls `FEShops.BrowseItem(0, GetEntries(child).link)` for an entry whose
  `GetNumEntries(child).type` is 1 (an item list); B always calls `FECac.CachePolicy(kClearCache)`, as the shipped
  game did only when leaving an item list. The tool checks each shop's bytes and leaves out one it does not know.
