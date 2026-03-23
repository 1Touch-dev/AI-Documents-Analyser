"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { OglBackground } from "@/components/ogl-background";

const features = [
  {
    title: "Multi-LLM Intelligence",
    desc: "Run document analysis with local and cloud models, with model routing and source-grounded responses.",
  },
  {
    title: "Secure Document Workflows",
    desc: "Upload, index, and query enterprise files with auth-ready architecture and scalable API layers.",
  },
  {
    title: "Analytics and Reporting",
    desc: "Convert raw documents into dashboards, financial insights, and export-ready intelligence outputs.",
  },
];

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden text-slate-100">
      <OglBackground />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_10%_15%,rgba(99,102,241,0.28),transparent_40%),radial-gradient(circle_at_90%_80%,rgba(14,165,233,0.22),transparent_45%)]" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-8">
        <header className="flex items-center justify-between rounded-xl border border-white/15 bg-slate-950/55 px-4 py-3 backdrop-blur-xl">
          <p className="text-sm font-medium tracking-wide text-white">AI Knowledge Platform</p>
          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className="rounded-lg border border-white/25 px-3 py-1.5 text-sm text-slate-100 hover:bg-white/10"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-3 py-1.5 text-sm font-medium text-white hover:brightness-110"
            >
              Get started
            </Link>
          </div>
        </header>

        <section className="flex flex-1 items-center py-12">
          <div className="grid w-full items-center gap-8 lg:grid-cols-2">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            >
              <p className="mb-3 inline-block rounded-full border border-indigo-300/35 bg-indigo-500/20 px-3 py-1 text-xs font-medium text-indigo-100">
                Production-Ready Document Intelligence
              </p>
              <h1 className="text-4xl font-semibold leading-tight text-white md:text-5xl">
                Understand every document with AI-powered precision.
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-7 text-slate-200">
                A modern intelligence layer for your business docs: ingest, query, analyze, and generate
                strategic reports with a premium user experience.
              </p>

              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href="/register"
                  className="rounded-xl bg-gradient-to-r from-indigo-500 to-cyan-500 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-indigo-900/30 hover:brightness-110"
                >
                  Start Free
                </Link>
                <Link
                  href="/dashboard"
                  className="rounded-xl border border-white/25 px-5 py-2.5 text-sm text-white hover:bg-white/10"
                >
                  Open Dashboard
                </Link>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.65, delay: 0.08 }}
              className="rounded-2xl border border-white/20 bg-white/8 p-6 backdrop-blur-xl"
            >
              <h2 className="text-lg font-medium text-white">Why teams choose this platform</h2>
              <div className="mt-4 space-y-3">
                {features.map((feature) => (
                  <article
                    key={feature.title}
                    className="rounded-xl border border-white/15 bg-slate-900/40 p-4"
                  >
                    <h3 className="text-sm font-semibold text-cyan-100">{feature.title}</h3>
                    <p className="mt-1 text-xs leading-6 text-slate-300">{feature.desc}</p>
                  </article>
                ))}
              </div>
            </motion.div>
          </div>
        </section>
      </div>
    </main>
  );
}
