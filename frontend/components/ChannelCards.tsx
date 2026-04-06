"use client";

import { BrandGEOScore, GRADE_COLORS } from "@/lib/types";

interface Props {
  score: BrandGEOScore;
}

export function ChannelCards({ score }: Props) {
  const websiteScore = Math.round(score.website.overall_score);
  const websiteGrade = score.grade;
  const gradeColor = GRADE_COLORS[websiteGrade] || "#6B7280";

  return (
    <div className="bg-card rounded-2xl p-6">
      <h3 className="text-base font-semibold text-slate-300 mb-4">四渠道分解</h3>
      <div className="grid grid-cols-2 gap-3">
        {/* 官網 — active, shows real score */}
        <div className="bg-[#0F172A] rounded-xl p-4 border border-[#334155]">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🌐</span>
            <span className="text-sm font-medium text-slate-200">官網</span>
          </div>
          <div className="font-data text-2xl font-bold" style={{ color: gradeColor }}>
            {websiteScore}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            技術 / 內容 / 權威
          </div>
        </div>

        {/* 媒體 — Phase 2, grayed out */}
        <ComingSoonCard icon="📰" label="媒體報導" />

        {/* 社群 — Phase 2, grayed out */}
        <ComingSoonCard icon="💬" label="社群媒體" />

        {/* 其他 — Phase 2, grayed out */}
        <ComingSoonCard icon="🔗" label="其他渠道" />
      </div>
    </div>
  );
}

function ComingSoonCard({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="bg-[#0F172A]/60 rounded-xl p-4 border border-[#334155]/50 opacity-50">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg grayscale">{icon}</span>
        <span className="text-sm font-medium text-slate-400">{label}</span>
      </div>
      <div className="font-data text-2xl font-bold text-slate-600">--</div>
      <div className="text-xs text-slate-600 mt-1">即將推出</div>
    </div>
  );
}
