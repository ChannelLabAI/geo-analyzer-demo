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

export interface BrandGEOScore {
  brand: string;
  url: string;
  website: WebsiteScore;
  overall_score: number;
  grade: "A" | "B" | "C" | "D" | "F";
  grade_label: string;
  data_confidence: "low" | "medium" | "high";
  action_items: ActionItem[];
  generated_at: string;
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
