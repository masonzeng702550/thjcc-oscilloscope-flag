#!/usr/bin/env python3
"""
Oscilloscope-music CTF challenge generator.

Encodes a flag as an X-Y (Lissajous) vector drawing: left channel drives X,
right channel drives Y. Plotting L against R as a scatter reveals the text.

Two layers of deliberate damage are then applied so the naive plot is garbage:
  1. Mid/Side encoding   -- ch0 = (L+R)/2, ch1 = (L-R)/2
  2. Inter-channel delay -- ch1 is shifted forward by DELAY samples

Solving requires undoing them in reverse order: de-delay, then M/S decode.
"""

import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from scipy.io import wavfile

# ---------------------------------------------------------------- config

FLAG_LINES = ["THJCC", "{δράκος}"]

SR = 48_000          # sample rate
FRAME_SAMPLES = 3000 # samples per drawing refresh -> 16 fps
DRAW_SECONDS = 6.0   # length of the payload segment
CARRIER_SECONDS = 2.0
TRANSIT_SAMPLES = 6  # blanking-ish jump between contours

DELAY = 1129         # inter-channel delay, in samples
DRAW_LEVEL = 0.85
CARRIER_LEVEL = 0.12

OUT_DIR = "."
SEED = 20260811


# ---------------------------------------------------- text -> XY contours

def flag_contours(lines):
    """Return list of (N,2) float arrays, normalised into a centred [-1,1] box."""
    fp = FontProperties(family="DejaVu Sans", weight="bold")
    contours, y_cursor = [], 0.0

    for line in reversed(lines):          # build bottom-up so y grows upward
        tp = TextPath((0, y_cursor), line, size=1.0, prop=fp)
        for poly in tp.to_polygons():
            if len(poly) >= 3:
                contours.append(np.asarray(poly, dtype=np.float64))
        y_cursor += 1.35                  # line advance

    allpts = np.concatenate(contours, axis=0)
    lo, hi = allpts.min(axis=0), allpts.max(axis=0)
    centre = (lo + hi) / 2.0
    scale = 0.95 / max((hi - lo) / 2.0)   # uniform -> preserves aspect ratio

    return [(c - centre) * scale for c in contours]


def resample_closed(pts, n):
    """Resample a contour to n points at constant arc-length spacing."""
    closed = np.vstack([pts, pts[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    if cum[-1] <= 0 or n < 2:
        return np.repeat(closed[:1], max(n, 1), axis=0)
    t = np.linspace(0.0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(t, cum, closed[:, 0]),
                     np.interp(t, cum, closed[:, 1])], axis=1)


def build_frame(contours, frame_samples, transit):
    """One full refresh of the beam: every contour traced once, plus transits."""
    perims = np.array([np.hypot(*np.diff(np.vstack([c, c[:1]]), axis=0).T).sum()
                       for c in contours])
    budget = frame_samples - transit * len(contours)
    if budget < len(contours) * 4:
        raise ValueError("FRAME_SAMPLES too small for this many contours")

    counts = np.maximum(4, np.round(budget * perims / perims.sum()).astype(int))

    # nudge counts so the frame lands on exactly frame_samples
    drift = budget - counts.sum()
    order = np.argsort(-perims)
    for i in range(abs(drift)):
        counts[order[i % len(order)]] += 1 if drift > 0 else -1

    pieces, pen = [], None
    for contour, n in zip(contours, counts):
        traced = resample_closed(contour, n)
        if pen is not None:                       # fast jump from previous pen-up
            a = np.linspace(0, 1, transit, endpoint=False)[:, None]
            pieces.append(pen * (1 - a) + traced[:1] * a)
        else:
            pieces.append(np.repeat(traced[:1], transit, axis=0))
        pieces.append(traced)
        pen = traced[-1:]

    frame = np.concatenate(pieces, axis=0)
    assert len(frame) == frame_samples, (len(frame), frame_samples)
    return frame


# ------------------------------------------------------------- carrier

def carrier(n, rng):
    """A quiet, near-mono ambient pad. In X-Y it collapses to a diagonal smear,
    which stays visually distinct from the payload text."""
    t = np.arange(n) / SR
    env = np.minimum(1.0, np.minimum(t, (n / SR) - t) / 0.4).clip(0, 1)
    sig = np.zeros(n)
    for f, a in [(110.0, 1.0), (164.81, 0.6), (220.0, 0.45), (329.63, 0.25)]:
        drift = 1.0 + 0.0015 * np.sin(2 * np.pi * (0.07 + 0.03 * a) * t)
        sig += a * np.sin(2 * np.pi * f * drift * t + rng.uniform(0, 2 * np.pi))
    sig *= env / 2.3
    width = 0.02 * np.sin(2 * np.pi * 0.11 * t)
    return np.stack([sig * (1 - width), sig * (1 + width)], axis=1)


# -------------------------------------------------------------- damage

def apply_damage(lr, delay):
    """L/R -> Mid/Side, then delay the side channel by `delay` samples."""
    mid = (lr[:, 0] + lr[:, 1]) / 2.0
    side = (lr[:, 0] - lr[:, 1]) / 2.0
    side_delayed = np.concatenate([np.zeros(delay), side])[:len(side)]
    return np.stack([mid, side_delayed], axis=1)


# ---------------------------------------------------------------- main

def main():
    rng = np.random.default_rng(SEED)

    contours = flag_contours(FLAG_LINES)
    frame = build_frame(contours, FRAME_SAMPLES, TRANSIT_SAMPLES)
    n_frames = int(round(DRAW_SECONDS * SR / FRAME_SAMPLES))
    payload = np.tile(frame, (n_frames, 1)) * DRAW_LEVEL

    pad = int(CARRIER_SECONDS * SR)
    clean = np.concatenate([
        carrier(pad, rng) * CARRIER_LEVEL,
        payload,
        carrier(pad, rng) * CARRIER_LEVEL,
    ], axis=0)

    damaged = apply_damage(clean, DELAY)

    for name, buf in [("reference_clean.wav", clean), ("challenge.wav", damaged)]:
        peak = np.abs(buf).max()
        pcm = (buf / peak * 0.97 * 32767).astype(np.int16)
        wavfile.write(f"{OUT_DIR}/{name}", SR, pcm)
        print(f"wrote {name}  {len(buf)/SR:.2f}s  peak={peak:.3f}")

    print(f"contours={len(contours)} frames={n_frames} delay={DELAY}")


if __name__ == "__main__":
    main()
