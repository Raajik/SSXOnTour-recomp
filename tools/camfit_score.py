"""Rank vertex programs as the scene pass's camera source (RECOMP_SCENE_VSH).

    RECOMP_CAMFIT_TRACE=1 ... build-linux/ssxot_recomp 2> run.err   (during a race)
    python3 tools/camfit_score.py run.err [from_seconds]

A terrain program draws world positions, so every one of its draws in a frame
gives the same eye ("agree" near 1.00) and that eye moves smoothly from frame
to frame (no jumps). A program that draws objects with their own model matrix
gives a different eye per draw (low "agree") and is not a camera.
"""
import collections
import math
import re
import statistics
import sys

LINE = re.compile(r"\+\s*([\d.]+) \w+ +\[CAMFIT\] f (\d+) prog (\w+) eye (\S+) (\S+) (\S+)")


def majority(eyes):
    return max(eyes, key=lambda e: sum(math.dist(e, x) < 5 for x in eyes))


def main(path, start=0.0):
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for line in open(path, errors="replace"):
        m = LINE.search(line)
        if m and float(m.group(1)) >= start:
            by[m.group(3)][int(m.group(2))].append(tuple(map(float, m.group(4, 5, 6))))
    rows = []
    for prog, frames in by.items():
        fs = sorted(frames)
        maj = {f: majority(frames[f]) for f in fs}
        agree = statistics.mean(sum(math.dist(e, maj[f]) < 5 for e in frames[f]) / len(frames[f]) for f in fs)
        steps = [math.dist(maj[a], maj[b]) for a, b in zip(fs, fs[1:]) if b == a + 1]
        draws = sum(len(v) for v in frames.values()) / len(fs)
        rows.append((agree, draws, prog, len(fs), statistics.median(steps) if steps else 0.0,
                     sum(s > 1000 for s in steps)))
    print("program   frames draws/frame agree step(median) jumps>1000")
    for agree, draws, prog, nf, step, jumps in sorted(rows, reverse=True):
        print(f"{prog}  {nf:6d} {draws:11.1f} {agree:5.2f} {step:12.1f} {jumps:10d}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)
