#!/usr/bin/env python3
"""
Stress-test the X-Y payload against a dense, loud, wide-stereo pop carrier.

Answers two separate questions:

  Test A (splice) -- payload REPLACES a section of the song.
                     Does the surrounding music break payload recovery?

  Test B (mix)    -- payload is SUMMED with the song underneath it.
                     At what music/payload ratio does the text stop being
                     readable? This is the "can I actually hide it in a song"
                     question, and the answer is the point of the test.

The carrier is synthesised (113 BPM, four-on-the-floor, detuned saw pads,
soft-limited) because what matters is its statistics -- loud, dense,
wide-stereo, heavily compressed -- not which song it is.
"""

import numpy as np
from scipy.io import wavfile

import generate as G
import solve as S

SR = G.SR
BPM = 113.0
OUT = "."


# --------------------------------------------------------- pop carrier

def _env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(attack, 1e-6)) * np.exp(-t / decay)


def _saw(freq, n, phase=0.0):
    t = np.arange(n) / SR
    return 2.0 * ((freq * t + phase) % 1.0) - 1.0


def synth_pop(n_samples, rng):
    """Dense four-on-the-floor pop: kick, snare, hats, bass, wide detuned pad."""
    left = np.zeros(n_samples)
    right = np.zeros(n_samples)
    beat = int(SR * 60.0 / BPM)

    # --- drums -------------------------------------------------------
    for i in range(n_samples // beat + 1):
        pos = i * beat
        if pos >= n_samples:
            break

        # kick: pitch-swept sine
        ln = min(int(0.18 * SR), n_samples - pos)
        t = np.arange(ln) / SR
        kick = np.sin(2 * np.pi * (48 + 90 * np.exp(-t / 0.03)) * t) * _env(ln, 0.001, 0.06)
        left[pos:pos + ln] += kick
        right[pos:pos + ln] += kick

        # snare on 2 and 4
        if i % 2 == 1:
            ln = min(int(0.15 * SR), n_samples - pos)
            noise = rng.normal(0, 1, ln) * _env(ln, 0.001, 0.05)
            left[pos:pos + ln] += noise * 0.7
            right[pos:pos + ln] += noise[::-1] * 0.7      # decorrelated -> wide

        # eighth-note hats
        for half in (0, beat // 2):
            hp = pos + half
            ln = min(int(0.04 * SR), n_samples - hp)
            if ln <= 0:
                continue
            h = rng.normal(0, 1, ln) * _env(ln, 0.0005, 0.012) * 0.25
            left[hp:hp + ln] += h * rng.uniform(0.6, 1.0)
            right[hp:hp + ln] += h * rng.uniform(0.6, 1.0)

    # --- bass + pad --------------------------------------------------
    roots = [55.00, 61.74, 82.41, 73.42]      # A1 B1 E2 D2, one per bar
    bar = beat * 4
    for i in range(n_samples // bar + 1):
        pos, ln = i * bar, min(bar, n_samples - i * bar)
        if ln <= 0:
            break
        f = roots[i % len(roots)]
        env = _env(ln, 0.01, 1.6)

        bass = _saw(f, ln) * env * 0.5
        left[pos:pos + ln] += bass
        right[pos:pos + ln] += bass

        # detuned pad, hard-panned voices -> genuinely wide stereo image
        for mult, det in [(4, 0.4), (5, -0.6), (6, 0.9), (8, -0.3)]:
            voice = _saw(f * mult + det, ln, rng.uniform(0, 1)) * env * 0.16
            pan = rng.uniform(0.2, 0.8)
            left[pos:pos + ln] += voice * pan
            right[pos:pos + ln] += voice * (1 - pan)

    stereo = np.stack([left, right], axis=1) / 3.0
    return np.tanh(stereo * 1.8) * 0.85        # soft limiter -> loud & dense


# ------------------------------------------------------------- payload

def make_payload(seconds):
    contours = G.flag_contours(G.FLAG_LINES)
    frame = G.build_frame(contours, G.FRAME_SAMPLES, G.TRANSIT_SAMPLES)
    n = int(round(seconds * SR / G.FRAME_SAMPLES))
    return np.tile(frame, (n, 1))


def write(name, buf):
    pcm = (buf / np.abs(buf).max() * 0.97 * 32767).astype(np.int16)
    wavfile.write(f"{OUT}/{name}", SR, pcm)


def readability(lr, bins=200):
    """Fraction of the unit square the trace occupies. A clean vector drawing
    touches few cells; a blurred one smears across many. Rough legibility proxy."""
    h, _, _ = np.histogram2d(lr[:, 0], lr[:, 1], bins=bins, range=[[-1, 1], [-1, 1]])
    return np.count_nonzero(h) / h.size


# ---------------------------------------------------------------- main

def main():
    rng = np.random.default_rng(G.SEED)
    payload = make_payload(6.0)
    music_pad = int(4.0 * SR)

    # ---- Test A: splice ---------------------------------------------
    print("=== Test A: payload spliced between music sections ===")
    spliced = np.concatenate([
        synth_pop(music_pad, rng) * 0.9,
        payload * G.DRAW_LEVEL,
        synth_pop(music_pad, rng) * 0.9,
    ], axis=0)
    damaged = G.apply_damage(spliced, G.DELAY)
    write("test_splice.wav", damaged)

    sr, x = S.load(f"{OUT}/test_splice.wav")
    seg = S.find_payload(x, sr)
    d, lr, _ = S.recover(seg)
    print(f"  payload isolated: {len(seg)/sr:.2f}s")
    print(f"  delay recovered : {d}  (true {G.DELAY})  "
          f"{'OK' if d == G.DELAY else 'FAILED'}")
    S.plot(lr, "test_splice_xy.png", f"spliced into music -- delay={d}")

    # ---- Test B: mix -------------------------------------------------
    print("\n=== Test B: payload summed with music underneath ===")
    print(f"  {'music level':>12} | {'occupancy':>9} | verdict")
    print(f"  {'-'*12}-+-{'-'*9}-+--------")

    base = readability(payload / np.abs(payload).max())
    print(f"  {'0.00 (none)':>12} | {base:9.4f} | reference")

    for level in (0.05, 0.10, 0.20, 0.35, 0.60):
        music = synth_pop(len(payload), rng) * level
        mixed = payload * G.DRAW_LEVEL + music
        mixed = mixed / np.abs(mixed).max()

        occ = readability(mixed)
        ratio = occ / base
        verdict = ("clean" if ratio < 2 else
                   "degraded" if ratio < 6 else
                   "unreadable")
        print(f"  {level:12.2f} | {occ:9.4f} | {verdict} ({ratio:.1f}x smear)")

        S.plot(mixed, f"test_mix_{int(level*100):02d}.png",
               f"payload + music @ {level:.2f} -- {verdict}")
        write(f"test_mix_{int(level*100):02d}.wav", mixed)


if __name__ == "__main__":
    main()
