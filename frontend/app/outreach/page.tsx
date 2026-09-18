"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken, Outreach } from "@/lib/api";

export default function OutreachPage() {
  const router = useRouter();
  const [items, setItems] = useState<Outreach[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [active, setActive] = useState<Outreach | null>(null);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const data = await api<Outreach[]>("/api/outreach");
    setItems(data);
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load().catch((e) => setError(String(e.message || e)));
  }, [router]);

  function open(o: Outreach) {
    setActive(o);
    setEditSubject(o.subject);
    setEditBody(o.body);
  }

  async function act(path: string, method = "POST") {
    if (!active) return;
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const updated = await api<Outreach>(`/api/outreach/${active.id}${path}`, { method });
      setActive(updated);
      setInfo(`Status: ${updated.status}`);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function saveEdits() {
    if (!active) return;
    setBusy(true);
    try {
      const updated = await api<Outreach>(`/api/outreach/${active.id}`, {
        method: "PATCH",
        body: JSON.stringify({ subject: editSubject, body: editBody }),
      });
      setActive(updated);
      setInfo("Edits saved; QC re-checked");
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function bulkApprove() {
    const ids = Object.entries(selected).filter(([, v]) => v).map(([k]) => k);
    if (!ids.length) {
      setError("Select messages explicitly before bulk approve");
      return;
    }
    setBusy(true);
    try {
      await api("/api/outreach/bulk-approve", {
        method: "POST",
        body: JSON.stringify({ message_ids: ids }),
      });
      setInfo(`Bulk approve attempted for ${ids.length} messages`);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Outreach review</h1>
          <p className="text-sm text-slate-500">
            Human approval required. Never auto-send. No verified contact → application URL fallback.
          </p>
        </div>
        <button
          onClick={bulkApprove}
          disabled={busy}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:bg-slate-50"
        >
          Bulk approve selected
        </button>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      {info && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{info}</div>}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2"></th>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Recruiter</th>
              <th className="px-3 py-2">Match</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((o) => (
              <tr
                key={o.id}
                className="cursor-pointer border-b hover:bg-slate-50"
                onClick={() => open(o)}
              >
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={!!selected[o.id]}
                    onChange={(e) => setSelected({ ...selected, [o.id]: e.target.checked })}
                  />
                </td>
                <td className="px-3 py-2">{o.company_name}</td>
                <td className="px-3 py-2">{o.role}</td>
                <td className="px-3 py-2">
                  {o.recruiter_name || "—"}
                  {o.recruiter_confidence ? ` (${o.recruiter_confidence})` : ""}
                </td>
                <td className="px-3 py-2">{o.match_score != null ? `${Math.round(o.match_score)}%` : "—"}</td>
                <td className="px-3 py-2">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{o.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <p className="p-4 text-sm text-slate-500">No outreach yet. Prepare from the Jobs page.</p>
        )}
      </div>

      {active && (
        <div className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:grid-cols-2">
          <div className="space-y-3">
            <h2 className="font-semibold">
              {active.company_name} — {active.role}
            </h2>
            <div className="text-xs text-slate-500">
              QC: {active.qc_verified ? "verified" : "blocked"}{" "}
              {active.qc_issues?.length ? `— ${active.qc_issues.join("; ")}` : ""}
            </div>
            {!active.recipient_email && active.fallback_application_url && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                No verified public contact. Apply via official URL:{" "}
                <a className="underline" href={active.fallback_application_url} target="_blank" rel="noreferrer">
                  {active.fallback_application_url}
                </a>
              </div>
            )}
            <label className="block text-sm">
              Subject
              <input
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                value={editSubject}
                onChange={(e) => setEditSubject(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              Email body
              <textarea
                className="mt-1 h-64 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button onClick={saveEdits} disabled={busy} className="rounded-lg border px-3 py-1.5 text-sm">
                Edit / Save
              </button>
              <button onClick={() => act("/approve")} disabled={busy} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm text-white">
                Approve
              </button>
              <button
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    if (active && active.status !== "approved") {
                      await api(`/api/outreach/${active.id}/approve`, { method: "POST" });
                    }
                    if (active) {
                      const updated = await api<Outreach>(`/api/outreach/${active.id}/send?provider=noop`, { method: "POST" });
                      setActive(updated);
                      setInfo(`Sent (provider may be no-op): ${updated.status}`);
                      await load();
                    }
                  } catch (e: unknown) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setBusy(false);
                  }
                }}
                disabled={busy}
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm text-white"
              >
                Approve & Send (noop if OAuth unset)
              </button>
              <button onClick={() => act("/reject")} disabled={busy} className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-700">
                Reject
              </button>
              <button onClick={() => act("/save")} disabled={busy} className="rounded-lg border px-3 py-1.5 text-sm">
                Save for later
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Send requires prior Approve when require_manual_approval=true. Gmail/Outlook send is a safe no-op until OAuth keys are set.
            </p>
          </div>
          <div className="space-y-3 text-sm">
            <div>
              <div className="font-medium">Personalization</div>
              <pre className="mt-1 overflow-auto rounded-lg bg-slate-50 p-3 text-xs">
                {JSON.stringify(active.personalization, null, 2)}
              </pre>
            </div>
            <div>
              <div className="text-xs text-slate-500">Recipient</div>
              <div>{active.recipient_email || "(none — application URL fallback)"}</div>
            </div>
            {active.resume_version_id && (
              <a className="text-brand-600 underline" href="/resumes">
                View tailored resume versions →
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
