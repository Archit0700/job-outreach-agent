const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type Metrics = {
  jobs_found: number;
  relevant_jobs: number;
  emails_approved: number;
  emails_sent: number;
  responses: number;
  interviews: number;
  pending_reviews: number;
  followups: number;
  rejected: number;
};

export type Job = {
  id: string;
  company_id: string;
  company_name?: string;
  job_title: string;
  location: string;
  employment_type: string;
  job_url: string;
  application_url: string;
  source: string;
  description: string;
  is_remote: boolean;
  match_score?: number | null;
  why_this_job?: {
    matches?: { item: string; reason: string }[];
    gaps?: { item: string; reason: string }[];
  } | null;
};

export type Outreach = {
  id: string;
  job_id: string;
  company_name?: string;
  role?: string;
  subject: string;
  body: string;
  status: string;
  recipient_email?: string | null;
  recruiter_name?: string | null;
  recruiter_confidence?: string | null;
  match_score?: number | null;
  qc_verified: boolean;
  qc_issues: string[];
  personalization: Record<string, unknown>;
  fallback_application_url?: string | null;
  resume_version_id?: string | null;
  sent_at?: string | null;
};

export type ResumeVersion = {
  id: string;
  job_id?: string | null;
  plain_text: string;
  diff: Record<string, unknown>;
  qc_passed: boolean;
  qc_issues: string[];
  content: Record<string, unknown>;
};
