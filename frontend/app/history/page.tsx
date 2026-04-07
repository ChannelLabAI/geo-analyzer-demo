// History page — Phase 1 skeleton
// Full implementation in Phase 2: persistent storage, trend charts, brand comparison

import Link from "next/link";

export default function HistoryPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-lg bg-gray-800 rounded-2xl p-10 text-center">
        <div className="text-5xl mb-4">📊</div>
        <h1 className="text-2xl font-bold text-white mb-2">歷史分析</h1>
        <p className="text-gray-400 mb-6">
          歷史紀錄和趨勢圖表將在 Phase 2 上線。
          <br />
          目前每次分析結果保存 30 分鐘，可透過分析結果頁面 URL 分享。
        </p>
        <Link
          href="/"
          className="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white font-semibold transition-colors"
        >
          開始新分析
        </Link>
      </div>
    </main>
  );
}
