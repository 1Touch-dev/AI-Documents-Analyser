"use client";

import { useEffect, useState } from "react";
import { listConversations, type ConversationItem } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export default function ConversationsPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<ConversationItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    listConversations(token ?? undefined)
      .then((res) => mounted && setItems(res.conversations))
      .catch((e) =>
        mounted && setError(e instanceof Error ? e.message : "Failed to load conversations.")
      );
    return () => {
      mounted = false;
    };
  }, [token]);

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-white">Conversations</h2>
        <p className="text-sm text-slate-300">Conversation history migration baseline.</p>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      <div className="grid gap-3">
        {items.map((item) => (
          <article key={item.session_id} className="rounded-lg border border-white/15 bg-white/5 p-4">
            <h3 className="text-sm font-semibold text-cyan-100">{item.title || "Untitled session"}</h3>
            <p className="mt-1 text-xs text-slate-300">
              {item.category || "general"} · {item.message_count} messages
            </p>
          </article>
        ))}
        {!items.length ? <p className="text-sm text-slate-300">No conversations found.</p> : null}
      </div>
    </section>
  );
}

