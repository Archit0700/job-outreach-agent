"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";

const DEFAULT_ROLES = [
  "Software Engineer",
  "SDE",
  "Backend Engineer",
  "Full Stack Engineer",
  "ML Engineer",
  "AI Engineer",
  "Android Developer",
];
const DEFAULT_LOCATIONS = [
  "India",
  "Bengaluru",
  "Delhi NCR",
  "Hyderabad",
  "Pune",
  "Mumbai",
  "Remote",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [roles, setRoles] = useState(DEFAULT_ROLES.join("\n"));
  const [locations, setLocations] = useState(DEFAULT_LOCATIONS.join("\n"));
  const [employment, setEmployment] = useState("internship,full_time");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMsg("");
    try {
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        await api("/api/resumes/upload", { method: "POST", body: fd });
      }
      await api("/api/settings", {
        method: "PATCH",
        body: JSON.stringify({
          target_roles: roles.split("\n").map((s) => s.trim()).filter(Boolean),
          preferred_locations: locations.split("\n").map((s) => s.trim()).filter(Boolean),
          employment_types: employment.split(",").map((s) => s.trim()).filter(Boolean),
          experience_level: "entry_level",
          require_manual_approval: true,
        }),
      });
      setMsg("Saved. Resume parsed into candidate profile (no fabrication).");
      router.push("/jobs");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Onboarding</h1>
      <p className="text-sm text-slate-500">
        Upload your master resume and set preferences. The system extracts evidence-backed skills only.
      </p>
      <form onSubmit={submit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="block text-sm">
          Master resume (PDF / DOCX / TXT)
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            className="mt-1 block w-full text-sm"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>
        <label className="block text-sm">
          Target roles (one per line)
          <textarea
            className="mt-1 h-32 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            value={roles}
            onChange={(e) => setRoles(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          Preferred locations
          <textarea
            className="mt-1 h-32 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            value={locations}
            onChange={(e) => setLocations(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          Employment types (comma-separated)
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={employment}
            onChange={(e) => setEmployment(e.target.value)}
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {msg && <p className="text-sm text-emerald-700">{msg}</p>}
        <button
          disabled={busy}
          className="rounded-lg bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {busy ? "Saving…" : "Save & continue"}
        </button>
      </form>
    </div>
  );
}
