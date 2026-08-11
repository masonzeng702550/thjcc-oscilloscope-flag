#!/usr/bin/env python3
"""
Decorrelate the sample song's stereo image so its side channel stops being a
dead giveaway for the payload's location.

Method: Mid/Side widening driven by an all-pass cascade.

    S_new = allpass_cascade(M) * width
    L = M + S_new,  R = M - S_new

Two properties make this the right tool here:

  * an all-pass filter changes only PHASE, not magnitude -- the song's timbre
    and spectral balance are untouched, it just stops being mono;
  * the mono sum L+R collapses back to exactly 2*M, so the widening is
    perfectly mono-compatible and cannot be undone into an audible artefact.

Run directly to sweep width values and print the resulting contrast table.
"""

import numpy as np
from scipy.signal import lfilter

import generate as G
import solve as S

# Schroeder all-pass cascade: coprime-ish delays, moderate feedback
AP_DELAYS = (137, 229, 349, 521)
AP_GAIN = 0.7


def allpass(x, delay, g):
    b = np.zeros(delay + 1); b[0] = -g; b[-1] = 1.0
    a = np.zeros(delay + 1); a[0] = 1.0;  a[-1] = -g
    return lfilter(b, a, x)


def decorrelate(mono):
    y = mono
    for d in AP_DELAYS:
        y = allpass(y, d, AP_GAIN)
    return y


def widen(stereo, width):
    """Return a widened copy, preserving the mono sum exactly."""
    mid = (stereo[:, 0] + stereo[:, 1]) / 2.0
    side = decorrelate(mid) * width
    out = np.stack([mid + side, mid - side], axis=1)
    peak = np.abs(out).max()
    return out / peak * 0.95 if peak > 0.95 else out


def measure(stereo):
    L, R = stereo[:, 0], stereo[:, 1]
    side = (L - R) / 2.0
    mid = (L + R) / 2.0
    return {
        "corr": float(np.corrcoef(L, R)[0, 1]),
        "side_rms": float(np.sqrt((side ** 2).mean())),
        "side_mid": float(np.sqrt((side ** 2).mean()) /
                          max(np.sqrt((mid ** 2).mean()), 1e-12)),
    }


def payload_side_rms():
    contours = G.flag_contours(G.FLAG_LINES)
    frame = G.build_frame(contours, G.FRAME_SAMPLES, G.TRANSIT_SAMPLES) * G.DRAW_LEVEL
    return float(np.sqrt((((frame[:, 0] - frame[:, 1]) / 2) ** 2).mean()))


def main():
    sr, song = S.load("_song.wav")
    p_side = payload_side_rms()
    base = measure(song)

    print(f"payload side RMS = {p_side:.5f}\n")
    print(f"  {'width':>6} | {'L/R corr':>9} | {'side RMS':>9} | {'side/mid':>8} | contrast")
    print(f"  {'-'*6}-+-{'-'*9}-+-{'-'*9}-+-{'-'*8}-+---------")
    print(f"  {'orig':>6} | {base['corr']:9.4f} | {base['side_rms']:9.5f} | "
          f"{base['side_mid']:8.4f} | {p_side/base['side_rms']:6.0f}x")

    for w in (0.10, 0.20, 0.30, 0.45, 0.60, 0.80):
        m = measure(widen(song, w))
        print(f"  {w:6.2f} | {m['corr']:9.4f} | {m['side_rms']:9.5f} | "
              f"{m['side_mid']:8.4f} | {p_side/m['side_rms']:6.1f}x")


if __name__ == "__main__":
    main()
