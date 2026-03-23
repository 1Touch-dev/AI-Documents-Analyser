"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { motion } from "motion/react";
import { useAuth } from "@/contexts/auth-context";
import { AuthShell } from "@/components/auth-shell";

export default function RegisterPage() {
  const router = useRouter();
  const { registerUser, isAuthenticated } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await registerUser(username, password);
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Set up secure access for the AI Knowledge Platform."
      footer={
        <>
          Already registered?{" "}
          <Link href="/login" className="font-medium text-indigo-300 hover:text-indigo-200">
            Sign in
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
          {isSubmitting ? "Creating account..." : "Create account"}
        </motion.button>
      </form>
    </AuthShell>
  );
}

