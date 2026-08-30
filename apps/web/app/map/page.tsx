import { Train } from "lucide-react";
import Link from "next/link";

export default function MapPage() {
  return (
    <main className="bg-mesh flex min-h-screen flex-col items-center justify-center gap-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600/20">
        <Train className="h-7 w-7 text-indigo-400" />
      </div>
      <h1 className="text-3xl font-bold text-white">Live Train Map</h1>
      <p className="text-gray-500">
        Coming in <span className="text-indigo-400">Phase 2</span>
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
