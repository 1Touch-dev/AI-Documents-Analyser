"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listConversations, type ConversationItem } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export default function ConversationsPage() {
  const { token } = useAuth();
  const router = useRouter();
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
        <p className="text-sm text-slate-300">Click any conversation to open and resume that chat session.</p>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      <div className="grid gap-3">
        {items.map((item) => (
          <article 
            key={item.session_id} 
            onClick={() => router.push(`/chat?session_id=${item.session_id}`)}
            className="rounded-xl border border-white/10 bg-slate-900/40 p-5 cursor-pointer transition hover:bg-slate-900/80 hover:border-indigo-500/30 hover:scale-[1.01] shadow-lg active:scale-95"
          >
            <h3 className="text-sm font-semibold text-cyan-100">{item.title || "Untitled session"}</h3>
            <p className="mt-1 text-xs text-slate-400">
              {item.category || "general"} · {item.message_count} messages
            </p>
          </article>
        ))}
        {!items.length ? <p className="text-sm text-slate-300">No conversations found.</p> : null}
      </div>
    </section>
  );
}

