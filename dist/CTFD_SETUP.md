# CTFd 設定 — v3

## 附件

`double_fault.zip` — 內含 `double_fault/signal.wav` + `README.txt`
（2.3 MB · 44.1kHz · 16-bit stereo · 13.88s）

sha256 (zip) : a1639d99cff9ec6af57a9a4c145cfc3561a7edb597f89dc701b6eeb01daf5669

**zip 內附了一份 `README.txt`，重複了題目敘述。** 這不是多餘 —— 見下方
「為什麼有 v3」。

## 題目名稱 / 分類

```
Double Fault          Misc
```

Tags：`audio` `dsp` `signal-processing`

**不要標 Stego**（觸發的頻譜圖／LSB 反射在實測中全是死路）；
**不要標 Crypto**（無金鑰、無密文）。

## 題目敘述

```
Meant to be looked at, not listened to -- and not as a waveform.
The two channels have been mixed together, and one channel is late.
```

**這段敘述是必要的，不是提示。** 八次無敘述測試全部失敗，包含兩次
大規模嘗試（78 萬 tokens／1 小時；5 個平行 worker／57 分鐘）。
附上敘述後，單一 agent 17.5 分鐘解出。

## Flag

```
THJCC{δράκος}
```

畫面分兩行：`THJCC{` 在上，`δράκος}` 在下。

### ⚠️ 提交比對務必正規化

- 大小寫不敏感、去除前後空白
- Unicode 正規化為 **NFC**（`ά` 可能被輸入成 `α` + 組合重音 U+0301）
- 建議接受等價寫法：`ς`↔`σ`、`κ`↔`k`、`ο`↔`o`、`ρ`↔`p`

## 為什麼有 v3

v2 把 payload 縮到 0.54 秒並用 crossfade 接進音樂，想讓它更難找。結果：

- 兩次獨立的高強度分析都**立刻**找到它，都稱之為 **buffer underrun**，
  並得出「**這個檔案壞了**」的結論。其中一份推測產生器的嵌入步驟沒執行成功。
- 而且隱蔽化**沒有增加難度** —— v2 反而比 v1 更快被解出（17.5 vs 44.4 分鐘）。

當選手分不出「很難」和「壞掉」，他們會停手並開申訴。這比太難更糟。

v3 撤回兩項隱蔽化，保留有效的改動：

| 項目 | v1 | v2 | v3 |
|---|---|---|---|
| payload 長度 | 6.0s | 0.54s | **4.04s** |
| 邊界 | 靜默 | crossfade | **靜默 150ms** |
| 畫格週期 | 3000 | 2971 | 2971 |
| 混合 | Mid/Side | 31° + 增益 | 31° + 增益 |
| 斷行 | `THJCC` / `{δράκος}` | `THJCC{` / `δράκος}` | `THJCC{` / `δράκος}` |

延遲判準餘裕也從 v2 的 110/114 回到 **1062/1100**，盲解穩定度大幅改善。

## 難度定位

建議 **中高分題**。附敘述後強隊 15–45 分鐘；不附敘述大概率零解。

## 備援提示（長時間零解才放）

```
Fix the timing first, then undo the mix. The order matters.
```

## 已知限制

任意 affine 那層可被解析捷徑五分鐘破解：字母 `T` 的外框是 8 條軸對齊線段，
其邊緣角度直方圖的兩根尖峰**就是**混合矩陣的行基底，取反矩陣即可。
一般字型的文字會洩漏自己的座標軸。

若要讓這層真的成為關卡，需改用**手寫體／圓體字型**。目前版本未做此改動 ——
難度主要仍來自「想到畫 X-Y」與「意識到要同時修兩層」。
