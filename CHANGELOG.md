# Changelog

All notable changes to GEO Analyzer Demo are documented here.

## [0.2.0] - 2026-04-06

### Added — Phase 2: Full-Channel Dashboard

- **`ChannelRadar`** (`components/ChannelRadar.tsx`): hand-coded SVG diamond radar chart showing Website / Media / Social / Authority four-axis weighted scores. Hover tooltips with channel score, available/N/A state, and per-axis color coding.
- **`ChannelHealthCards`** (`components/ChannelHealthCards.tsx`): four score cards — one per channel. Each shows score, data confidence dots (low/medium/high), and expandable platform details. Falls back to legacy `LegacyChannelCards` layout when Phase 2 data is absent.
- **`SourceChannelMatrix`** (`components/SourceChannelMatrix.tsx`): citation heatmap table — rows = AI engines, columns = channels. Cell color opacity scales with citation count (0→transparent, 1-2→30%, 3-5→60%, 6+→100%). Sticky left column, hover tooltip, channel contribution summary row.
- **Phase 2 type definitions** (`lib/types.ts`): `FullChannelScore`, `MediaScore`, `SocialScore`, `CrossChannelAnalysis`, `PlatformDetail`. `BrandGEOScore` extended with optional `full_channel`, `full_channel_score`, `media`, `social` fields.
- **Channel design tokens** (`tailwind.config.ts`): `channel-web` (Blue 500), `channel-media` (Amber 500), `channel-social` (Pink 500), `channel-auth` (Violet 400). WCAG AA on dark bg, hue separation ≥60°.
- **Result page update** (`app/result/[job_id]/page.tsx`): Phase 2 layout — `ScoreCard` + `ChannelRadar` side-by-side, `ChannelHealthCards` below, `SourceChannelMatrix` conditional on `full_channel` presence. Phase 1 path unchanged.

### Backward compatibility

- Phase 1 data (`overall_score`, `grade`, `website.*`) renders the existing layout unchanged.
- Phase 2 components render only when `BrandGEOScore.full_channel` is present.

## [0.1.0] - 2026-04-05

### Added

- **Brand GEO Score Dashboard**: Next.js 14 + Tailwind CSS front-end with polling-based job status, score ring, dimension bars, action items, and before/after score projection.
- **GEO Analyzer SPA** (`index.html`): multi-platform citation analysis, competitor comparison, query × platform matrix, source ranking, history trend chart, PDF export.
- **Python API server** (`serve.py`): Brand GEO Score job queue, history SQLite store, live/demo mode switching.
