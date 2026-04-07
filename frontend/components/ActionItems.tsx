"use client";

import { ActionItem } from "@/lib/types";

interface Props {
  items: ActionItem[];
}

const DIFFICULTY_LABEL: Record<string, string> = {
  easy: "簡單",
  medium: "中等",
  hard: "困難",
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: "text-green-400",
  medium: "text-yellow-400",
  hard: "text-red-400",
};

export function ActionItems({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="bg-gray-800 rounded-2xl p-6">
        <h3 className="text-base font-semibold text-gray-300 mb-2">改善建議</h3>
        <p className="text-sm text-gray-500">暫無建議 — 繼續保持！</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-2xl p-6">
      <h3 className="text-base font-semibold text-gray-300 mb-4">
        改善建議
        <span className="ml-2 text-xs text-gray-500 font-normal">按分數提升排序</span>
      </h3>
      <div className="space-y-3">
        {items.map((item, i) => (
          <div key={i} className="bg-gray-700/50 rounded-xl p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white">{item.title}</p>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">{item.description}</p>
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <span className="text-xs font-semibold text-green-400">
                  +{item.estimated_score_gain.toFixed(0)} 分
                </span>
                <span className={`text-xs ${DIFFICULTY_COLOR[item.difficulty] ?? "text-gray-400"}`}>
                  {DIFFICULTY_LABEL[item.difficulty] ?? item.difficulty}
                </span>
                <span className="text-xs text-gray-500">{item.estimated_hours}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
