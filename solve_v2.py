#!/usr/bin/env python3
"""
Reference solution for the v2 challenge.

Unlike v1 this cannot assume Mid/Side -- the mixing is an arbitrary rotation
with unequal per-axis gains, so the affine has to be recovered from the data.

Pipeline:
  1. frame period      -- unbiased autocorrelation
  2. inter-channel delay -- minimise the traced path length
  3. the affine        -- the beam was resampled at CONSTANT ARC LENGTH, so in
                          the original coordinates every velocity vector has
                          the same magnitude: the velocity cloud is a CIRCLE.
                          An affine maps that circle to an ellipse, so whitening
                          the velocity covariance undoes the affine up to an
                          unknown rotation.
  4. residual rotation -- text is full of horizontal and vertical strokes, so
                          pick the angle whose stroke-direction histogram is
                          most concentrated on the axes (maximise <cos 4th>).
"""

import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.io import wavfile


def load(path):
    sr, data = wavfile.read(path)
    x = data.astype(np.float64)
    if np.issubdtype(data.dtype, np.integer):
        x /= np.iinfo(data.dtype).max
    return sr, x


def find_payload(x, win=6000, hop=250, lo=1200, hi=4500, margin=1.25):
    """Locate the payload before measuring anything else.

    v2 gives no silence boundaries and only ~0.5 s of payload inside a full
    song, so a whole-file autocorrelation is dominated by the music. Instead
    slide a window and score each position by how self-similar it is at a LONG
    lag: the payload retraces an identical frame, music never does."""
    m = x.mean(axis=1)
    starts = np.arange(0, max(1, len(m) - win), hop)

    scores = []
    for s in starts:
        b = m[s:s + win]
        b = b - b.mean()
        if np.abs(b).max() < 1e-6:
            scores.append(0.0)
            continue
        spec = np.fft.rfft(b, 2 * win)
        ac = np.fft.irfft(spec * np.conj(spec))[:hi + 1]
        lags = np.arange(len(ac))
        ac = ac / np.maximum(win - lags, 1)      # unbiased
        ac /= ac[0] + 1e-12
        scores.append(float(ac[lo:hi].max()))

    scores = np.array(scores)
    thresh = max(margin * np.median(scores), 0.5)
    hot = np.flatnonzero(scores > thresh)
    if len(hot) == 0:
        return x, None

    runs = np.split(hot, np.flatnonzero(np.diff(hot) > 2) + 1)
    run = max(runs, key=len)
    a = int(starts[run[0]])
    b = int(min(len(x), starts[run[-1]] + win))
    return x[a:b], (a, b)


def find_period(x, lo=800, hi=6000):
    """Unbiased autocorrelation: divide by the overlap length, not the block."""
    m = x.mean(axis=1)
    m = m - m.mean()
    n = len(m)
    spec = np.fft.rfft(m, 2 * n)
    ac = np.fft.irfft(spec * np.conj(spec))[:hi + 1]
    lags = np.arange(len(ac))
    ac = ac / np.maximum(n - lags, 1)
    ac /= ac[0] + 1e-12
    return int(lo + np.argmax(ac[lo:hi])), ac


def path_length(xy):
    d = np.diff(xy, axis=0)
    return np.hypot(d[:, 0], d[:, 1]).sum()


def find_delay(x, period):
    """Correct alignment traces smooth outlines; wrong alignment jitters."""
    a, b = x[:, 0], x[:, 1]
    usable = len(b) - period - 1
    costs = np.array([path_length(np.stack([a[:usable], b[d:d + usable]], axis=1))
                      for d in range(period)])
    return int(costs.argmin()), costs


def whiten(xy):
    """Map the velocity ellipse back to a circle -> undoes the affine up to
    an unknown rotation."""
    v = np.diff(xy, axis=0)
    keep = np.hypot(v[:, 0], v[:, 1]) > 1e-9
    C = np.cov(v[keep].T)
    evals, evecs = np.linalg.eigh(C)
    W = evecs @ np.diag(1.0 / np.sqrt(np.maximum(evals, 1e-18))) @ evecs.T
    return xy @ W.T, W


