"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import StatCard from "@/components/StatCard";
import { api, getToken, Metrics } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<Metrics>("/api/metrics")
      .then(setMetrics)
      .catch((e) => setError(String(e.message || e)));
  }, [router]);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Overview</h1>
          <p className="text-sm text-slate-500">
            Accuracy + relevance + personalization + your approval — never auto-send.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/onboarding"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:bg-slate-50"
          >
            Onboarding
          </Link>
          <Link
            href="/jobs"
            className="rounded-lg bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700"
          >
            Job feed
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Relevant Jobs" value={metrics?.relevant_jobs ?? "—"} />
        <StatCard label="Pending Reviews" value={metrics?.pending_reviews ?? "—"} />
        <StatCard label="Emails Sent" value={metrics?.emails_sent ?? "—"} />
        <StatCard label="Responses" value={metrics?.responses ?? "—"} />
        <StatCard label="Interviews" value={metrics?.interviews ?? "—"} />
        <StatCard label="Jobs Found" value={metrics?.jobs_found ?? "—"} />
        <StatCard label="Approved" value={metrics?.emails_approved ?? "—"} />
        <StatCard label="Follow-ups" value={metrics?.followups ?? "—"} />
      </div>
    </div>
  );
}
