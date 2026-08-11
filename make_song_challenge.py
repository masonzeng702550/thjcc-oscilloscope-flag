#!/usr/bin/env python3
"""
Splice the X-Y payload into the organiser-supplied sample song.

Runs at the song's native 44.1kHz (no resampling of the source), so the frame
rate becomes 44100/3000 = 14.7 fps instead of 16.

Reports the side-channel contrast between song and payload, because that
number decides how obvious the payload's location is after Mid/Side encoding.
"""

import subprocess

import numpy as np
from scipy.io import wavfile

import generate as G
import solve as S
from widen_song import widen, measure

SOURCE_MP3 = "/Users/mazon/Downloads/all_nigh_long.mp3"
SONG = "_song.wav"
GAP = 0.18                 # seconds of silence either side of the splice
PAYLOAD_SECONDS = 6.0
SPLICE_AT = 4.75           # seconds into the song

# Stereo width applied to the source before splicing. The source is near-mono
# (L/R corr 0.9998), which would leave the payload standing alone in the side
# channel and give its position away. 0.30 pulls that contrast from 114x down
# to 4.6x while keeping L/R corr at 0.84 -- an ordinary commercial width.
WIDTH = 0.30


def main():
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SOURCE_MP3,
                    "-c:a", "pcm_s16le", "-ar", "44100", SONG], check=True)

    sr, raw = S.load(SONG)
    print(f"song: {len(raw)/sr:.2f}s @ {sr}Hz")

    song = widen(raw, WIDTH)
    b, a = measure(raw), measure(song)
    print(f"widen({WIDTH}): L/R corr {b['corr']:.4f} -> {a['corr']:.4f}, "
          f"side RMS {b['side_rms']:.5f} -> {a['side_rms']:.5f}")

    contours = G.flag_contours(G.FLAG_LINES)
    frame = G.build_frame(contours, G.FRAME_SAMPLES, G.TRANSIT_SAMPLES)
    n_frames = int(round(PAYLOAD_SECONDS * sr / G.FRAME_SAMPLES))
    payload = np.tile(frame, (n_frames, 1)) * G.DRAW_LEVEL
    print(f"payload: {len(payload)/sr:.2f}s, "
          f"{sr/G.FRAME_SAMPLES:.1f} fps, {n_frames} frames")

    cut = int(SPLICE_AT * sr)
    gap = np.zeros((int(GAP * sr), 2))
    clean = np.concatenate([song[:cut], gap, payload, gap, song[cut:]], axis=0)
    damaged = G.apply_damage(clean, G.DELAY)

    for name, buf in [("song_reference_clean.wav", clean),
                      ("song_challenge.wav", damaged)]:
        pcm = (buf / np.abs(buf).max() * 0.97 * 32767).astype(np.int16)
        wavfile.write(name, sr, pcm)
        print(f"wrote {name}  {len(buf)/sr:.2f}s")

    t0 = (cut + len(gap)) / sr
    print(f"payload sits at {t0:.2f}s .. {t0 + len(payload)/sr:.2f}s")

    # --- how loudly does the payload announce itself in the side channel? ---
    def side_rms(a):
        return float(np.sqrt((((a[:, 0] - a[:, 1]) / 2) ** 2).mean()))

    s_song = side_rms(song)
    s_payload = side_rms(payload)
    print(f"\nside-channel RMS -- song {s_song:.5f} | payload {s_payload:.5f}"
          f"  ({s_payload / max(s_song, 1e-9):.0f}x)")

    # --- verify end to end ---
    sr2, x = S.load("song_challenge.wav")
    seg = S.find_payload(x, sr2)
    d, lr, _ = S.recover(seg)
    print(f"solver: isolated {len(seg)/sr2:.2f}s, delay={d} (true {G.DELAY}) "
          f"{'OK' if d == G.DELAY else 'FAILED'}")
    S.plot(lr, "song_solved_xy.png", f"sample song version -- delay={d}")


if __name__ == "__main__":
    main()
