/**
 * Game-state hooks the shared code (renderer, logs, thread dumps) asks for.
 *
 * SSX3-recomp answers these from SSX 3's own memory (game_state.c, the
 * overrides). SSX On Tour's addresses are not known yet, so until they are
 * each hook gives the neutral answer: not in game, 4:3, no rider positions,
 * nothing to dump. The ssx3_ names stay as the shared code uses them.
 */
#include <stdint.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>

/* The target's shape (width / height; 4/3 = no widescreen). Starts as
 * RECOMP_ASPECT; the Vulkan backend changes it at a flip when the window is
 * resized (ssx3_SetAspect). */
static volatile float s_aspect = -1.0f;

float ssx3_Aspect(void)
{
    if (s_aspect < 0.0f) {
        const char *e = getenv("RECOMP_ASPECT");
        double a = e ? atof(e) : 0;
        s_aspect = a > 4.0 / 3.0 + 0.01 ? (float)a : 4.0f / 3.0f;
    }
    return s_aspect;
}

void ssx3_SetAspect(float a)
{
    s_aspect = a > 4.0f / 3.0f + 0.01f ? a : 4.0f / 3.0f;
}

int ssx3_InGame(void) { return 0; }
int ssx3_InGameNow(void) { return 0; }
int ssx3_InGameMenuUp(void) { return 0; }
int ssx3_WidescreenNow(void) { return 0; }
int ssx3_PlayerPos(float out[3]) { (void)out; return 0; }
int ssx3_RiderPos(int i, float out[3]) { (void)i; (void)out; return 0; }
const char *ssx3_ScreenNow(void) { return "unknown"; }
void ssx3_WhereNow(char *out, size_t n) { if (n) out[0] = 0; }
void ssx3_JobTraceDump(void) {}
void ssx3_StreamDump(void) {}
void ssx3_StrmTraceDump(void) {}
void *ssx3_lookup_trace(uint32_t va) { (void)va; return NULL; }
int ssx3_lensfx_nowait;
