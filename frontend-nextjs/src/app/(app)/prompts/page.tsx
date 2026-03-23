"use client";

import { FormEvent, useEffect, useState } from "react";
import { createPrompt, deletePrompt, listPrompts, type PromptItem } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export default function PromptsPage() {
  const { token } = useAuth();
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  async function refresh() {
    const result = await listPrompts(token ?? undefined);
    setPrompts(result.prompts);
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : "Failed to load prompts."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!name || !template) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await createPrompt(
        {
          name,
          template,
          category: category.trim() || undefined,
          description: description.trim() || undefined,
        },
        token ?? undefined
      );
      setName("");
      setCategory("");
      setDescription("");
      setTemplate("");
      setIsCreateModalOpen(false);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create prompt.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function onDelete(promptId: string) {
    setError(null);
    setDeletingId(promptId);
    try {
      await deletePrompt(promptId, token ?? undefined);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete prompt.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Prompts</h2>
          <p className="text-sm text-slate-300">Reusable prompt templates migration baseline.</p>
        </div>
        <button
          type="button"
          onClick={() => setIsCreateModalOpen(true)}
          className="rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-4 py-2 text-sm font-medium text-white"
        >
          + Add Prompt
        </button>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      {isCreateModalOpen && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-950/70 p-4 backdrop-blur-sm"
          onClick={() => setIsCreateModalOpen(false)}
        >
          <form
            onSubmit={onSubmit}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl space-y-3 rounded-xl border border-white/15 bg-slate-950 p-5"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Create New Prompt</h3>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="rounded-md border border-white/20 px-2 py-1 text-xs text-slate-200 hover:bg-white/10"
              >
                Close
              </button>
            </div>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name"
              className="w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
            />
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="Category (optional)"
              className="w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
            />
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              className="w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
            />
            <textarea
              rows={5}
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              placeholder="Template (use ${context} and ${question})"
              className="w-full rounded-lg border border-white/20 bg-slate-950/60 px-3 py-2 text-sm text-white"
            />
            <button
              disabled={isSubmitting || !name.trim() || !template.trim()}
              className="rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {isSubmitting ? "Creating..." : "Create Prompt"}
            </button>
          </form>
        </div>
      )}
      <div className="space-y-3">
        {prompts.map((prompt) => (
          <article key={prompt.id} className="rounded-lg border border-white/15 bg-white/5 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-cyan-100">
                  {prompt.name}{" "}
                  <span className="text-xs font-normal text-slate-300">({prompt.category || "—"})</span>
                </h3>
                <p className="mt-1 text-xs text-slate-300">{prompt.description || "No description"}</p>
              </div>
              <button
                type="button"
                onClick={() => onDelete(prompt.id)}
                disabled={deletingId === prompt.id}
                className="rounded-md border border-red-300/40 px-2 py-1 text-xs text-red-200 hover:bg-red-500/10 disabled:opacity-60"
              >
                {deletingId === prompt.id ? "Deleting..." : "Delete"}
              </button>
            </div>
            <pre className="mt-3 overflow-x-auto rounded-md border border-white/10 bg-slate-950/60 p-3 text-xs text-slate-200">
              {prompt.template}
            </pre>
          </article>
        ))}
      </div>
    </section>
  );
}

