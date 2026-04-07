"use client";

import { useState } from "react";
import { FullChannelScore, CHANNEL_COLORS, GRADE_COLORS } from "@/lib/types";

interface SourceRow {
  engine: string;
  available: boolean;
  channels: { website: number; media: number; social: number };
  overall: number;
  grade: string;
}

interface Props {
  fullChannel: FullChannelScore;
  // Raw citation data — rows derived from BrandReport if available
  // Falls back to synthetic rows from cross_analysis when no detailed data
  rows?: SourceRow[];
}

const CHANNELS: { key: keyof SourceRow["channels"]; label: string; colorKey: keyof typeof CHANNEL_COLORS }[] = [
  { key: "website", label: "官網",   colorKey: "web" },
  { key: "media",   label: "媒體",   colorKey: "media" },
  { key: "social",  label: "社群",   colorKey: "social" },
];

function citationColor(
  count: number,
  channelKey: keyof typeof CHANNEL_COLORS,
): string {
  const base = CHANNEL_COLORS[channelKey];
  if (count === 0) return "transparent";
  const opacity = count >= 6 ? 1.0 : count >= 3 ? 0.6 : 0.3;
  // Apply opacity to hex color by converting to rgba
  const r = parseInt(base.slice(1, 3), 16);
  const g = parseInt(base.slice(3, 5), 16);
  const b = parseInt(base.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

// Build synthetic rows from cross-analysis when no detailed citation data
function buildSyntheticRows(fullChannel: FullChannelScore): SourceRow[] {
  const contrib = fullChannel.cross_analysis.channel_contribution;
  // We don't have per-engine breakdown without citation scan — show one summary row
  const total = Object.values(contrib).reduce((a, b) => a + b, 0);
  if (total === 0) return [];

  const websiteCount = Math.round((contrib["website"] ?? 0) * 20);
  const mediaCount = Math.round((contrib["media"] ?? 0) * 20);
  const socialCount = Math.round((contrib["social"] ?? 0) * 20);

  return [
    {
      engine: "全渠道彙總",
      available: true,
      channels: { website: websiteCount, media: mediaCount, social: socialCount },
      overall: fullChannel.overall_score,
      grade: overallGrade(fullChannel.overall_score),
    },
  ];
}

function overallGrade(score: number): string {
  if (score >= 90) return "A";
  if (score >= 70) return "B";
  if (score >= 50) return "C";
  if (score >= 30) return "D";
  return "F";
}

interface TooltipInfo {
  engine: string;
  channel: string;
  count: number;
  total: number;
  rowIdx: number;
  colIdx: number;
}

export function SourceChannelMatrix({ fullChannel, rows }: Props) {
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  const displayRows = rows ?? buildSyntheticRows(fullChannel);

  if (displayRows.length === 0) {
    return (
      <div className="bg-card rounded-2xl p-6">
        <MatrixHeader />
        <p className="text-sm text-slate-500 mt-4 text-center">
          需要執行 Citation Scan 才能顯示交叉分析
        </p>
      </div>
    );
  }

  // Sort by overall descending
  const sorted = [...displayRows].sort((a, b) => b.overall - a.overall);

  return (
    <div className="bg-card rounded-2xl p-6">
      <MatrixHeader />

      <div className="overflow-x-auto mt-4">
        <table className="w-full text-xs min-w-[320px]">
          <thead>
            <tr>
              <th className="text-left py-2 pr-4 text-slate-400 font-medium sticky left-0 bg-card z-10 min-w-[100px]">
                AI 引擎
              </th>
              {CHANNELS.map((ch) => (
                <th
                  key={ch.key}
                  className="text-center py-2 px-3 font-medium"
                  style={{ color: CHANNEL_COLORS[ch.colorKey] }}
                >
                  {ch.label}
                </th>
              ))}
              <th className="text-center py-2 px-3 text-slate-400 font-medium">彙總</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, rowIdx) => {
              const totalCitations = Object.values(row.channels).reduce((a, b) => a + b, 0);
              const gradeColor = GRADE_COLORS[row.grade] || "#6B7280";

              return (
                <tr key={row.engine} className={row.available ? "" : "opacity-40"}>
                  {/* Engine name — sticky */}
                  <td className="py-2 pr-4 sticky left-0 bg-card z-10">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-200 font-medium">{row.engine}</span>
                      {!row.available && (
                        <span className="text-[9px] text-slate-600 border border-slate-700 rounded px-1">未接入</span>
                      )}
                    </div>
                  </td>

                  {/* Citation cells */}
                  {CHANNELS.map((ch, colIdx) => {
                    const count = row.channels[ch.key];
                    const bgColor = citationColor(count, ch.colorKey);
                    const isHovered =
                      tooltip?.rowIdx === rowIdx && tooltip?.colIdx === colIdx;

                    return (
                      <td key={ch.key} className="py-2 px-3 text-center">
                        <div
                          className="relative mx-auto w-10 h-8 rounded flex items-center justify-center font-mono font-semibold cursor-default select-none"
                          style={{
                            backgroundColor: bgColor,
                            color: count > 0 ? "#F1F5F9" : "#475569",
                            border: isHovered ? `1px solid ${CHANNEL_COLORS[ch.colorKey]}` : "1px solid transparent",
                            transition: "border 0.15s ease",
                          }}
                          onMouseEnter={() =>
                            setTooltip({
                              engine: row.engine,
                              channel: ch.label,
                              count,
                              total: totalCitations,
                              rowIdx,
                              colIdx,
                            })
                          }
                          onMouseLeave={() => setTooltip(null)}
                        >
                          {count > 0 ? count : "·"}
                        </div>
                      </td>
                    );
                  })}

                  {/* Overall score */}
                  <td className="py-2 px-3 text-center">
                    <span
                      className="font-mono font-bold text-sm px-2 py-0.5 rounded"
                      style={{ color: gradeColor, backgroundColor: `${gradeColor}1a` }}
                    >
                      {Math.round(row.overall)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Tooltip */}
      {tooltip && tooltip.count > 0 && (
        <div className="mt-3 text-xs text-slate-400 text-center">
          <span className="font-medium text-slate-200">{tooltip.engine}</span> 從{" "}
          <span className="font-medium text-slate-200">{tooltip.channel}</span> 引用了{" "}
          <span className="font-mono font-bold text-white">{tooltip.count}</span> 次
          {tooltip.total > 0 && (
            <span className="text-slate-500">
              {" "}（佔 {Math.round((tooltip.count / tooltip.total) * 100)}%）
            </span>
          )}
        </div>
      )}

      {/* Channel contribution summary */}
      {Object.keys(fullChannel.cross_analysis.channel_contribution).length > 0 && (
        <div className="mt-4 flex gap-4 flex-wrap justify-center">
          {Object.entries(fullChannel.cross_analysis.channel_contribution)
            .sort(([, a], [, b]) => b - a)
            .map(([ch, pct]) => {
              const colorKey = ch === "website" ? "web" : ch === "authority" ? "auth" : (ch as keyof typeof CHANNEL_COLORS);
              const color = CHANNEL_COLORS[colorKey] || "#94A3B8";
              return (
                <div key={ch} className="flex items-center gap-1.5 text-xs">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-slate-400 capitalize">{ch}</span>
                  <span className="font-mono text-slate-200">{Math.round(pct * 100)}%</span>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}

function MatrixHeader() {
  return (
    <div>
      <h3 className="text-base font-semibold text-slate-300">Source × Channel 交叉分析</h3>
      <p className="text-xs text-muted mt-0.5">哪些 AI 引擎偏好引用您的哪些渠道？</p>
    </div>
  );
}
