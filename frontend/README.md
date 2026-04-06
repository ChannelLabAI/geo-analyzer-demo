# Brand GEO Score Dashboard

Next.js 14 前端，配合 `serve.py` 提供品牌 AI 能見度評分（0-100 分）的完整儀表板。

## 啟動

```bash
# 確保 Python API 已在 :8080 跑起來
cd .. && python3 serve.py &

# 安裝依賴並啟動 dev server
bun install
bun run dev
```

開啟 [http://localhost:3000](http://localhost:3000)，輸入品牌網址開始分析。

## 路由

| Path | 說明 |
|------|------|
| `/` | Landing page — URL + 品牌名輸入表單 |
| `/result/[job_id]` | 評分結果頁，每 2 秒 polling 直到完成 |
| `/history` | 歷史記錄（Phase 2，目前為 skeleton） |

## 組件

| 組件 | 說明 |
|------|------|
| `ScoreCard` | 品牌總分 + 等級 ring 動畫（A–F，顏色區分） |
| `ChannelCards` | 四渠道分解：官網（active）/ 媒體/社群/其他（即將推出） |
| `DimensionBars` | 技術 / 內容 / 權威三維度進度條 |
| `ActionItems` | 改善建議，按預估增分排序 |
| `BeforeAfter` | 完成 Top 3 建議後的預估分數對比 |
| `PollingStatus` | 分析進度條 + 剩餘時間估算 |

## 技術細節

- **Next.js 14** App Router（Node 18 相容）
- **Tailwind CSS**，自定義 token：`surface` #0F172A / `card` #1E293B
- **JetBrains Mono**（`font-data` class）用於所有數字顯示
- **API Proxy**：`/api/*` → `http://127.0.0.1:8080/api/*`（用 127.0.0.1 避免 IPv6 解析問題）

## Build

```bash
bun run build    # 生產 build
bun run lint     # ESLint 檢查
```
