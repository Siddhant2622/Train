"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await auth.login(email, password);
      localStorage.setItem("access_token", response.access_token);
      router.push("/control");
    } catch (err: any) {
      setError(err.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-gray-950 p-4">
      <div className="w-full max-w-md rounded-xl border border-gray-800 bg-gray-900 p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white">Railway Block</h1>
          <p className="mt-2 text-sm text-gray-400">Control Room Access</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {error && (
            <div className="rounded-lg bg-red-900/50 p-3 text-sm text-red-200 border border-red-800/50">
              {error}
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Email
            </label>
            <input
              type="email"
              required
              className="w-full rounded-lg border border-gray-700 bg-gray-950 p-3 text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@railwayblock.local"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Password
            </label>
            <input
              type="password"
              required
              className="w-full rounded-lg border border-gray-700 bg-gray-950 p-3 text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-lg bg-blue-600 p-3 font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
          >
            {loading ? "Authenticating..." : "Login"}
          </button>
        </form>
      </div>
    </div>
  );
}
