"use client";

import { motion } from "motion/react";
import { OglBackground } from "@/components/ogl-background";

type AuthShellProps = {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
};

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <main className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden px-4 py-16">
      <OglBackground />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(99,102,241,0.28),transparent_48%),radial-gradient(circle_at_80%_70%,rgba(14,165,233,0.18),transparent_45%)]" />

      <motion.section
        initial={{ opacity: 0, y: 28, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.55, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md rounded-2xl border border-white/20 bg-slate-950/65 p-7 shadow-2xl shadow-indigo-950/40 backdrop-blur-xl"
      >
        <div className="mb-6">
          <p className="inline-block rounded-full border border-indigo-300/40 bg-indigo-500/20 px-3 py-1 text-xs font-medium text-indigo-100">
            AI Knowledge Platform
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">{title}</h1>
          <p className="mt-2 text-sm text-slate-300">{subtitle}</p>
        </div>
        {children}
        <div className="mt-5 text-sm text-slate-300">{footer}</div>
      </motion.section>
    </main>
  );
}

