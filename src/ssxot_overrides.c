/**
 * SSX On Tour - hand-written replacements for generated functions.
 *
 * Every sub_XXXXXXXX defined here replaces the generated body: the pipeline is
 * run with --exclude-manual src/ssxot_overrides.c, which skips generating any
 * function this file defines, so direct calls link to these.
 *
 * This file includes recomp_types.h rather than declaring the registers itself
 * the way recomp_manual.c does: the registers are thread-local, and a plain
 * `extern uint32_t g_eax` names the TLS template, not the running thread's copy.
 */
#include "log.h"
#ifdef _WIN32
#include <windows.h>
#else
#include "platform/win32_compat.h"
#endif
#include "recomp/gen/recomp_types.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * The XDK library fixes SSX3-recomp needed, carried over: SSX On Tour links
 * the same libraries (XDK 5849 here, 5558 there). Each function below was
 * found by tools/match_funcs.py: its bytes equal SSX 3's with only
 * addresses masked, so the reasons in SSX 3's notes hold.
 *
 * Not carried over: SSX 3's XAPI startup media check (the security-sector
 * read). This XAPI has no such code (no test of cert+0x1D8 anywhere).
 */

/*
 * CRT math through the x87 transcendental dispatcher, replaced natively.
 *
 * sub_00286B50 is exp(double) and sub_00286C84 is fmod(double, double):
 * cdecl, arguments on the stack, result pushed on the x87 stack. Both reach
 * the CRT's hand-written dispatcher (ctrandisp1/ctrandisp2 -> trandisp*, a
 * computed `jmp [ebx]` into shared tails), and in SSX 3 the lifted path
 * returned with the caller's ebx replaced by stale stack data
 * ("[ABI] ...: ebx 00000000->...", RECOMP_ABI_CHECK).
 *
 * Unlike SSX 3, other stubs here reach the same dispatchers too (from
 * 0x002A3878 on); they stay lifted until one shows the same fault.
 */
static double arg_double(uint32_t va)
{
    union { uint32_t u[2]; double d; } v;
    v.u[0] = MEM32(va);
    v.u[1] = MEM32(va + 4);
    return v.d;
}

static void fp_push_result(double v)
{
    g_fp_top = (g_fp_top + 7) & 7;
    g_fp_stack[g_fp_top] = v;
}

/* double exp(double) */
void sub_00286B50(void)
{
    fp_push_result(exp(arg_double(g_esp + 4)));
    g_esp += 4;
}

/* double fmod(double, double) */
void sub_00286C84(void)
{
    fp_push_result(fmod(arg_double(g_esp + 4), arg_double(g_esp + 12)));
    g_esp += 4;
}

/*
 * DirectSound effects-image download (XDK DSOUND): after copying the image
 * it posts command 3 to the GP DSP at *(*(*(this+8)+0x10)) + 0x810 and
 * spins until the DSP clears it. The DSP is a stub, so the toolkit's DSP
 * ack clears it -- this registers the word from the object itself.
 */
extern void sub_002E2AA1_gen(void);
extern int xbox_DspAckAdd(uint32_t va);

void sub_002E2AA1(void)
{
    uint32_t p = g_ecx;
    if (p) p = MEM32(p + 8);
    if (p) p = MEM32(p + 0x10);
    if (p) p = MEM32(p);
    if (p)
        xbox_DspAckAdd(p + 0x810);
    sub_002E2AA1_gen();
}

/* D3D's gamma-ramp upload (SetGammaRamp's hardware half): 256 R, then G,
 * then B bytes at [esp+4], written through the NV2A's VGA palette port,
 * which our MMIO does not keep. Hand the ramp to the presenter (toolkit
 * fb_gamma.c), then run the original. */
extern void sub_002C0886_gen(void);
extern void xbox_FramebufferSetGammaRamp(const uint8_t *r, const uint8_t *g, const uint8_t *b);

void sub_002C0886(void)
{
    uint32_t ramp = MEM32(g_esp + 4);
    if (ramp) {
        const uint8_t *p = (const uint8_t *)XBOX_PTR(ramp);
        xbox_FramebufferSetGammaRamp(p, p + 256, p + 512);
    }
    sub_002C0886_gen();
}

/*
 * D3D's PGRAPH interrupt handler, wrapped so a software-method trap is seen
 * exactly once. The handler acknowledges by writing PGRAPH_INTR back with
 * the value it read -- write-1-to-clear on hardware, a no-op on our
 * RAM-backed registers -- and its DPC re-runs it while PMC_INTR_0 bit 12
 * stays set. In SSX 3 one trapped flip NOP became thousands of flips. The
 * toolkit clears the trap the moment the handler returns.
 */
extern void sub_002C2730_gen(void);
extern void xbox_Nv2aSwmHandled(void);

void sub_002C2730(void)
{
    sub_002C2730_gen();
    xbox_Nv2aSwmHandled();
}

/*
 * EA file layer, archive open (RECOMP_FS_TRACE=1): sub_00221F4C(path, ?,
 * &out) is thiscall (this = the file system), ret 0xC. It strips "D:\",
 * splits "archive|member" at '|', walks the mounted archives (list at
 * this+0x30: +0 next, +8 archive, +0xC name; names compared with strcmp)
 * and asks sub_0021E575(archive, member, 0, &offset, &size) for the
 * member. Returns the open file's index, or -1, and then the caller asks
 * the OS for the whole "archive|member" path, which fails.
 */
extern void sub_00221F4C_gen(void);

static int fs_trace_on(void)
{
    static int on = -1;
    if (on < 0)
        on = getenv("RECOMP_FS_TRACE") != NULL;
    return on;
}

