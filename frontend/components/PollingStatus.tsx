"use client";

interface Props {
  status: "pending" | "running" | "error";
  progress: number;
  estimatedTotal: number;
  error?: string | null;
  elapsedSeconds: number;
}

export function PollingStatus({ status, progress, estimatedTotal, error, elapsedSeconds }: Props) {
  if (status === "error") {
    return (
      <div className="flex flex-col items-center gap-4 py-16">
        <div className="text-5xl">❌</div>
        <p className="text-xl font-semibold text-red-400">分析失敗</p>
        <p className="text-sm text-gray-400 max-w-md text-center">{error ?? "未知錯誤"}</p>
        <a href="/" className="mt-4 px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">
          重新分析
        </a>
      </div>
    );
  }

  const displayProgress = progress > 0 ? progress : Math.min(95, Math.round((elapsedSeconds / estimatedTotal) * 100));
  const remaining = Math.max(0, Math.round(estimatedTotal - elapsedSeconds));

  return (
    <div className="flex flex-col items-center gap-6 py-16">
      {/* Spinner */}
      <div className="relative w-20 h-20">
        <div className="absolute inset-0 rounded-full border-4 border-gray-700" />
        <div className="absolute inset-0 rounded-full border-4 border-blue-500 border-t-transparent animate-spin" />
      </div>

      <div className="text-center">
        <p className="text-xl font-semibold text-white">
          {status === "pending" ? "正在啟動分析..." : "AI 可見度分析中..."}
        </p>
        <p className="text-sm text-gray-400 mt-1">
          {remaining > 0 ? `預計剩餘 ${remaining} 秒` : "即將完成..."}
        </p>
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-sm">
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-1000"
            style={{ width: `${displayProgress}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>技術審查 + 內容分析 + 權威評估</span>
          <span>{displayProgress}%</span>
        </div>
      </div>
    </div>
  );
}
