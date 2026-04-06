# GEO Analyzer Demo

AI 品牌可見度分析工具 — 分析品牌在 Gemini、Perplexity、Google AI Overview 等 AI 搜尋平台的引用表現。

**Live Demo:** [channellabai.github.io/geo-analyzer-demo](https://channellabai.github.io/geo-analyzer-demo/)

## Features

- **多平台分析** — Gemini、Perplexity、Google AI Overview
- **競品對比** — 同一組查詢比較最多 3 個競品的引用率
- **查詢 × 平台矩陣** — 每條查詢在每個平台的引用狀態
- **AI 引用來源排行** — 哪些網域最常被 AI 平台引用
- **歷史趨勢** — 追蹤品牌引用率隨時間的變化（≥2 次分析時顯示折線圖）
- **PDF 報告匯出** — 一鍵生成專業 PDF 報告
- **分析結果持久化** — SQLite 自動存檔，可回看歷史分析

## Quick Start

### GEO Analyzer Demo（競品分析儀表板）

```bash
# Demo mode（mock data，不需要 API key）
python3 serve.py

# Live mode（需要 geo-analyzer + API keys）
python3 serve.py --live

# 指定 port
python3 serve.py --port 3000
python3 serve.py --live --port 3000
```

Server 啟動後會自動開啟瀏覽器到 `http://localhost:8080/`。

### Brand GEO Score Dashboard（品牌評分儀表板）

輸入品牌網址，AI 分析後給出 0-100 分的品牌 AI 能見度評分，含維度分解和改善建議。

```bash
# 1. 啟動 Python API（在一個 terminal）
python3 serve.py

# 2. 啟動 Next.js 前端（在另一個 terminal）
cd frontend && bun install && bun run dev
```

前端開啟 [http://localhost:3000](http://localhost:3000)，輸入品牌網址即可開始分析。

**環境需求：** Node.js 18+，Bun，Python 3.9+

## Modes

| Mode | 說明 | 需要 API Key |
|------|------|:---:|
| Demo | 使用 `data/mock_data.json` 回傳假資料 | ❌ |
| Live | 呼叫 geo-analyzer CLI 執行真實分析 | ✅ |

Live mode 需要 [geo-analyzer](https://github.com/ChannelLabAI/geo-analyzer) 安裝在 `~/AIwork/projects/geo-analyzer`。

## API Endpoints

### GEO Analyzer API

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/analyze?brand=X&queries=Q&competitors=C&platforms=P` | 執行分析 |
| GET | `/api/status` | 取得 server 模式 |
| GET | `/api/history?limit=N` | 歷史分析列表 |
| GET | `/api/history/<id>` | 單筆分析完整結果 |
| GET | `/api/history/trend?brand=X` | 品牌趨勢數據 |
| DELETE | `/api/history/<id>` | 刪除歷史紀錄 |

### Brand GEO Score API

| Method | Path | 說明 |
|--------|------|------|
| POST | `/api/brand-score?url=URL&brand=NAME` | 建立評分任務，回傳 `{job_id, estimated_total}` |
| GET | `/api/brand-score/<job_id>` | 查詢任務進度，回傳 `{status, progress, result}` |

任務 TTL 30 分鐘，狀態：`pending` → `running` → `done` / `error`。

### Analyze Parameters

- `brand` (required) — 品牌名稱
- `queries` — 逗號分隔的查詢關鍵詞，不填則用品牌名稱
- `competitors` — 逗號分隔的競品名稱，最多 3 個
- `platforms` — `gemini`, `perplexity`, `google_aio`（逗號分隔）

## Project Structure

```
geo-analyzer-demo/
├── index.html              # GEO Analyzer SPA（Landing → Results）
├── serve.py                # HTTP server + API（GEO Analyzer + Brand GEO Score）
├── tests/
│   └── test_brand_score_api.py  # Brand GEO Score API 測試（13 tests）
├── css/common.css          # NOXCAT dark theme
├── data/
│   ├── mock_data.json      # Demo mode 假資料
│   └── history.db          # SQLite 歷史資料（auto-generated）
├── screenshots/            # Live mode 截圖（auto-generated）
└── frontend/               # Brand GEO Score Dashboard（Next.js 14）
    ├── app/
    │   ├── page.tsx        # Landing page（URL + 品牌輸入表單）
    │   ├── result/[job_id]/page.tsx  # 評分結果頁（polling + 完整報告）
    │   └── history/page.tsx  # 歷史記錄（Phase 2）
    ├── components/         # ScoreCard, DimensionBars, ActionItems,
    │                       #   ChannelCards, BeforeAfter, PollingStatus
    └── lib/types.ts        # TypeScript 型別定義
```

## Static Deploy (GitHub Pages)

靜態版自動偵測 `github.io` domain，跳過需要後端的功能（歷史列表、趨勢圖），直接使用 `data/mock_data.json`。

---

Built by [ChannelLab](https://channellab.tw)
