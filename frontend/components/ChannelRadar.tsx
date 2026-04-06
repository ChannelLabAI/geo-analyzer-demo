"use client";

import { useState } from "react";
import { FullChannelScore, CHANNEL_COLORS } from "@/lib/types";

interface Props {
  fullChannel: FullChannelScore;
}

// Radar chart: rotated square (diamond), 4 axes at top/right/bottom/left
// Axes: Website(top), Media(right), Authority(bottom), Social(left)
// SVG coordinate system: center at (140, 140), radius 100
const CX = 140;
const CY = 140;
const R = 100;  // max radius = score 100

// Axis unit vectors (top, right, bottom, left)
const AXES = [
  { key: "web",    label: "官網",  weight: "30%", dx: 0,  dy: -1 },
  { key: "media",  label: "媒體",  weight: "25%", dx: 1,  dy: 0 },
  { key: "auth",   label: "權威",  weight: "25%", dx: 0,  dy: 1 },
  { key: "social", label: "社群",  weight: "20%", dx: -1, dy: 0 },
] as const;

type AxisKey = "web" | "media" | "auth" | "social";

function scoreToCoord(score: number, dx: number, dy: number) {
  const r = (score / 100) * R;
  return { x: CX + dx * r, y: CY + dy * r };
}

function gridCoords(fraction: number) {
  return AXES.map((a) => ({
    x: CX + a.dx * R * fraction,
    y: CY + a.dy * R * fraction,
  }));
}

function polyPoints(coords: { x: number; y: number }[]) {
  return coords.map((c) => `${c.x},${c.y}`).join(" ");
}

interface TooltipData {
  key: AxisKey;
  label: string;
  weight: string;
  score: number;
  x: number;
  y: number;
}

export function ChannelRadar({ fullChannel }: Props) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  const scores: Record<AxisKey, number> = {
    web:    fullChannel.website_score,
    media:  fullChannel.media_available ? (fullChannel.media_score ?? 0) : 0,
    auth:   fullChannel.authority_score,
    social: fullChannel.social_available ? (fullChannel.social_score ?? 0) : 0,
  };

  // Data polygon vertices
  const dataCoords = AXES.map((a) => scoreToCoord(scores[a.key], a.dx, a.dy));

  // Grid lines at 25 / 50 / 75 / 100
  const gridFractions = [0.25, 0.50, 0.75, 1.0];

  return (
    <div className="bg-card rounded-2xl p-6">
      <h3 className="text-base font-semibold text-slate-300 mb-4">全渠道雷達圖</h3>
      <div className="flex justify-center">
        <svg
          viewBox="0 0 280 280"
          className="w-[240px] h-[240px] sm:w-[280px] sm:h-[280px]"
          role="img"
          aria-label="全渠道評分雷達圖"
        >
          {/* Grid polygons */}
          {gridFractions.map((f) => {
            const pts = gridCoords(f);
            return (
              <polygon
                key={f}
                points={polyPoints(pts)}
                fill="none"
                stroke="#334155"
                strokeWidth="1"
              />
            );
          })}

          {/* Grid scale labels */}
          {[25, 50, 75].map((val) => (
            <text
              key={val}
              x={CX + 4}
              y={CY - (val / 100) * R + 4}
              className="fill-slate-600 text-[8px]"
              fontSize="8"
            >
              {val}
            </text>
          ))}

          {/* Axis lines */}
          {AXES.map((a) => (
            <line
              key={a.key}
              x1={CX}
              y1={CY}
              x2={CX + a.dx * R}
              y2={CY + a.dy * R}
              stroke="#334155"
              strokeWidth="1"
            />
          ))}

          {/* Data polygon fill */}
          <polygon
            points={polyPoints(dataCoords)}
            fill="rgba(59, 130, 246, 0.15)"
            stroke="#3B82F6"
            strokeWidth="2"
            style={{ transition: "all 0.8s ease-out" }}
          />

          {/* Axis labels */}
          {AXES.map((a) => {
            const lx = CX + a.dx * (R + 22);
            const ly = CY + a.dy * (R + 22);
            const textAnchor = a.dx === 0 ? "middle" : a.dx > 0 ? "start" : "end";
            return (
              <g key={a.key}>
                <text
                  x={lx}
                  y={ly - 4}
                  textAnchor={textAnchor}
                  fontSize="10"
                  fontWeight="500"
                  fill={CHANNEL_COLORS[a.key]}
                >
                  {a.label}
                </text>
                <text
                  x={lx}
                  y={ly + 8}
                  textAnchor={textAnchor}
                  fontSize="10"
                  fontWeight="600"
                  fill={CHANNEL_COLORS[a.key]}
                >
                  {scores[a.key].toFixed(0)}
                </text>
                <text
                  x={lx}
                  y={ly + 19}
                  textAnchor={textAnchor}
                  fontSize="8"
                  fill="#64748B"
                >
                  {a.weight}
                </text>
              </g>
            );
          })}

          {/* Vertex dots */}
          {AXES.map((a, i) => {
            const { x, y } = dataCoords[i];
            const isHovered = tooltip?.key === a.key;
            const available =
              a.key === "web" || a.key === "auth" ||
              (a.key === "media" && fullChannel.media_available) ||
              (a.key === "social" && fullChannel.social_available);

            return (
              <circle
                key={a.key}
                cx={x}
                cy={y}
                r={isHovered ? 7 : 5}
                fill={available ? CHANNEL_COLORS[a.key] : "#475569"}
                stroke={available ? "#0F172A" : "#334155"}
                strokeWidth="1.5"
                style={{ transition: "r 0.15s ease, cx 0.8s ease, cy 0.8s ease" }}
                onMouseEnter={() =>
                  setTooltip({ key: a.key, label: a.label, weight: a.weight, score: scores[a.key], x, y })
                }
                onMouseLeave={() => setTooltip(null)}
                className="cursor-pointer"
              />
            );
          })}

          {/* Tooltip */}
          {tooltip && (
            <g>
              <rect
                x={tooltip.x - 52}
                y={tooltip.y - 48}
                width={104}
                height={40}
                rx="6"
                fill="#1E293B"
                stroke="#334155"
                strokeWidth="1"
              />
              <text x={tooltip.x} y={tooltip.y - 32} textAnchor="middle" fontSize="9" fill="#CBD5E1" fontWeight="500">
                {tooltip.label} ({tooltip.weight})
              </text>
              <text x={tooltip.x} y={tooltip.y - 18} textAnchor="middle" fontSize="13" fill={CHANNEL_COLORS[tooltip.key]} fontWeight="700">
                {tooltip.score.toFixed(1)}
              </text>
            </g>
          )}
        </svg>
      </div>

      {/* Full-channel score summary */}
      <div className="mt-3 text-center">
        <span className="text-xs text-slate-500">全渠道評分 </span>
        <span className="font-mono font-bold text-white">{fullChannel.overall_score.toFixed(1)}</span>
      </div>
    </div>
  );
}
