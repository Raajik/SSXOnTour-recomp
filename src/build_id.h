/* Force-included into the hand-written sources (CMakeLists.txt). This
 * program is made for one disc: SSX On Tour NTSC-U, .text sha256 6c786579...
 * Address literals are written VA(0x...) as in SSX3-recomp, where a port
 * file could remap them; here they are the identity. */
#ifndef SSXOT_BUILD_ID_H
#define SSXOT_BUILD_ID_H
#define SSX3_BUILD_VARIANT "ntsc"
#define SSX3_BUILD_NAME "NTSC-U"
#define VA(x) (x##u)
#endif
