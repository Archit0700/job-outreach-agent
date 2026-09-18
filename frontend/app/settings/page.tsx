"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";

type Settings = {
  target_roles: string[];
  preferred_locations: string[];
  max_emails_per_day: number;
  per_company_send_limit: number;
  require_manual_approval: boolean;
  followups_enabled: boolean;
  target_companies: string[];
};

export default function SettingsPage() {
  const router = useRouter();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [gmail, setGmail] = useState<{ configured: boolean; authorize_url?: string; message?: string } | null>(null);
  const [ms, setMs] = useState<{ configured: boolean; authorize_url?: string; message?: string } | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<Settings>("/api/settings")
      .then(setSettings)
      .catch((e) => setError(String(e.message || e)));
    api<typeof gmail>("/api/oauth/gmail/start").then(setGmail).catch(() => null);
    api<typeof ms>("/api/oauth/microsoft/start").then(setMs).catch(() => null);
  }, [router]);

  async function save() {
    if (!settings) return;
    try {
      const updated = await api<Settings>("/api/settings", {
        method: "PATCH",
        body: JSON.stringify(settings),
      });
      setSettings(updated);
      setMsg("Settings saved");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  if (!settings) {
    return <p className="text-sm text-slate-500">{error || "Loading…"}</p>;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <label className="flex items-center justify-between text-sm">
          Require manual approval before send
          <input
            type="checkbox"
            checked={settings.require_manual_approval}
            onChange={(e) => setSettings({ ...settings, require_manual_approval: e.target.checked })}
          />
        </label>
        <label className="flex items-center justify-between text-sm">
          Enable follow-ups (opt-in)
          <input
            type="checkbox"
            checked={settings.followups_enabled}
            onChange={(e) => setSettings({ ...settings, followups_enabled: e.target.checked })}
          />
        </label>
        <label className="block text-sm">
          Max emails / day
          <input
            type="number"
            className="mt-1 w-full rounded-lg border px-3 py-2"
            value={settings.max_emails_per_day}
            onChange={(e) => setSettings({ ...settings, max_emails_per_day: Number(e.target.value) })}
          />
        </label>
        <label className="block text-sm">
          Per-company send limit
          <input
            type="number"
            className="mt-1 w-full rounded-lg border px-3 py-2"
            value={settings.per_company_send_limit}
            onChange={(e) => setSettings({ ...settings, per_company_send_limit: Number(e.target.value) })}
          />
        </label>
        <button onClick={save} className="rounded-lg bg-brand-600 px-4 py-2 text-sm text-white">
          Save
        </button>
        {msg && <p className="text-sm text-emerald-700">{msg}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-medium">Email sending OAuth</h2>
        <p className="text-sm text-slate-500">
          Until configured, send uses a safe no-op that records the event without delivering mail.
        </p>
        <div className="text-sm">
          <div className="font-medium">Gmail</div>
          {gmail?.configured && gmail.authorize_url ? (
            <a className="text-brand-600 underline" href={gmail.authorize_url}>
              Connect Gmail
            </a>
          ) : (
            <p className="text-slate-500">{gmail?.message || "Not configured"}</p>
          )}
        </div>
        <div className="text-sm">
          <div className="font-medium">Microsoft / Outlook</div>
          {ms?.configured && ms.authorize_url ? (
            <a className="text-brand-600 underline" href={ms.authorize_url}>
              Connect Microsoft
            </a>
          ) : (
            <p className="text-slate-500">{ms?.message || "Not configured"}</p>
          )}
        </div>
      </div>
    </div>
  );
}
