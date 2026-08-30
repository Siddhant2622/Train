/**
 * Placeholder pages for Phase 1+ routes.
 * These exist so navigation links don't 404.
 * They will be replaced with real implementations in their respective phases.
 */

import { Train } from "lucide-react";
import Link from "next/link";

function ComingSoon({ title, phase }: { title: string; phase: string }) {
  return (
    <main className="bg-mesh flex min-h-screen flex-col items-center justify-center gap-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600/20">
        <Train className="h-7 w-7 text-indigo-400" />
      </div>
      <h1 className="text-3xl font-bold text-white">{title}</h1>
      <p className="text-gray-500">
        Coming in <span className="text-indigo-400">{phase}</span>
      </p>
      <Link
        href="/"
        className="rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm text-gray-300 transition hover:bg-white/10"
      >
        ← Back to Home
      </Link>
    </main>
  );
}

export default function DashboardPage() {
  return <ComingSoon title="Control Room" phase="Phase 2" />;
}