def axis_score(xy, theta):
    """High when stroke directions cluster on the axes."""
    c, s = np.cos(theta), np.sin(theta)
    rot = np.array([[c, -s], [s, c]])
    v = np.diff(xy @ rot.T, axis=0)
    mag = np.hypot(v[:, 0], v[:, 1])
    keep = mag > np.percentile(mag, 40)
    ang = np.arctan2(v[keep, 1], v[keep, 0])
    return np.cos(4 * ang).mean()


def upright(xy):
    """Axis-align the strokes, then resolve the resulting 90-degree ambiguity.

    cos(4*theta) has period 90 degrees, so it cannot tell upright text from text
    lying on its side. Lines of text run horizontally, so the correct quarter
    turn is simply the one whose bounding box is wider than it is tall."""
    thetas = np.linspace(0, np.pi / 2, 900, endpoint=False)
    scores = np.array([axis_score(xy, t) for t in thetas])
    t = thetas[scores.argmax()]

    c, s = np.cos(t), np.sin(t)
    out = xy @ np.array([[c, -s], [s, c]]).T

    # Aspect ratio is useless here: two lines turned on their side become two
    # side-by-side columns, still wider than tall. What actually distinguishes
    # the axes is the blank gutter BETWEEN the lines -- projecting onto the
    # stacking axis is bimodal, projecting along the lines is not.
    if _gutter(out[:, 0]) > _gutter(out[:, 1]):
        out = out @ np.array([[0.0, -1.0], [1.0, 0.0]]).T
        t += np.pi / 2
    return out, np.rad2deg(t)


def _gutter(vals, bins=60):
    """Depth of the emptiest valley in the central part of the projection."""
    h, _ = np.histogram(vals, bins=bins)
    h = h / max(h.max(), 1)
    lo, hi = int(0.2 * bins), int(0.8 * bins)
    return 1.0 - h[lo:hi].min()


def plot(xy, path, title):
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    ax.plot(xy[:, 0], xy[:, 1], lw=0.5, color="#12d67a")
    ax.set_facecolor("#03120b")
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, color="#12d67a", fontsize=10, family="monospace")
    fig.patch.set_facecolor("#03120b")
    fig.tight_layout()
    fig.savefig(path, facecolor="#03120b")
    plt.close(fig)
    print(f"  -> {path}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "v2_payload_only.wav"
    sr, full = load(path)
    print(f"loaded {path}  {len(full)/sr:.3f}s  {full.shape[1]}ch @ {sr}Hz")

    x, span = find_payload(full)
    if span:
        print(f"payload      : {span[0]/sr:.3f}s .. {span[1]/sr:.3f}s "
              f"({len(x)/sr:.3f}s)")

    period, _ = find_period(x)
    print(f"frame period : {period} samples  ({sr/period:.2f} fps)")

    # The located span overshoots into the music and its edges are crossfaded.
    # Trim a whole frame off each end so the delay search sees only clean loop.
    if len(x) > 3 * period:
        x = x[period:len(x) - period]
        print(f"trimmed to   : {len(x)} samples ({len(x)/period:.1f} frames)")

    delay, costs = find_delay(x, period)
    print(f"delay        : {delay}  "
          f"(cost {costs[delay]:.0f} vs median {np.median(costs):.0f})")

    aligned = np.stack([x[:len(x) - delay, 0], x[delay:, 1]], axis=1)
    plot(aligned / np.abs(aligned).max(), "v2_step1_aligned.png",
         f"de-delayed ({delay}) -- still affine-mixed")

    w, _ = whiten(aligned)
    plot(w / np.abs(w).max(), "v2_step2_whitened.png",
         "velocity-whitened -- affine undone up to rotation")

    final, ang = upright(w)
    print(f"residual rot : {ang:.2f} deg")
    final = final / np.abs(final).max()
    for flip, tag in [((1, 1), "a"), ((1, -1), "b"), ((-1, 1), "c"), ((-1, -1), "d")]:
        plot(final * np.array(flip), f"v2_step3_{tag}.png",
             f"upright (rot {ang:.1f} deg) flip={flip}")


if __name__ == "__main__":
    main()
