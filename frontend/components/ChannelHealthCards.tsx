"use client";

import { BrandGEOScore, FullChannelScore, CHANNEL_COLORS, GRADE_COLORS } from "@/lib/types";

interface Props {
  score: BrandGEOScore;
}

interface CardDef {
  key: "web" | "media" | "social" | "auth";
  icon: string;
  label: string;
  weight: string;
  colorKey: keyof typeof CHANNEL_COLORS;
  getScore: (score: BrandGEOScore, fc: FullChannelScore) => number | null;
  getConfidence: (score: BrandGEOScore, fc: FullChannelScore) => string;
  getSubScores: (score: BrandGEOScore, fc: FullChannelScore) => { label: string; value: number }[];
}

const CARDS: CardDef[] = [
  {
    key: "web",
    icon: "🌐",
    label: "官網",
    weight: "30%",
    colorKey: "web",
    getScore: (s) => s.website.overall_score,
    getConfidence: (s) => s.data_confidence,
    getSubScores: (s) => [
      { label: "技術", value: s.website.technical_score },
      { label: "內容", value: s.website.content_score },
      { label: "權威", value: s.website.authority_score },
    ],
  },
  {
    key: "media",
    icon: "📰",
    label: "媒體",
    weight: "25%",
    colorKey: "media",
    getScore: (_s, fc) => (fc.media_available ? fc.media_score : null),
    getConfidence: (s) => s.media?.data_confidence ?? "low",
    getSubScores: (s) =>
      s.media
        ? [
            { label: "內容量", value: s.media.content_count_score },
            { label: "引用率", value: s.media.citation_hit_rate_score },
            { label: "平台權重", value: s.media.platform_weight_score },
          ]
        : [],
  },
  {
    key: "social",
    icon: "💬",
    label: "社群",
    weight: "20%",
    colorKey: "social",
    getScore: (_s, fc) => (fc.social_available ? fc.social_score : null),
    getConfidence: (s) => s.social?.data_confidence ?? "low",
    getSubScores: (s) =>
      s.social
        ? [
            { label: "討論頻率", value: s.social.discussion_frequency_score },
            { label: "引用率", value: s.social.citation_hit_rate_score },
            { label: "情感分", value: s.social.sentiment_score },
          ]
        : [],
  },
  {
    key: "auth",
    icon: "🏆",
    label: "權威",
    weight: "25%",
    colorKey: "auth",
    getScore: (_s, fc) => fc.authority_score,
    getConfidence: (s) => s.data_confidence,
    getSubScores: (s) => [
      { label: "PageRank", value: s.website.traditional_authority },
      { label: "AI 引用", value: s.website.ai_authority },
    ],
  },
];

const CONFIDENCE_DOTS: Record<string, number> = { high: 3, medium: 2, low: 1 };

export function ChannelHealthCards({ score }: Props) {
  const fc = score.full_channel;

  // Phase 1 fallback: no full-channel data, show legacy ChannelCards layout
  if (!fc) {
    return <LegacyChannelCards score={score} />;
  }

  return (
    <div className="bg-card rounded-2xl p-6">
      <h3 className="text-base font-semibold text-slate-300 mb-4">渠道健康度</h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {CARDS.map((card) => {
          const channelScore = card.getScore(score, fc);
          const confidence = card.getConfidence(score, fc);
          const subScores = card.getSubScores(score, fc);
          const color = CHANNEL_COLORS[card.colorKey];
          const available = channelScore !== null;

          return (
            <ChannelCard
              key={card.key}
              icon={card.icon}
              label={card.label}
              weight={card.weight}
              color={color}
              score={channelScore}
              available={available}
              confidence={confidence}
              subScores={subScores}
            />
          );
        })}
      </div>
    </div>
  );
}

interface ChannelCardProps {
  icon: string;
  label: string;
  weight: string;
  color: string;
  score: number | null;
  available: boolean;
  confidence: string;
  subScores: { label: string; value: number }[];
}

function ChannelCard({
  icon, label, weight, color, score, available, confidence, subScores,
}: ChannelCardProps) {
  const dots = CONFIDENCE_DOTS[confidence] ?? 1;

  return (
    <div
      className={`bg-[#0F172A] rounded-xl p-4 border border-[#334155] transition-opacity ${!available ? "opacity-70" : ""}`}
      style={{ borderLeftWidth: "3px", borderLeftColor: color }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <span className="text-base">{icon}</span>
          <span className="text-xs font-medium text-slate-200">{label}</span>
        </div>
      </div>

      {/* Score */}
      <div className="font-mono text-2xl font-bold mb-2" style={{ color }}>
        {available && score !== null ? Math.round(score) : "--"}
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-slate-700 rounded-full mb-3">
        {available && score !== null && (
          <div
            className="h-1 rounded-full transition-all duration-700"
            style={{ width: `${score}%`, backgroundColor: color }}
          />
        )}
      </div>

      {/* Sub-scores */}
      {available && subScores.length > 0 ? (
        <div className="flex gap-1 flex-wrap mb-2">
          {subScores.map((s) => (
            <span key={s.label} className="text-[10px] text-slate-400">
              {s.label} <span className="font-mono text-slate-300">{Math.round(s.value)}</span>
            </span>
          ))}
        </div>
      ) : !available ? (
        <p className="text-xs text-slate-600 mb-2">分析中...</p>
      ) : null}

      {/* Footer meta */}
      <div className="flex items-center justify-between mt-1">
        <span className="text-[10px] text-slate-500">權重 {weight}</span>
        <ConfidenceDots dots={dots} />
      </div>
    </div>
  );
}

function ConfidenceDots({ dots }: { dots: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i <= dots ? "bg-slate-300" : "bg-slate-700"}`}
        />
      ))}
    </div>
  );
}

// Phase 1 fallback — replicates the original ChannelCards layout
function LegacyChannelCards({ score }: { score: BrandGEOScore }) {
  const websiteScore = Math.round(score.website.overall_score);
  const gradeColor = GRADE_COLORS[score.grade] || "#6B7280";

  return (
    <div className="bg-card rounded-2xl p-6">
      <h3 className="text-base font-semibold text-slate-300 mb-4">四渠道分解</h3>
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#0F172A] rounded-xl p-4 border border-[#334155]">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🌐</span>
            <span className="text-sm font-medium text-slate-200">官網</span>
          </div>
          <div className="font-mono text-2xl font-bold" style={{ color: gradeColor }}>
            {websiteScore}
          </div>
          <div className="text-xs text-slate-400 mt-1">技術 / 內容 / 權威</div>
        </div>
        <ComingSoon icon="📰" label="媒體報導" />
        <ComingSoon icon="💬" label="社群媒體" />
        <ComingSoon icon="🔗" label="其他渠道" />
      </div>
    </div>
  );
}

function ComingSoon({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="bg-[#0F172A]/60 rounded-xl p-4 border border-[#334155]/50 opacity-50">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg grayscale">{icon}</span>
        <span className="text-sm font-medium text-slate-400">{label}</span>
      </div>
      <div className="font-mono text-2xl font-bold text-slate-600">--</div>
      <div className="text-xs text-slate-600 mt-1">即將推出</div>
    </div>
  );
}
