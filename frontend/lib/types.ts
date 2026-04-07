// Types matching BrandGEOScore.to_dict() output from geo-analyzer

export interface WebsiteScore {
  url: string;
  technical_score: number;
  content_score: number;
  authority_score: number;
  traditional_authority: number;
  ai_authority: number;
  overall_score: number;
  technical_breakdown: Record<string, { status: string; score: number; detail: string }>;
  content_breakdown: Record<string, number>;
}

export interface ActionItem {
  title: string;
  description: string;
  estimated_score_gain: number;
  difficulty: "easy" | "medium" | "hard";
  estimated_hours: string;
  category: string;
}

// Phase 2: Channel types
export interface PlatformDetail {
  platform: string;
  channel_type: string;
  content_count: number;
  ai_citation_rate: number;
  platform_weight: number;
  sentiment_score: number;
  error: string | null;
}

export interface MediaScore {
  overall_score: number;
  content_count_score: number;
  citation_hit_rate_score: number;
  platform_weight_score: number;
  data_confidence: "low" | "medium" | "high";
  platforms: PlatformDetail[];
}

export interface SocialScore {
  overall_score: number;
  discussion_frequency_score: number;
  citation_hit_rate_score: number;
  sentiment_score: number;
  data_confidence: "low" | "medium" | "high";
  platforms: PlatformDetail[];
}

export interface CrossChannelAnalysis {
  channel_contribution: Record<string, number>;
  top_sources: string[];
  source_channel_map: Record<string, string>;
}

export interface FullChannelScore {
  website_score: number;
  media_score: number | null;
  social_score: number | null;
  authority_score: number;
  overall_score: number;
  media_available: boolean;
  social_available: boolean;
  cross_analysis: CrossChannelAnalysis;
}

export interface SourceRow {
  engine: string;
  available: boolean;
  channels: { website: number; media: number; social: number };
  overall: number;
}

export interface BrandGEOScore {
  brand: string;
  url: string;
  website: WebsiteScore;
  overall_score: number;           // Phase 1 compat: website score
  grade: "A" | "B" | "C" | "D" | "F";
  grade_label: string;
  data_confidence: "low" | "medium" | "high";
  action_items: ActionItem[];
  generated_at: string;
  estimated_after_top3: number;
  // Phase 2 fields (optional — absent when running website-only mode)
  full_channel_score?: number;
  full_channel?: FullChannelScore;
  media?: MediaScore | null;
  social?: SocialScore | null;
}

export type JobStatus = "pending" | "running" | "done" | "error";

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  result: BrandGEOScore | null;
  error: string | null;
  estimated_total: number;
}

export const GRADE_COLORS: Record<string, string> = {
  A: "#22C55E",
  B: "#3B82F6",
  C: "#F59E0B",
  D: "#F97316",
  F: "#EF4444",
};

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// Phase 2: Channel colors
export const CHANNEL_COLORS = {
  web:    "#3B82F6",  // Blue 500
  media:  "#F59E0B",  // Amber 500
  social: "#EC4899",  // Pink 500
  auth:   "#A78BFA",  // Violet 400
} as const;

// Semi-transparent fills for radar chart
export const CHANNEL_FILLS = {
  web:    "rgba(59, 130, 246, 0.15)",
  media:  "rgba(245, 158, 11, 0.15)",
  social: "rgba(236, 72, 153, 0.15)",
  auth:   "rgba(167, 139, 250, 0.15)",
} as const;
