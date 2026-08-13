#!/usr/bin/env python3
"""
Oscilloscope-music CTF challenge -- v2, hardened.

Same core idea as v1 (left channel = X, right = Y, so an X-Y scatter draws the
flag) but every giveaway the v1 red teams exploited has been closed:

  v1                          v2                    why
  --------------------------  --------------------  ---------------------------
  period 3000                 period 2971 (prime)   3000 screams "hand-made",
                                                    which killed the modem/FSK
                                                    branch for free
  88 identical frames         60 frames             REVERTED in v3. Shrinking
                                                    the payload to 0.5s made it
                                                    read as a buffer underrun:
                                                    two independent analyses
                                                    concluded the file was
                                                    BROKEN rather than hard.
  silence gap either side     silence gap           REVERTED in v3, same reason.
                                                    Crossfading removed the last
                                                    cue that the segment was put
                                                    there on purpose.
  Mid/Side (a known 45 deg)   arbitrary rotation    "try mid/side" is a stereo
                              + per-axis gains      cliche; an arbitrary affine
                                                    has to be solved for
  lines "THJCC" / "{drakos}"  "THJCC{" / "drakos}"  5+8 chars left the top line
                                                    spanning only 63% of the
                                                    width, risking a crop that
                                                    silently drops the prefix

Deliberately NOT changed, both measured unsound:
  * per-channel absolute offsets -- a no-op. The payload is periodic, so only
    the RELATIVE offset is observable; shifting both channels just re-phases
    the frame. Verified: the two X-Y point clouds differ by exactly 0.0.
  * payload at -40 dBFS under the music -- unrecoverable. Test B in
    test_music_carrier.py already showed music at 0.20 destroys legibility, and
    the solver has no way to cancel the music: L-R yields ONE signal, while the
    drawing needs two independent coordinates.
"""

import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from scipy.io import wavfile

# ---------------------------------------------------------------- config

FLAG_LINES = ["THJCC{", "δράκος}"]     # 6 + 7 chars -> balanced widths

SR = 44_100
FRAME_SAMPLES = 2971       # prime: no longer legibly hand-picked
N_FRAMES = 60              # ~4.0 s -- unmistakably deliberate, not a glitch
TRANSIT_SAMPLES = 6

# The mixing affine. v1 used Mid/Side, i.e. rotation by exactly 45 degrees with
# equal gains -- guessable in one try. An arbitrary angle with unequal per-axis
# gains has to be recovered from the data.
MIX_ANGLE_DEG = 31.0
MIX_GAIN = (1.00, 0.62)

DELAY = 1129               # relative inter-channel delay, in samples
DRAW_LEVEL = 0.85

SEED = 20260813


# ---------------------------------------------------- text -> XY contours

def flag_contours(lines):
    """Glyph outlines, normalised into a centred [-1, 1] box (aspect preserved)."""
    fp = FontProperties(family="DejaVu Sans", weight="bold")
    contours, y_cursor = [], 0.0

    for line in reversed(lines):               # bottom-up so y grows upward
        tp = TextPath((0, y_cursor), line, size=1.0, prop=fp)
        for poly in tp.to_polygons():
            if len(poly) >= 3:
                contours.append(np.asarray(poly, dtype=np.float64))
        y_cursor += 1.35

    allpts = np.concatenate(contours, axis=0)
    lo, hi = allpts.min(axis=0), allpts.max(axis=0)
    centre = (lo + hi) / 2.0
    scale = 0.95 / max((hi - lo) / 2.0)
    return [(c - centre) * scale for c in contours]


def resample_closed(pts, n):
    closed = np.vstack([pts, pts[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    if cum[-1] <= 0 or n < 2:
        return np.repeat(closed[:1], max(n, 1), axis=0)
    t = np.linspace(0.0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(t, cum, closed[:, 0]),
                     np.interp(t, cum, closed[:, 1])], axis=1)


def build_frame(contours, frame_samples, transit):
    perims = np.array([np.hypot(*np.diff(np.vstack([c, c[:1]]), axis=0).T).sum()
                       for c in contours])
    budget = frame_samples - transit * len(contours)
    if budget < len(contours) * 4:
        raise ValueError("FRAME_SAMPLES too small for this many contours")

    counts = np.maximum(4, np.round(budget * perims / perims.sum()).astype(int))
    drift = budget - counts.sum()
    order = np.argsort(-perims)
    for i in range(abs(drift)):
        counts[order[i % len(order)]] += 1 if drift > 0 else -1

    pieces, pen = [], None
    for contour, n in zip(contours, counts):
        traced = resample_closed(contour, n)
        if pen is not None:
            a = np.linspace(0, 1, transit, endpoint=False)[:, None]
            pieces.append(pen * (1 - a) + traced[:1] * a)
        else:
            pieces.append(np.repeat(traced[:1], transit, axis=0))
        pieces.append(traced)
        pen = traced[-1:]

    frame = np.concatenate(pieces, axis=0)
    assert len(frame) == frame_samples, (len(frame), frame_samples)
    return frame


# -------------------------------------------------------------- damage

def mix_matrix(angle_deg=MIX_ANGLE_DEG, gain=MIX_GAIN):
    a = np.deg2rad(angle_deg)
    rot = np.array([[np.cos(a), -np.sin(a)],
                    [np.sin(a),  np.cos(a)]])
    return np.diag(gain) @ rot


def apply_damage(xy, delay, angle_deg=MIX_ANGLE_DEG, gain=MIX_GAIN):
    """Linear mix of the two coordinates, then delay channel 1 relative to 0."""
    mixed = xy @ mix_matrix(angle_deg, gain).T
    ch0, ch1 = mixed[:, 0], mixed[:, 1]
    ch1 = np.concatenate([np.zeros(delay), ch1])[:len(ch1)]
    return np.stack([ch0, ch1], axis=1)


# ---------------------------------------------------------------- main

def make_payload():
    contours = flag_contours(FLAG_LINES)
    frame = build_frame(contours, FRAME_SAMPLES, TRANSIT_SAMPLES)
    return np.tile(frame, (N_FRAMES, 1)) * DRAW_LEVEL, len(contours)


def main():
    payload, n_contours = make_payload()
    dur = len(payload) / SR

    clean = payload
    damaged = apply_damage(clean, DELAY)

    for name, buf in [("v2_reference_clean.wav", clean),
                      ("v2_payload_only.wav", damaged)]:
        pcm = (buf / np.abs(buf).max() * 0.97 * 32767).astype(np.int16)
        wavfile.write(name, SR, pcm)

    M = mix_matrix()
    print(f"contours   : {n_contours}")
    print(f"frame      : {FRAME_SAMPLES} samples  ({SR/FRAME_SAMPLES:.2f} fps)")
    print(f"frames     : {N_FRAMES}  -> payload {dur:.3f}s ({len(payload)} samples)")
    print(f"delay      : {DELAY}")
    print(f"mix angle  : {MIX_ANGLE_DEG} deg   gains {MIX_GAIN}")
    print(f"mix matrix : [[{M[0,0]:+.4f} {M[0,1]:+.4f}] [{M[1,0]:+.4f} {M[1,1]:+.4f}]]")
    print(f"cond       : {np.linalg.cond(M):.3f}")


if __name__ == "__main__":
    main()
