"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken, getToken } from "@/lib/api";
import { useEffect, useState } from "react";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/onboarding", label: "Onboarding" },
  { href: "/jobs", label: "Jobs" },
  { href: "/outreach", label: "Outreach" },
  { href: "/resumes", label: "Resumes" },
  { href: "/settings", label: "Settings" },
];

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(!!getToken());
  }, [pathname]);

  function logout() {
    clearToken();
    setAuthed(false);
    router.push("/login");
  }

  return (
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-40">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="font-semibold text-brand-700">
          Job Outreach Agent
        </Link>
        <nav className="flex flex-wrap items-center gap-1 text-sm">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-md px-3 py-1.5 ${
                pathname === l.href
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {l.label}
            </Link>
          ))}
          {authed ? (
            <button
              onClick={logout}
              className="ml-2 rounded-md px-3 py-1.5 text-slate-500 hover:bg-slate-50"
            >
              Log out
            </button>
          ) : (
            <Link href="/login" className="ml-2 rounded-md bg-brand-600 px-3 py-1.5 text-white">
              Log in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