static void guest_str(uint32_t va, char *out, size_t n)
{
    size_t i;
    for (i = 0; i + 1 < n && va >= 0x10000u && va < 0x84000000u; i++) {
        uint8_t c = MEM8(va + i);
        if (!c)
            break;
        out[i] = c >= 32 && c < 127 ? (char)c : '.';
    }
    out[i] = 0;
}

void sub_00221F4C(void)
{
    uint32_t self = g_ecx, path = MEM32(g_esp + 4);
    char p[160];
    if (fs_trace_on()) {
        uint32_t e;
        int k = 0;
        guest_str(path, p, sizeof p);
        fprintf(stderr, "[FS] open \"%s\" this %08X mounts:", p, self);
        for (e = MEM32(self + 0x30); e >= 0x10000u && e < 0x84000000u && k < 16; e = MEM32(e), k++) {
            char nm[64];
            guest_str(e + 0xC, nm, sizeof nm);
            fprintf(stderr, " [%s arc %08X]", nm, MEM32(e + 8));
        }
        fprintf(stderr, "\n");
    }
    sub_00221F4C_gen();
    if (fs_trace_on())
        fprintf(stderr, "[FS]   -> %d\n", (int)g_eax);
}

/* The member lookup the open above uses, cdecl (archive, member, flags,
 * &offset, &size); nonzero when found. */
extern void sub_0021E575_gen(void);

void sub_0021E575(void)
{
    uint32_t arc = MEM32(g_esp + 4), member = MEM32(g_esp + 8);
    char m[160];
    if (fs_trace_on())
        guest_str(member, m, sizeof m);
    sub_0021E575_gen();
    if (fs_trace_on())
        fprintf(stderr, "[FS]   lookup arc %08X \"%s\" -> %d\n", arc, m, (int)g_eax);
}

/*
 * The front end's save natives (RECOMP_SAVE_TRACE=1): ActionScript calls
 * them by name (registered next to "SetAutoSave" at 0x0009D10C). Logs each
 * call and what it returns, to follow the autosave prompt's "Yes", which
 * stops on "Saving Options" without a file call.
 */
static int save_trace_on(void)
{
    static int on = -1;
    if (on < 0)
        on = getenv("RECOMP_SAVE_TRACE") != NULL;
    return on;
}

static void save_trace(const char *label, uint32_t a1, uint32_t a2)
{
    if (save_trace_on())
        fprintf(stderr, "[SAVE] %s(%08X, %08X) -> %08X\n", label, a1, a2, g_eax);
}

extern void sub_00094560_gen(void);
void sub_00094560(void)
{
    uint32_t a1 = MEM32(g_esp + 4), a2 = MEM32(g_esp + 8);
    sub_00094560_gen();
    save_trace("QuerySave", a1, a2);
}

extern void sub_00094680_gen(void);
void sub_00094680(void)
{
    uint32_t a1 = MEM32(g_esp + 4), a2 = MEM32(g_esp + 8);
    sub_00094680_gen();
    save_trace("Save", a1, a2);
}

extern void sub_00094EB0_gen(void);
void sub_00094EB0(void)
{
    uint32_t a1 = MEM32(g_esp + 4), a2 = MEM32(g_esp + 8);
    sub_00094EB0_gen();
    save_trace("SetAutoSave", a1, a2);
}

extern void sub_00095210_gen(void);
void sub_00095210(void)
{
    uint32_t a1 = MEM32(g_esp + 4), a2 = MEM32(g_esp + 8);
    sub_00095210_gen();
    save_trace("IsMemCardDirtyFlag", a1, a2);
}

/* The storage thread's result posts (RECOMP_SAVE_TRACE=1): thiscall on the
 * result block 0x003EEEF8 with (code, operation, ...); the front end reads
 * the block back (sub_00226C8E). With the storage state at 0x003EF13C. */
extern void sub_00225DEE_gen(void);
void sub_00225DEE(void)
{
    if (save_trace_on())
        fprintf(stderr, "[SAVE] post A code %X op %X arg %08X | state %X\n", MEM32(g_esp + 4),
                MEM32(g_esp + 8), MEM32(g_esp + 12), MEM32(VA(0x003EF13C)));
    sub_00225DEE_gen();
}

extern void sub_0022CF1C_gen(void);
void sub_0022CF1C(void)
{
    if (save_trace_on())
        fprintf(stderr, "[SAVE] post B code %X op %X arg %08X %08X | state %X\n", MEM32(g_esp + 4),
                MEM32(g_esp + 8), MEM32(g_esp + 12), MEM32(g_esp + 16), MEM32(VA(0x003EF13C)));
    sub_0022CF1C_gen();
}

/* The storage system's per-frame tick (RECOMP_SAVE_TRACE=1): sub_00226C8E(dt)
 * adds dt to the "Saving..." minimum-display timer at 0x003EEB64 (+4
 * elapsed, +8 duration, 3000 ms) when it is armed. Logs dt once a second. */
extern void sub_00226C8E_gen(void);
void sub_00226C8E(void)
{
    if (save_trace_on()) {
        static DWORD last;
        static unsigned calls;
        DWORD now = GetTickCount();
        calls++;
        if (now - last >= 1000) {
            fprintf(stderr, "[SAVE] tick dt %d (%u calls) timer armed %u elapsed %d of %d\n",
                    (int)MEM32(g_esp + 4), calls, MEM8(VA(0x003EEB64)), (int)MEM32(VA(0x003EEB68)),
                    (int)MEM32(VA(0x003EEB6C)));
            last = now;
            calls = 0;
        }
    }
    sub_00226C8E_gen();
}
