# CTFd 設定

## 附件

`double_fault.zip` — 內含 `double_fault/double_fault.wav`（2.8 MB，44.1kHz / 16-bit stereo / 15.88s）

sha256 (zip) : 612c81d3de7578f1ea95f07e36c13fb9180f13097c3f7f0b0227df0409588d9f
sha256 (wav) : e2e0eacec41e484490dff89b31a32be851f9a152d8b1bd338f4151d8094964a8

## 題目名稱

```
Double Fault
```

## 題目敘述（實測最佳版本）

```
Meant to be looked at, not listened to -- and not as a waveform.
The two channels have been mixed together, and one channel is late.
```

第一句用實測最快的措辭（15.9 分鐘），避開「頻譜圖丟掉的東西 → 相位」陷阱。
第二句的 `one channel`（而非 `one of them`）消除「來源 vs 聲道」歧義 ——
該歧義曾讓一個 agent 浪費 45–50% 的總工時。

## Flag

```
THJCC{δράκος}
```

### ⚠️ 提交比對務必做正規化

希臘字母極易打錯，建議後端：

- 大小寫不敏感、去除前後空白
- Unicode 正規化為 **NFC**（`ά` 可能被輸入成 `α` + 組合重音 U+0301）
- 建議額外接受的等價寫法：
  - `ς`（U+03C2 字尾 sigma）↔ `σ`（U+03C3）
  - `κ`（希臘 kappa）↔ `k`（拉丁）
  - `ο`（希臘 omicron）↔ `o`（拉丁）
  - `ρ`（希臘 rho）↔ `p`（拉丁）

建議在敘述附一行：「Flag 內容為希臘文，可直接複製貼上。」
或提供希臘字母對照表連結，降低申訴量。

## 分數建議

實測解題時間（隔離 AI agent，附敘述）：**15.9 分鐘 / 44.4 分鐘**
無敘述條件：6 次全部失敗

建議定位為**中高分題**。

## 備援提示（卡關才放）

```
Fix the timing first, then undo the mix. The order matters.
```

實測顯示這層非必要，但若比賽中長時間零解可作為最後一張牌。
