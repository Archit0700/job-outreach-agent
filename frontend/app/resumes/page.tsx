"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, ResumeVersion } from "@/lib/api";

export default function ResumesPage() {
  const router = useRouter();
  const [versions, setVersions] = useState<ResumeVersion[]>([]);
  const [active, setActive] = useState<ResumeVersion | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<ResumeVersion[]>("/api/resume-versions")
      .then(setVersions)
      .catch((e) => setError(String(e.message || e)));
  }, [router]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Resume versions</h1>
      <p className="text-sm text-slate-500">
        Every tailored resume is stored with a diff. Fabrication is blocked by the QC gate.
      </p>
      {error && <div className="text-sm text-red-600">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          {versions.map((v) => (
            <button
              key={v.id}
              onClick={() => setActive(v)}
              className="block w-full rounded-xl border border-slate-200 bg-white p-3 text-left text-sm hover:bg-slate-50"
            >
              <div className="font-medium">Version {v.id.slice(0, 8)}</div>
              <div className="text-xs text-slate-500">
                Job: {v.job_id || "—"} · QC {v.qc_passed ? "passed" : "failed"}
              </div>
            </button>
          ))}
          {versions.length === 0 && <p className="text-sm text-slate-500">No tailored versions yet.</p>}
        </div>
        {active && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="font-medium">Diff</div>
            <pre className="mt-2 max-h-40 overflow-auto rounded bg-slate-50 p-2 text-xs">
              {JSON.stringify(active.diff, null, 2)}
            </pre>
            <div className="mt-4 font-medium">Tailored text</div>
            <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">
              {active.plain_text}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
