"use client";

import { BrandGEOScore, GRADE_COLORS } from "@/lib/types";

interface Props {
  score: BrandGEOScore;
}

function gradeFor(s: number): string {
  if (s >= 90) return "A";
  if (s >= 70) return "B";
  if (s >= 50) return "C";
  if (s >= 30) return "D";
  return "F";
}

export function BeforeAfter({ score }: Props) {
  if (score.action_items.length === 0) return null;

  const before = Math.round(score.overall_score);
  const after = Math.round(score.estimated_after_top3);
  const gain = after - before;
  const afterGrade = gradeFor(after);
  const afterColor = GRADE_COLORS[afterGrade] || "#6B7280";

  return (
    <div className="bg-card rounded-2xl p-6">
      <h3 className="text-base font-semibold text-slate-300 mb-4">
        完成 Top 3 建議後的預估分數
      </h3>

      {/* Before / After display */}
      <div className="flex items-center gap-4">
        {/* Before */}
        <div className="flex-1 bg-[#0F172A] rounded-xl p-4 text-center border border-[#334155]">
          <p className="text-xs text-slate-500 mb-1">現在</p>
          <p className="font-data text-3xl font-bold text-slate-300">{before}</p>
          <p className="text-xs text-slate-500 mt-1">{score.grade} 等</p>
        </div>

        {/* Arrow + gain */}
        <div className="flex flex-col items-center gap-1 shrink-0">
          <span className="text-green-400 text-xl">→</span>
          <span className="font-data text-xs font-semibold text-green-400">+{gain}</span>
        </div>

        {/* After */}
        <div className="flex-1 bg-[#0F172A] rounded-xl p-4 text-center border border-[#334155]"
             style={{ borderColor: afterColor + "66" }}>
          <p className="text-xs text-slate-500 mb-1">預估</p>
          <p className="font-data text-3xl font-bold" style={{ color: afterColor }}>{after}</p>
          <p className="text-xs mt-1" style={{ color: afterColor }}>{afterGrade} 等</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-4">
        <div className="h-2 bg-[#334155] rounded-full overflow-hidden relative">
          {/* Before marker */}
          <div
            className="absolute top-0 left-0 h-full bg-slate-500 rounded-full"
            style={{ width: `${before}%` }}
          />
          {/* After fill */}
          <div
            className="absolute top-0 left-0 h-full rounded-full transition-all duration-700"
            style={{ width: `${after}%`, backgroundColor: afterColor + "80" }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>0</span>
          <span className="text-slate-400">完成 Top 3 建議後預估提升 +{gain} 分</span>
          <span>100</span>
        </div>
      </div>
    </div>
  );
}
