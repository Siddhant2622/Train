"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Train, LayoutDashboard, Map, Activity } from "lucide-react";
import { useApiStatus } from "@/hooks/useApiStatus";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/map", label: "Live Map", icon: Map },
];

export default function Nav() {
  const pathname = usePathname();
  const { status, isLoading, data } = useApiStatus();
  const isOnline = status === "success" && data?.status === "ok";

  return (
    <nav className="nav">
      <Link href="/" className="nav-logo" id="nav-logo">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600">
          <Train className="h-4 w-4 text-white" />
        </div>
        RailPredict AI
      </Link>

      <div className="nav-links">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`nav-link ${pathname.startsWith(href) ? "active" : ""}`}
          >
            <span className="flex items-center gap-1.5">
              <Icon className="h-3.5 w-3.5" />
              {label}
            </span>
          </Link>
        ))}
      </div>

      <div className="nav-spacer" />

      {!isLoading && (
        <span className={`status-badge ${isOnline ? "online" : "offline"}`} id="api-status-badge">
          <span className={`status-dot ${isOnline ? "online" : "offline"}`} />
          {isOnline ? "API Online" : "API Offline"}
        </span>
      )}
    </nav>
  );
}
