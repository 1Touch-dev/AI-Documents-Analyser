"use client";

import { PlayCircle, CheckCircle2, ArrowRight, Sparkles, LayoutDashboard, MessageCircle, Workflow, Files } from "lucide-react";
import Link from "next/link";

export default function DemoPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-16 pb-20">
      {/* Hero */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-4 py-1.5 text-xs font-bold text-indigo-400 border border-indigo-500/20">
          <Sparkles className="h-3 w-3" />
          Interactive Demo
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-white lg:text-6xl">
          Experience the Future of <br />
          <span className="bg-gradient-to-r from-indigo-400 via-cyan-400 to-indigo-400 bg-clip-text text-transparent">Business Intelligence</span>
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-slate-400">
          Welcome to the AI Knowledge Platform. Follow this quick tour to understand how to leverage 
          automated document analysis for your business.
        </p>
      </div>

      {/* Feature Grid */}
      <div className="grid gap-8 md:grid-cols-2">
        {[
          { 
            title: "Executive Console", 
            desc: "Monitor your organization's knowledge growth and key financial metrics in real-time.", 
            icon: LayoutDashboard, 
            href: "/dashboard",
            color: "indigo"
          },
          { 
            title: "AI Assistant", 
            desc: "Query your entire document repository in plain English. Get answers with citations.", 
            icon: MessageCircle, 
            href: "/chat",
            color: "cyan"
          },
          { 
            title: "Business Analysis", 
            desc: "Run one-click intelligence workflows for SWOT, Financial Audits, and Risk Assessment.", 
            icon: Workflow, 
            href: "/workflows",
            color: "emerald"
          },
          { 
            title: "Intelligent Vault", 
            desc: "Store and automatically categorize your documents using advanced LLM classification.", 
            icon: Files, 
            href: "/documents",
            color: "amber"
          }
        ].map((f, i) => (
          <div key={i} className="group relative rounded-[2.5rem] border border-white/10 bg-slate-900/40 p-8 backdrop-blur-xl transition hover:bg-slate-900/60 shadow-xl overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition">
              <f.icon className="h-24 w-24" />
            </div>
            
            <div className={`mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-${f.color}-500/10 text-${f.color}-400`}>
              <f.icon className="h-7 w-7" />
            </div>
            
            <h3 className="text-2xl font-bold text-white">{f.title}</h3>
            <p className="mt-2 text-slate-400 leading-relaxed">{f.desc}</p>
            
            <Link 
              href={f.href}
              className="mt-8 flex items-center gap-2 text-sm font-bold text-white transition hover:gap-3"
            >
              Explore Module
              <ArrowRight className="h-4 w-4 text-indigo-400" />
            </Link>
          </div>
        ))}
      </div>

      {/* Checklist */}
      <div className="rounded-[3rem] border border-white/10 bg-gradient-to-br from-indigo-500/10 via-slate-900 to-slate-900 p-12 shadow-2xl">
        <div className="grid gap-12 lg:grid-cols-2">
          <div>
            <h2 className="text-3xl font-bold text-white mb-6">How to get started?</h2>
            <div className="space-y-6">
              {[
                "Upload a few business documents (PDF/XLSX) in the Documents section.",
                "Wait for the AI to finish indexing and categorization.",
                "Ask your first question in the AI Assistant chat.",
                "Run a Financial Health workflow to see extracted metrics.",
                "Save and export your first Executive Report."
              ].map((step, i) => (
                <div key={i} className="flex gap-4">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="h-4 w-4" />
                  </div>
                  <p className="text-slate-300 text-sm leading-relaxed">{step}</p>
                </div>
              ))}
            </div>
          </div>
          
          <div className="flex flex-col items-center justify-center text-center p-8 rounded-[2rem] bg-white/5 border border-white/5 backdrop-blur-md">
            <div className="h-20 w-20 rounded-full bg-indigo-500/20 flex items-center justify-center mb-6 animate-pulse">
              <PlayCircle className="h-10 w-10 text-indigo-400" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Ready to Dive In?</h3>
            <p className="text-sm text-slate-500 mb-8 max-w-xs">Start your first analysis now and see the power of Agentic BI.</p>
            <Link 
              href="/dashboard"
              className="w-full rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 py-4 text-lg font-bold text-white shadow-xl transition hover:scale-[1.02] hover:brightness-110"
            >
              Go to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
