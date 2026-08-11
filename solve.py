#!/usr/bin/env python3
"""
Reference solution for the oscilloscope-music challenge.

Pipeline:
  1. isolate the payload segment (the loud, buzzy middle section)
  2. recover the inter-channel delay by scanning for the sharpest X-Y image
  3. undo Mid/Side:  L = M + S,  R = M - S
  4. scatter-plot L vs R -> the flag
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.io import wavfile

MAX_DELAY = 4000


def load(path):
    sr, data = wavfile.read(path)
    x = data.astype(np.float64)
    if np.issubdtype(data.dtype, np.integer):
        x /= np.iinfo(data.dtype).max
    return sr, x


def find_payload(x, sr, block=16384, min_lag=1200, max_lag=8000,
                 periodic_thresh=0.95, level_thresh=0.30):
    """Locate the drawing segment: it is both LOUD and LONG-LAG PERIODIC.

    Neither test alone is enough:
      * loudness alone fails against a mastered music bed, which is as loud
        as the payload;
      * periodicity alone fails against a sustained tonal pad, which really is
        perfectly periodic.
    The payload is the only thing that is both -- the beam retraces a
    sample-identical path every frame, at a lag far below audio pitch rates.

    Note the unbiased autocorrelation normalisation: dividing by the overlap
    length (block - lag) rather than by block. Without it, long lags are
    penalised purely for having less overlap and the payload scores ~0.63
    instead of ~0.995.
    """
    mono = x.mean(axis=1)
    n_fft = 1 << (2 * block - 1).bit_length()
    hop = block // 2
    lags = np.arange(max_lag + 1)
    starts = list(range(0, max(1, len(mono) - block), hop))

    env = np.array([np.abs(mono[s:s + block]).max() for s in starts])
    loud = env > level_thresh * env.max()

    scores = np.zeros(len(starts))
    for i, s in enumerate(starts):
        if not loud[i]:
            continue
        b = mono[s:s + block]
        b = b - b.mean()
        spec = np.fft.rfft(b, n_fft)
        ac = np.fft.irfft(spec * np.conj(spec), n_fft)[:max_lag + 1]
        ac /= np.maximum(block - lags, 1)          # unbiased
        ac /= ac[0] + 1e-12
        scores[i] = ac[min_lag:max_lag].max()

    hot = np.flatnonzero(loud & (scores > periodic_thresh))
    if len(hot) == 0:
        hot = np.flatnonzero(loud)
    if len(hot) == 0:
        return x

    splits = np.split(hot, np.flatnonzero(np.diff(hot) > 2) + 1)
    run = max(splits, key=len)
    return x[run[0] * hop: min(len(x), run[-1] * hop + block)]


def ms_decode(mid, side):
    return np.stack([mid + side, mid - side], axis=1)


def path_length(lr):
    """Total distance travelled by the beam. When the two channels are aligned
    the trace follows smooth glyph outlines and this is small; when they are
    misaligned X and Y come from unrelated points on the path and the trace
    jitters, inflating the length. Minimum == in focus."""
    d = np.diff(lr, axis=0)
    return np.hypot(d[:, 0], d[:, 1]).sum()


def recover(seg, window=60_000):
    mid, side = seg[:, 0], seg[:, 1]
    scale = 1.0 / np.abs(seg).max()
    usable = min(window, len(side) - MAX_DELAY)

    costs = np.array([
        path_length(ms_decode(mid[:usable], side[d:d + usable]) * scale)
        for d in range(MAX_DELAY)
    ])
    delay = int(costs.argmin())

    aligned = side[delay:]
    lr = ms_decode(mid[:len(aligned)], aligned)
    return delay, lr / np.abs(lr).max(), costs


def plot(lr, path, title):
    fig, ax = plt.subplots(figsize=(9, 5), dpi=140)
    ax.scatter(lr[:, 0], lr[:, 1], s=0.12, c="#12d67a",
               alpha=0.5, linewidths=0, rasterized=True)
    ax.set_facecolor("#03120b")
    ax.set_aspect("equal")
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, color="#12d67a", fontsize=10, family="monospace")
    fig.patch.set_facecolor("#03120b")
    fig.tight_layout()
    fig.savefig(path, facecolor="#03120b")
    plt.close(fig)
    print(f"  -> {path}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "challenge.wav"
    sr, x = load(path)
    print(f"loaded {path}  {len(x)/sr:.2f}s  {x.shape[1]}ch @ {sr}Hz")

    seg = find_payload(x, sr)
    print(f"payload segment: {len(seg)/sr:.2f}s")

    naive = seg / np.abs(seg).max()
    plot(naive, "step1_naive_xy.png", "naive X-Y (raw channels) -- unreadable")

    delay, lr, costs = recover(seg)
    margin = np.median(costs) / costs[delay]
    print(f"recovered inter-channel delay: {delay} samples "
          f"(cost {costs[delay]:.0f}, {margin:.2f}x better than median)")
    plot(lr, "step2_solved_xy.png", f"de-delayed ({delay}) + M/S decoded")


if __name__ == "__main__":
    main()
