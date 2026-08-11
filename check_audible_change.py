#!/usr/bin/env python3
"""
Quantify how much the song actually changes, at each stage of processing.

Three things could alter it:
  A. all-pass stereo widening (width 0.30)
  B. Mid/Side encoding      -- applied to the WHOLE file, song included
  C. inter-channel delay    -- likewise

Exports listenable renders of each stage so the change can be judged by ear,
not just by number.
"""

import numpy as np
from scipy.io import wavfile

import generate as G
import solve as S
from widen_song import widen
from make_song_challenge import WIDTH, SPLICE_AT


def band_spectrum(x, sr, n_fft=8192):
    """Average magnitude spectrum in dB, octave-ish bands."""
    step = n_fft // 2
    frames = [x[i:i + n_fft] * np.hanning(n_fft)
              for i in range(0, len(x) - n_fft, step)]
    if not frames:
        return None, None
    mag = np.mean([np.abs(np.fft.rfft(f)) for f in frames], axis=0)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    edges = [20, 60, 150, 400, 1000, 2500, 6000, 12000, 20000]
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (freqs >= lo) & (freqs < hi)
        out.append(20 * np.log10(mag[m].mean() + 1e-12))
    return np.array(out), [f"{lo}-{hi}" for lo, hi in zip(edges[:-1], edges[1:])]


def rms_db(x):
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)


def main():
    sr, orig = S.load("_song.wav")
    wide = widen(orig, WIDTH)

    # what a media player actually outputs for the challenge file's song part
    sr2, chal = S.load("song_challenge.wav")
    n = int(SPLICE_AT * sr)
    played = chal[:n]

    print(f"source: {len(orig)/sr:.2f}s @ {sr}Hz\n")

    # ---- A. does widening change the timbre? -------------------------
    print("A. all-pass widening (width %.2f)" % WIDTH)
    mono_o = orig.mean(axis=1)
    mono_w = wide.mean(axis=1)
    scale = np.sqrt((mono_o ** 2).mean()) / np.sqrt((mono_w ** 2).mean())
    resid = mono_o - mono_w * scale
    print(f"   mono sum (L+R) difference : {rms_db(resid) - rms_db(mono_o):+6.1f} dB "
          f"-> {'identical' if rms_db(resid)-rms_db(mono_o) < -60 else 'AUDIBLE'}")

    so, labels = band_spectrum(mono_o, sr)
    sw, _ = band_spectrum(mono_w * scale, sr)
    print(f"   magnitude spectrum, per band (dB difference):")
    for lab, d in zip(labels, sw - so):
        print(f"      {lab:>10} Hz : {d:+5.2f}")
    print(f"   max band deviation        : {np.abs(sw-so).max():.2f} dB")

    # ---- B+C. what the listener hears from the challenge file ---------
    print("\nB+C. Mid/Side + delay, as heard from song_challenge.wav")
    ref = orig[:len(played)]
    for ch, name in [(0, "left "), (1, "right")]:
        c = np.corrcoef(ref[:, ch], played[:, ch])[0, 1]
        print(f"   {name} channel vs original : corr {c:+.4f}")
    print(f"   original L/R corr          : {np.corrcoef(ref[:,0], ref[:,1])[0,1]:+.4f}")
    print(f"   as-played L/R corr         : {np.corrcoef(played[:,0], played[:,1])[0,1]:+.4f}")
    print(f"   as-played channel RMS      : L {rms_db(played[:,0]):.1f} dB  "
          f"R {rms_db(played[:,1]):.1f} dB  "
          f"(imbalance {abs(rms_db(played[:,0])-rms_db(played[:,1])):.1f} dB)")

    # ---- exports ------------------------------------------------------
    def w(name, buf):
        pk = np.abs(buf).max()
        wavfile.write(name, sr, (buf / pk * 0.97 * 32767).astype(np.int16))
        print(f"   -> {name}")

    print("\nlistenable renders:")
    w("compare_1_original.wav", orig)
    w("compare_2_widened.wav", wide)
    w("compare_3_as_played.wav", played)


if __name__ == "__main__":
    main()
