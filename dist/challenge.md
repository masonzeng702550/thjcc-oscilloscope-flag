# Double Fault

**Category:** Misc
**Tags:** audio, dsp, signal-processing
**Attachment:** `chal.zip` (sha256 `5cd0e88d6c6cb31df852d473fcba33438e1c7d37bf4ce06e4c5979bd8dbbe64f`)

## Description

```
Meant to be looked at, not listened to -- and not as a waveform.
The two channels have been mixed together, and one channel is late.

The flag is Greek text; copy it rather than retyping.
```

## Flag

```
THJCC{δράκος}
```

Rendered on two lines: `THJCC{` above, `δράκος}` below.

## Flag checking

Normalise before comparing, or expect tickets:

- Unicode **NFC** — `ά` may be entered as `α` + U+0301
- Strip whitespace, case-insensitive
- Accept `ς`↔`σ`, `κ`↔`k`, `ο`↔`o`, `ρ`↔`p`

## Hint (release only on a long zero-solve streak)

```
Fix the timing first, then undo the mix. The order matters.
```

## Notes for the organiser

- The description is not optional. Eight blind attempts without it all failed;
  with it, solve times were 6-45 minutes.
- Do not tag this Stego. That label sends players to spectrogram and LSB tools,
  both of which are dead ends here.
