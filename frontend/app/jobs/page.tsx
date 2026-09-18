"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import WhyThisJob from "@/components/WhyThisJob";
import { api, getToken, Job } from "@/lib/api";

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [minMatch, setMinMatch] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function load() {
    const params = new URLSearchParams();
    if (role) params.set("role", role);
    if (company) params.set("company", company);
    if (minMatch) params.set("min_match", minMatch);
    if (remoteOnly) params.set("remote", "true");
    const data = await api<Job[]>(`/api/jobs?${params}`);
    setJobs(data);
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load().catch((e) => setError(String(e.message || e)));
  }, [router]);

  async function discover() {
    setBusy(true);
    setError("");
    try {
      await api("/api/jobs/discover", { method: "POST", body: "{}" });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function matchAndPrepare(jobId: string) {
    setBusy(true);
    setError("");
    try {
      await api(`/api/jobs/${jobId}/match`, { method: "POST" });
      await api("/api/outreach/prepare", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, use_llm: false }),
      });
      router.push("/outreach");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Job feed</h1>
          <p className="text-sm text-slate-500">
            Public sources only (Greenhouse/Lever). No CAPTCHA/auth bypass.
          </p>
        </div>
        <button
          onClick={discover}
          disabled={busy}
          className="rounded-lg bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {busy ? "Working…" : "Discover jobs"}
        </button>
      </div>

      <div className="grid gap-2 rounded-xl border border-slate-200 bg-white p-3 sm:grid-cols-4">
        <input
          placeholder="Role filter"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        />
        <input
          placeholder="Company"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
        />
        <input
          placeholder="Min match %"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={minMatch}
          onChange={(e) => setMinMatch(e.target.value)}
        />
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.target.checked)} />
            Remote
          </label>
          <button
            onClick={() => load().catch((e) => setError(String(e.message || e)))}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50"
          >
            Apply
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      <div className="space-y-3">
        {jobs.length === 0 && (
          <p className="text-sm text-slate-500">No jobs yet — click Discover jobs (needs network for Greenhouse boards).</p>
        )}
        {jobs.map((j) => (
          <div key={j.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="font-medium">{j.job_title}</div>
                <div className="text-sm text-slate-500">
                  {j.company_name} · {j.location || "—"} · {j.employment_type}
                  {j.is_remote ? " · Remote" : ""} · {j.source}
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-semibold text-brand-700">
                  {j.match_score != null ? `${Math.round(j.match_score)}%` : "—"}
                </div>
                <div className="text-xs text-slate-400">match</div>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <a
                href={j.job_url}
                target="_blank"
                rel="noreferrer"
                className="rounded-md border border-slate-200 px-2.5 py-1 text-xs hover:bg-slate-50"
              >
                View job
              </a>
              <button
                className="rounded-md border border-slate-200 px-2.5 py-1 text-xs hover:bg-slate-50"
                onClick={() => setExpanded(expanded === j.id ? null : j.id)}
              >
                Why this job?
              </button>
              <button
                className="rounded-md bg-brand-600 px-2.5 py-1 text-xs text-white hover:bg-brand-700"
                onClick={() => matchAndPrepare(j.id)}
                disabled={busy}
              >
                Match & prepare outreach
              </button>
            </div>
            {expanded === j.id && (
              <div className="mt-3">
                <WhyThisJob why={j.why_this_job} />
                {!j.why_this_job && (
                  <p className="text-xs text-slate-500">Run match first to populate evidence-backed reasons.</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
