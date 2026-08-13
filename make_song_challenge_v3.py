#!/usr/bin/env python3
"""
Build the v3 song-carrier challenge.

v3 exists because v2 failed for a reason that has nothing to do with difficulty.

v2 shrank the payload to 0.54 s and crossfaded it into the music, on the theory
that a smaller, seamless insert would be harder to find. Two independent
high-effort analyses (78k tokens / 1 hour, and 5 parallel workers / 57 minutes)
both located it immediately, both described it as a "buffer underrun", and both
concluded the FILE WAS BROKEN rather than that the challenge was hard. One
suggested the generator's embedding step had silently failed.

That is the worst outcome a challenge can have: when solvers cannot tell "hard"
from "broken", they stop and open a ticket. Measurement also showed the
concealment bought nothing -- v2 was solved FASTER than v1 (17.5 min vs 44.4).

So v3 reverts both concealment changes and keeps everything that measured
useful:

  reverted  payload back to ~4 s, and clean silence either side, so the insert
            is unmistakably deliberate
  kept      prime frame period 2971
  kept      arbitrary affine (31 deg + unequal gains) instead of Mid/Side
  kept      balanced line break "THJCC{" / "drakos}", which fixes a real bug:
            v1's top line spanned only 63% of the width and could be silently
            cropped, handing the solver a flag with no prefix and no feedback
"""

import subprocess

import numpy as np
from scipy.io import wavfile

import generate_v2 as G
import solve_v2 as S
from widen_song import widen, measure

SOURCE_MP3 = "/Users/mazon/Downloads/all_nigh_long.mp3"
SONG = "_song_v3.wav"

SPLICE_AT = 4.50       # seconds into the song
GAP = 0.15             # clean silence either side -- the "on purpose" cue
WIDTH = 0.30           # stereo widening (see widen_song.py)


def main():
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SOURCE_MP3,
                    "-c:a", "pcm_s16le", "-ar", str(G.SR), SONG], check=True)

    sr, raw = S.load(SONG)
    song = widen(raw, WIDTH)
    b, a = measure(raw), measure(song)
    print(f"song  : {len(song)/sr:.2f}s @ {sr}Hz")
    print(f"widen : L/R corr {b['corr']:.4f} -> {a['corr']:.4f}")

    payload, n_contours = G.make_payload()
    at = int(SPLICE_AT * sr)
    gap = np.zeros((int(GAP * sr), 2))

    clean = np.concatenate([song[:at], gap, payload, gap, song[at:]], axis=0)
    damaged = G.apply_damage(clean, G.DELAY)

    for name, buf in [("v3_reference_clean.wav", clean),
                      ("v3_song_challenge.wav", damaged)]:
        pcm = (buf / np.abs(buf).max() * 0.97 * 32767).astype(np.int16)
        wavfile.write(name, sr, pcm)
        print(f"wrote {name}  {len(buf)/sr:.2f}s")

    t0 = (at + len(gap)) / sr
    print(f"payload at {t0:.3f}s .. {t0 + len(payload)/sr:.3f}s "
          f"({len(payload)/sr:.3f}s, {G.N_FRAMES} frames, {GAP*1000:.0f}ms gaps)")


if __name__ == "__main__":
    main()
