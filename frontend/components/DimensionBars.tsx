"use client";

import { WebsiteScore } from "@/lib/types";

interface Props {
  website: WebsiteScore;
}

const DIMENSIONS = [
  { key: "technical_score", label: "技術面", icon: "⚙️", color: "#60A5FA" },
  { key: "content_score",   label: "內容面", icon: "📝", color: "#34D399" },
  { key: "authority_score", label: "權威面", icon: "🏆", color: "#A78BFA" },
] as const;

export function DimensionBars({ website }: Props) {
  return (
    <div className="bg-gray-800 rounded-2xl p-6">
      <h3 className="text-base font-semibold text-gray-300 mb-4">維度分解</h3>
      <div className="space-y-5">
        {DIMENSIONS.map(({ key, label, icon, color }) => {
          const score = Math.round(website[key]);
          return (
            <div key={key}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm text-gray-300">
                  {icon} {label}
                </span>
                <span className="text-sm font-semibold text-white">{score}</span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${score}%`, backgroundColor: color }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Authority sub-breakdown */}
      {(website.traditional_authority > 0 || website.ai_authority > 0) && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-xs text-gray-500 mb-2">權威面細項</p>
          <div className="flex gap-4 text-xs text-gray-400">
            <span>PageRank: <span className="text-white">{Math.round(website.traditional_authority)}</span></span>
            <span>AI 引用: <span className="text-white">{Math.round(website.ai_authority)}</span></span>
          </div>
        </div>
      )}
    </div>
  );
}
