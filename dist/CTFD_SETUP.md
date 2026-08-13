# CTFd 設定 — v2

## 附件

`double_fault.zip` — 內含 `double_fault/signal.wav`
（1.6 MB · 44.1kHz · 16-bit stereo · 9.53s）

sha256 (zip) : cb40f1599e1164cc14a270b41b8943e67482fdbaaafff6b9316278fa45aecbd2
sha256 (wav) : 0440f313205cfdd410187d092b652edaea73fe1ef4b25107fc8ce20c09051518

## 題目名稱

```
Double Fault
```

## 分類

```
Misc
```

Tags 建議：`audio` `dsp` `signal-processing`

**不要標 Stego** —— 它觸發的頻譜圖／LSB 反射動作在實測中全是死路，
頻譜圖更是原理上保證無效（丟掉相位，而圖形就活在相位裡）。
**不要標 Crypto** —— 沒有金鑰也沒有密文。

## 題目敘述（實測最佳版本）

```
Meant to be looked at, not listened to -- and not as a waveform.
The two channels have been mixed together, and one channel is late.
```

第一句用實測最快的措辭，避開「頻譜圖丟掉的東西 → 相位」陷阱。
第二句用 `one channel`（非 `one of them`）消除「來源 vs 聲道」歧義。

## Flag

```
THJCC{δράκος}
```

畫面分兩行：`THJCC{` 在上，`δράκος}` 在下。

### ⚠️ 提交比對務必做正規化

- 大小寫不敏感、去除前後空白
- Unicode 正規化為 **NFC**（`ά` 可能被輸入成 `α` + 組合重音 U+0301）
- 建議額外接受的等價寫法：
  - `ς`（U+03C2 字尾 sigma）↔ `σ`（U+03C3）
  - `κ` ↔ `k`　`ο` ↔ `o`　`ρ` ↔ `p`（希臘／拉丁同形字）

建議敘述加一行：「Flag 內容為希臘文，可直接複製貼上。」

## 難度定位

實測（隔離 AI agent，附上述敘述）：

| 版本 | 時間 |
|---|---|
| v1 | 44.4 分鐘 |
| **v2（本次發布）** | **17.5 分鐘** |
| 無敘述 | 6 次全部失敗 |

建議定位 **中高分題**。附敘述後強隊 15–45 分鐘可解；不附敘述大概率零解。

## 備援提示（長時間零解才放）

```
Fix the timing first, then undo the mix. The order matters.
```

## v2 相對 v1 的改動

| 項目 | v1 | v2 |
|---|---|---|
| 畫格週期 | 3000 | 2971（質數） |
| 畫格數 | 88（6 秒） | 8（0.54 秒） |
| 邊界 | 靜默間隔 | crossfade |
| 混合 | Mid/Side | 31° 旋轉 + 兩軸增益 0.62 |
| 斷行 | `THJCC` / `{δράκος}` | `THJCC{` / `δράκος}` |

最後一項修掉了一個真實缺陷：v1 上行只佔畫面寬度 63%，
用 percentile auto-contrast 的 render 可能整行裁掉，
導致選手只拿到 `{δράκος}` 卻不知道少了前綴。

### 已知：加固效果不如預期

v2 的任意 affine 可被一個解析捷徑五分鐘破解 —— 字母 `T` 的外框是 8 條軸對齊
線段，其邊緣角度直方圖的兩根尖峰**就是**混合矩陣的行基底，取反矩陣即可。
一般字型的文字會洩漏自己的座標軸，所以 affine 這層的上限就是「多花五分鐘」。

若要讓這層真的成為關卡，需改用**手寫體／圓體字型**（無長直線段，
直方圖不會出現乾淨尖峰）。目前版本未做此改動。
