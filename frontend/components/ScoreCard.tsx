"use client";

import { BrandGEOScore, GRADE_COLORS } from "@/lib/types";

interface Props {
  score: BrandGEOScore;
}

export function ScoreCard({ score }: Props) {
  const gradeColor = GRADE_COLORS[score.grade] || "#6B7280";
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - score.overall_score / 100);

  return (
    <div className="bg-gray-800 rounded-2xl p-6 flex flex-col items-center gap-4">
      {/* Score ring */}
      <div className="relative w-40 h-40">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
          <circle cx="60" cy="60" r={radius} fill="none" stroke="#374151" strokeWidth="10" />
          <circle
            cx="60" cy="60" r={radius} fill="none"
            stroke={gradeColor}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 1s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold" style={{ color: gradeColor }}>
            {score.grade}
          </span>
          <span className="text-lg font-semibold text-white">
            {Math.round(score.overall_score)}
          </span>
        </div>
      </div>

      {/* Brand + label */}
      <div className="text-center">
        <p className="text-xl font-semibold text-white">{score.brand}</p>
        <p className="text-sm text-gray-400 mt-1">{score.grade_label}</p>
        <p className="text-xs text-gray-500 mt-1 truncate max-w-xs">{score.url}</p>
      </div>

      {/* Confidence badge */}
      <ConfidenceBadge level={score.data_confidence} />
    </div>
  );
}

function ConfidenceBadge({ level }: { level: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    high:   { label: "數據信心：高", cls: "bg-green-900 text-green-300" },
    medium: { label: "數據信心：中", cls: "bg-yellow-900 text-yellow-300" },
    low:    { label: "數據信心：低", cls: "bg-red-900 text-red-300" },
  };
  const { label, cls } = map[level] ?? map.low;
  return (
    <span className={`text-xs px-2 py-1 rounded-full font-medium ${cls}`}>{label}</span>
  );
}
