"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { motion } from "motion/react";
import Avatar from "react-avatar";
import {
  BarChart3,
  FileOutput,
  FileSpreadsheet,
  FileText,
  Files,
  History,
  LayoutDashboard,
  LogOut,
  MessageCircle,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageCircle },
  { href: "/documents", label: "Documents", icon: Files },
  { href: "/prompts", label: "Prompts", icon: FileText },
  { href: "/conversations", label: "Conversations", icon: History },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/report-generation", label: "Report Generation", icon: FileOutput },
  { href: "/export-data", label: "Export Data", icon: FileSpreadsheet },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [isNavCollapsed, setIsNavCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem("app-nav-collapsed") === "true";
  });
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname || "/dashboard")}`);
    }
  }, [isAuthenticated, isLoading, router, pathname]);

  useEffect(() => {
    window.localStorage.setItem("app-nav-collapsed", String(isNavCollapsed));
  }, [isNavCollapsed]);

  if (!mounted || isLoading || !isAuthenticated) {
    return (
      <main className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden bg-slate-950 px-4 py-16">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.26),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.2),transparent_45%)]" />
        <div className="relative flex flex-col items-center gap-4">
          <div className="relative grid h-16 w-16 place-items-center">
            <motion.span
              className="absolute h-16 w-16 rounded-full border border-cyan-300/35"
              animate={{ scale: [1, 1.25], opacity: [0.8, 0] }}
              transition={{ duration: 1.4, repeat: Number.POSITIVE_INFINITY, ease: "easeOut" }}
            />
            <motion.span
              className="absolute h-12 w-12 rounded-full border border-indigo-300/45"
              animate={{ scale: [1, 1.2], opacity: [0.9, 0] }}
              transition={{
                duration: 1.4,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeOut",
                delay: 0.2,
              }}
            />
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
              className="h-8 w-8 rounded-full border-2 border-indigo-300/30 border-t-cyan-300"
            />
          </div>
          <p className="text-sm text-slate-200">Preparing your workspace...</p>
          <p className="text-xs text-slate-400">Loading authentication and settings</p>
        </div>
      </main>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.26),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.2),transparent_45%)]" />
      <div className="relative min-h-screen w-full max-w-none">
        <aside
          className={`fixed left-0 top-0 z-30 hidden h-screen shrink-0 border-r border-white/10 bg-slate-950/85 p-3 backdrop-blur-xl transition-all duration-300 lg:flex lg:flex-col ${
            isNavCollapsed ? "w-20" : "w-64"
          }`}
        >
          <div className="mb-5 flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Avatar name="AI User" size="28" round textSizeRatio={2} color="#06b6d4" fgColor="#ffffff" />
                {!isNavCollapsed ? (
                  <div>
                    <h1 className="text-sm font-semibold text-white">AI Knowledge Platform</h1>
                    <p className="text-[11px] text-slate-300">Professional Next.js Experience</p>
                  </div>
                ) : null}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsNavCollapsed((prev) => !prev)}
              className="rounded-md border border-white/15 bg-white/5 px-2 py-1 text-xs text-slate-200 hover:bg-white/10"
              title={isNavCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isNavCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </button>
          </div>

          <nav className="flex-1 space-y-2 text-sm">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={item.label}
                  className={`flex items-center rounded-lg px-3 py-2.5 transition ${
                    active ? "bg-white/15 text-white" : "text-slate-200 hover:bg-white/10"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isNavCollapsed ? "mx-auto" : "mr-2.5"}`} />
                  {!isNavCollapsed ? item.label : null}
                </Link>
              );
            })}
          </nav>

          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="mt-4 flex items-center justify-center rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-3 py-2.5 text-sm font-medium text-white hover:brightness-110"
          >
            <LogOut className={`h-4 w-4 ${isNavCollapsed ? "" : "mr-2"}`} />
            {!isNavCollapsed ? "Logout" : null}
          </motion.button>
        </aside>

        <div
          className={`flex min-w-0 flex-1 flex-col transition-all duration-300 ${
            isNavCollapsed ? "lg:ml-20" : "lg:ml-64"
          }`}
        >
          <header className="border-b border-white/10 bg-slate-950/70 px-3 py-4 backdrop-blur-xl lg:hidden">
            <h1 className="text-lg font-semibold text-white">AI Knowledge Platform</h1>
            <p className="text-xs text-slate-300">Use a larger screen to see left sidebar navigation.</p>
          </header>
          <main className="w-full px-3 py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}

