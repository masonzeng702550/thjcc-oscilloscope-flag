# All Night Long

**Category:** Misc
**Tags:** audio, dsp, signal-processing
**Attachment:** `chal.zip` (sha256 `5cd0e88d6c6cb31df852d473fcba33438e1c7d37bf4ce06e4c5979bd8dbbe64f`)

## Description

```
奶龍不唱歌——別聽牠,用看的,而且不是看波形。牠左右兩隻爪子的動作被攪在一起了,還有一隻慢了半拍。Flag 內容為希臘文,請複製貼上,不要手動輸入。
```

English:

```
The dragon doesn't sing. Look at it, and not as a waveform. Its two claws got tangled together, and one of them is running late. The flag is Greek text, so copy it rather than retyping.
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
