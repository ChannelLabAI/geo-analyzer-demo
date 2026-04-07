"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { API_BASE } from "@/lib/types";

export default function LandingPage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [brand, setBrand] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const params = new URLSearchParams({ url, brand });
      const res = await fetch(`${API_BASE}/api/brand-score?${params}`, { method: "POST" });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error ?? `伺服器錯誤 (${res.status})`);
        return;
      }

      router.push(`/result/${data.job_id}`);
    } catch {
      setError("連線失敗，請確認伺服器是否運行中。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-12 max-w-2xl">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
          Brand GEO Score
        </h1>
        <p className="text-lg text-gray-400">
          測量你的品牌在 AI 搜尋平台的可見度。
          輸入網站 URL 取得 0-100 分的綜合評分。
        </p>
      </div>

      {/* Form card */}
      <div className="w-full max-w-lg bg-gray-800 rounded-2xl p-8 shadow-xl">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-300 mb-1.5">
              網站 URL
            </label>
            <input
              id="url"
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://yoursite.com"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
            />
          </div>

          <div>
            <label htmlFor="brand" className="block text-sm font-medium text-gray-300 mb-1.5">
              品牌名稱
            </label>
            <input
              id="brand"
              type="text"
              required
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="例：HubSpot"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
            />
          </div>

          {error && (
            <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg px-6 py-3.5 text-white font-semibold transition-colors"
          >
            {loading ? "送出中..." : "開始分析"}
          </button>
        </form>

        <p className="text-xs text-gray-500 text-center mt-4">
          分析需要約 30-60 秒。結果包含技術面、內容面、權威面評分。
        </p>
      </div>

      {/* Feature hints */}
      <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-2xl">
        {[
          { icon: "⚙️", label: "技術審查", desc: "robots.txt、llms.txt、Schema 標記" },
          { icon: "📝", label: "內容分析", desc: "AI 可引用性、結構、新鮮度" },
          { icon: "🏆", label: "權威評估", desc: "Open PageRank + AI 引用次數" },
        ].map(({ icon, label, desc }) => (
          <div key={label} className="bg-gray-800/60 rounded-xl p-4 text-center">
            <div className="text-2xl mb-2">{icon}</div>
            <p className="text-sm font-medium text-gray-300">{label}</p>
            <p className="text-xs text-gray-500 mt-1">{desc}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
