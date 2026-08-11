#!/usr/bin/env python3
"""
Build the song-structured version of the challenge.

Arrangement:  intro -> main -> break -> [PAYLOAD] -> outro

The payload is spliced in, not mixed (Test B in test_music_carrier.py proved
mixing destroys legibility even at inaudible music levels). Short gaps either
side make the splice read as a deliberate glitch and let the solver isolate it.

The whole file then gets the usual damage: Mid/Side + inter-channel delay.
"""

import numpy as np
from scipy.io import wavfile

import generate as G
import solve as S
from test_music_carrier import _env, _saw, synth_pop, BPM

SR = G.SR
BEAT = SR * 60.0 / BPM
BAR = int(round(BEAT * 4))

GAP = int(0.18 * SR)          # silence either side of the payload
PAYLOAD_SECONDS = 6.0
ROOTS = [55.00, 61.74, 82.41, 73.42]     # A1 B1 E2 D2

# (bars, active parts)
ARRANGEMENT = [
    (4,  {"kick", "hat", "bass"}),                            # intro
    (8,  {"kick", "snare", "hat", "bass", "pad"}),            # main
    (4,  {"kick", "snare", "hat", "bass", "pad", "lift"}),    # break / build
]
OUTRO = (6, {"kick", "snare", "hat", "bass", "pad"})


def render(bars_spec, rng, bar_offset=0, fade_out=False):
    """Render a run of bars with the given parts active."""
    n_bars, parts = bars_spec
    n = n_bars * BAR
    left, right = np.zeros(n), np.zeros(n)

    for b in range(n_bars):
        base = b * BAR
        root = ROOTS[(b + bar_offset) % len(ROOTS)]

        for beat_i in range(4):
            pos = base + int(round(beat_i * BEAT))

            if "kick" in parts:
                ln = min(int(0.18 * SR), n - pos)
                t = np.arange(ln) / SR
                k = np.sin(2 * np.pi * (48 + 90 * np.exp(-t / 0.03)) * t) * _env(ln, 0.001, 0.06)
                left[pos:pos + ln] += k
                right[pos:pos + ln] += k

            if "snare" in parts and beat_i % 2 == 1:
                ln = min(int(0.15 * SR), n - pos)
                nz = rng.normal(0, 1, ln) * _env(ln, 0.001, 0.05)
                left[pos:pos + ln] += nz * 0.7
                right[pos:pos + ln] += nz[::-1] * 0.7

            if "hat" in parts:
                for half in (0, int(BEAT // 2)):
                    hp = pos + half
                    ln = min(int(0.04 * SR), n - hp)
                    if ln <= 0:
                        continue
                    h = rng.normal(0, 1, ln) * _env(ln, 0.0005, 0.012) * 0.25
                    left[hp:hp + ln] += h * rng.uniform(0.6, 1.0)
                    right[hp:hp + ln] += h * rng.uniform(0.6, 1.0)

        ln = min(BAR, n - base)
        env = _env(ln, 0.01, 1.6)

        if "bass" in parts:
            bs = _saw(root, ln) * env * 0.5
            left[base:base + ln] += bs
            right[base:base + ln] += bs

        if "pad" in parts:
            for mult, det in [(4, 0.4), (5, -0.6), (6, 0.9), (8, -0.3)]:
                v = _saw(root * mult + det, ln, rng.uniform(0, 1)) * env * 0.16
                pan = rng.uniform(0.2, 0.8)
                left[base:base + ln] += v * pan
                right[base:base + ln] += v * (1 - pan)

        if "lift" in parts:                     # octave sparkle on the build
            v = _saw(root * 12 + 1.1, ln, rng.uniform(0, 1)) * env * 0.10
            left[base:base + ln] += v * 0.7
            right[base:base + ln] += v * 0.3

    stereo = np.stack([left, right], axis=1) / 3.0
    stereo = np.tanh(stereo * 1.8) * 0.85

    if fade_out:
        stereo *= np.linspace(1.0, 0.0, n)[:, None] ** 1.5
    return stereo


def main():
    rng = np.random.default_rng(G.SEED)

    music, bar_cursor = [], 0
    for spec in ARRANGEMENT:
        music.append(render(spec, rng, bar_offset=bar_cursor))
        bar_cursor += spec[0]
    song_head = np.concatenate(music, axis=0)
    outro = render(OUTRO, rng, bar_offset=bar_cursor, fade_out=True)

    contours = G.flag_contours(G.FLAG_LINES)
    frame = G.build_frame(contours, G.FRAME_SAMPLES, G.TRANSIT_SAMPLES)
    n_frames = int(round(PAYLOAD_SECONDS * SR / G.FRAME_SAMPLES))
    payload = np.tile(frame, (n_frames, 1)) * G.DRAW_LEVEL

    gap = np.zeros((GAP, 2))
    clean = np.concatenate([song_head, gap, payload, gap, outro], axis=0)
    damaged = G.apply_damage(clean, G.DELAY)

    for name, buf in [("musical_reference_clean.wav", clean),
                      ("musical_challenge.wav", damaged)]:
        pcm = (buf / np.abs(buf).max() * 0.97 * 32767).astype(np.int16)
        wavfile.write(name, SR, pcm)
        print(f"wrote {name}  {len(buf)/SR:.2f}s")

    t0 = len(song_head) + GAP
    print(f"payload sits at {t0/SR:.2f}s .. {(t0+len(payload))/SR:.2f}s")

    # verify end to end
    sr, x = S.load("musical_challenge.wav")
    seg = S.find_payload(x, sr)
    d, lr, _ = S.recover(seg)
    print(f"solver: isolated {len(seg)/sr:.2f}s, delay={d} "
          f"(true {G.DELAY}) {'OK' if d == G.DELAY else 'FAILED'}")
    S.plot(lr, "musical_solved_xy.png", f"musical version -- delay={d}")


if __name__ == "__main__":
    main()
