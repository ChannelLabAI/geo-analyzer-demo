import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  weight: ["400", "600", "700"],
});

export const metadata: Metadata = {
  title: "GEO Dashboard — Brand AI Visibility Score",
  description: "Measure your brand's AI search visibility with a unified 0-100 Brand GEO Score.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-TW">
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased bg-surface text-slate-100 min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
