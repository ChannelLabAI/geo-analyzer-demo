"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { BrandGEOScore, JobResponse, API_BASE } from "@/lib/types";
import { ScoreCard } from "@/components/ScoreCard";
import { DimensionBars } from "@/components/DimensionBars";
import { ActionItems } from "@/components/ActionItems";
import { PollingStatus } from "@/components/PollingStatus";

const POLL_INTERVAL_MS = 2000;

export default function ResultPage() {
  const params = useParams();
  const jobId = params.job_id as string;

  const [job, setJob] = useState<JobResponse | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let cancelled = false;

    // Elapsed timer
    const elapsedTimer = setInterval(() => {
      setElapsed(Math.round((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    async function poll() {
      if (cancelled) return;

      try {
        const res = await fetch(`${API_BASE}/api/brand-score/${jobId}`);
        if (!res.ok) {
          if (res.status === 404) {
            setFetchError("找不到分析任務。可能已過期（30 分鐘 TTL）。");
          } else {
            setFetchError(`伺服器錯誤 (${res.status})`);
          }
          return;
        }
        const data: JobResponse = await res.json();
        if (!cancelled) {
          setJob(data);
          if (data.status === "done" || data.status === "error") {
            return; // stop polling
          }
          // Schedule next poll
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch {
        if (!cancelled) {
          setFetchError("無法連線到分析伺服器。");
        }
      }
    }

    poll();

    return () => {
      cancelled = true;
      clearInterval(elapsedTimer);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [jobId]);

  // Error connecting to server
  if (fetchError) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="text-5xl mb-4">⚠️</div>
        <p className="text-xl font-semibold text-red-400 mb-2">無法取得結果</p>
        <p className="text-sm text-gray-400 text-center max-w-md mb-6">{fetchError}</p>
        <Link href="/" className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">
          重新分析
        </Link>
      </main>
    );
  }

  // Still loading or pending — show polling status
  if (!job || job.status === "pending" || job.status === "running") {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-md bg-gray-800 rounded-2xl p-8">
          <PollingStatus
            status={(job?.status as "pending" | "running") ?? "pending"}
            progress={job?.progress ?? 0}
            estimatedTotal={job?.estimated_total ?? 45}
            error={job?.error}
            elapsedSeconds={elapsed}
          />
        </div>
      </main>
    );
  }

  // Job failed
  if (job.status === "error") {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-md bg-gray-800 rounded-2xl p-8">
          <PollingStatus
            status="error"
            progress={0}
            estimatedTotal={45}
            error={job.error}
            elapsedSeconds={elapsed}
          />
        </div>
      </main>
    );
  }

  // Done — render full results
  const score = job.result as BrandGEOScore;

  return (
    <main className="min-h-screen px-4 py-12">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Nav */}
        <div className="flex items-center justify-between">
          <Link href="/" className="text-sm text-gray-400 hover:text-white transition-colors">
            ← 重新分析
          </Link>
          <span className="text-xs text-gray-600">
            生成時間：{new Date(score.generated_at).toLocaleString("zh-TW")}
          </span>
        </div>

        {/* Score card */}
        <ScoreCard score={score} />

        {/* Dimension breakdown */}
        <DimensionBars website={score.website} />

        {/* Technical breakdown detail */}
        {Object.keys(score.website.technical_breakdown).length > 0 && (
          <TechnicalDetail breakdown={score.website.technical_breakdown} />
        )}

        {/* Action items */}
        <ActionItems items={score.action_items} />

        {/* Footer */}
        <div className="text-center text-xs text-gray-600 pb-4">
          Built by <a href="https://channellab.tw" className="hover:text-gray-400">ChannelLab</a>
        </div>
      </div>
    </main>
  );
}

function TechnicalDetail({ breakdown }: { breakdown: Record<string, { status: string; score: number; detail: string }> }) {
  const STATUS_ICON: Record<string, string> = { PASS: "✅", WARN: "⚠️", FAIL: "❌" };

  return (
    <div className="bg-gray-800 rounded-2xl p-6">
      <h3 className="text-base font-semibold text-gray-300 mb-4">技術審查明細</h3>
      <div className="space-y-2">
        {Object.entries(breakdown).map(([name, check]) => (
          <div key={name} className="flex items-start gap-3 py-2 border-b border-gray-700/50 last:border-0">
            <span className="text-base mt-0.5 shrink-0">{STATUS_ICON[check.status] ?? "❓"}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-300">{name}</p>
              <p className="text-xs text-gray-500 mt-0.5 truncate">{check.detail}</p>
            </div>
            <span className="text-xs font-semibold shrink-0" style={{ color: check.score >= 50 ? "#34D399" : "#F87171" }}>
              {check.score}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
