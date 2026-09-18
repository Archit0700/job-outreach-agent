type Why = {
  matches?: { item: string; reason: string }[];
  gaps?: { item: string; reason: string }[];
} | null | undefined;

export default function WhyThisJob({ why }: { why: Why }) {
  if (!why) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
      <div className="font-medium text-slate-800">Why this job matches you</div>
      <ul className="mt-2 space-y-1">
        {(why.matches || []).map((m, i) => (
          <li key={i} className="text-emerald-700">
            ✓ {m.item} — {m.reason}
          </li>
        ))}
      </ul>
      {(why.gaps || []).length > 0 && (
        <>
          <div className="mt-3 font-medium text-slate-800">Potential gaps</div>
          <ul className="mt-1 space-y-1">
            {why.gaps!.map((g, i) => (
              <li key={i} className="text-amber-700">
                △ {g.item} — {g.reason}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
