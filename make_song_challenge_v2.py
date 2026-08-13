#!/usr/bin/env python3
"""
Build the v2 song-carrier challenge.

Differences from v1's splice:
  * no silence gaps -- the payload is CROSSFADED into the music, so segment
    boundaries have to be inferred rather than read off a waveform view
  * 0.54 s of payload instead of 6 s, so it is no longer an unmissable block
    of broadband noise on a spectrogram
  * the whole file carries the v2 affine (arbitrary rotation + per-axis gains)
    rather than Mid/Side
"""

import subprocess

import numpy as np
from scipy.io import wavfile

import generate_v2 as G2
import solve_v2 as S2
from widen_song import widen, measure

SOURCE_MP3 = "/Users/mazon/Downloads/all_nigh_long.mp3"
SONG = "_song_v2.wav"

SPLICE_AT = 5.60          # seconds into the song
XFADE = 0.010             # 10 ms -- short enough to spare whole frames
WIDTH = 0.30              # stereo widening, as measured in widen_song.py


def crossfade_in(bed, payload, at, n_x):
    """Drop payload into bed at sample `at`, crossfading both edges."""
    out = bed.copy()
    n = len(payload)
    seg = payload.copy()

    ramp = np.linspace(0, 1, n_x)[:, None]
    seg[:n_x] = seg[:n_x] * ramp + out[at:at + n_x] * (1 - ramp)
    seg[-n_x:] = seg[-n_x:] * (1 - ramp) + out[at + n - n_x:at + n] * ramp

    out[at:at + n] = seg
    return out


def main():
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SOURCE_MP3,
                    "-c:a", "pcm_s16le", "-ar", str(G2.SR), SONG], check=True)

    sr, raw = S2.load(SONG)
    song = widen(raw, WIDTH)
    b, a = measure(raw), measure(song)
    print(f"song  : {len(song)/sr:.2f}s @ {sr}Hz")
    print(f"widen : L/R corr {b['corr']:.4f} -> {a['corr']:.4f}")

    payload, n_contours = G2.make_payload()
    at = int(SPLICE_AT * sr)
    n_x = int(XFADE * sr)

    clean = crossfade_in(song, payload, at, n_x)
    damaged = G2.apply_damage(clean, G2.DELAY)

    for name, buf in [("v2_song_reference_clean.wav", clean),
                      ("v2_song_challenge.wav", damaged)]:
        pcm = (buf / np.abs(buf).max() * 0.97 * 32767).astype(np.int16)
        wavfile.write(name, sr, pcm)
        print(f"wrote {name}  {len(buf)/sr:.2f}s")

    print(f"payload at {at/sr:.3f}s .. {(at+len(payload))/sr:.3f}s "
          f"({len(payload)/sr:.3f}s, {G2.N_FRAMES} frames, "
          f"crossfade {XFADE*1000:.0f}ms)")


if __name__ == "__main__":
    main()
