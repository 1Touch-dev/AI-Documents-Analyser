"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { motion } from "motion/react";
import { useAuth } from "@/contexts/auth-context";
import { AuthShell } from "@/components/auth-shell";

export default function LoginPage() {
  const router = useRouter();
  const { loginUser, isAuthenticated } = useAuth();

  const [nextPath, setNextPath] = useState("/dashboard");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setNextPath(params.get("next") || "/dashboard");
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(nextPath);
    }
  }, [isAuthenticated, nextPath, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await loginUser(username, password);
      router.push(nextPath);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to access your AI documents workspace."
      footer={
        <>
          New here?{" "}
          <Link href="/register" className="font-medium text-indigo-300 hover:text-indigo-200">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block text-sm">
          <span className="mb-1.5 block text-slate-300">Username</span>
          <input
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2.5 text-white outline-none placeholder:text-slate-400 focus:border-indigo-300/70"
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1.5 block text-slate-300">Password</span>
          <input
            required
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2.5 text-white outline-none placeholder:text-slate-400 focus:border-indigo-300/70"
          />
        </label>

        {error ? (
          <p className="rounded-md border border-red-300/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        <motion.button
          whileTap={{ scale: 0.98 }}
          disabled={isSubmitting}
          className="w-full rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-3 py-2.5 text-sm font-medium text-white shadow-lg shadow-indigo-900/30 hover:brightness-110 disabled:opacity-60"
        >
          {isSubmitting ? "Signing in..." : "Sign in"}
        </motion.button>
      </form>
    </AuthShell>
  );
}

