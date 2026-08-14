"use client";

import { Github, Radio, Trello } from "lucide-react";
import { useWebhookEvents } from "@/lib/queries/webhooks";
import { WebhookEvent } from "@/types/webhook";

function SourceIcon({ source }: { source: string }) {
  if (source === "github") return <Github className="h-3.5 w-3.5" />;
  if (source === "jira") return <Trello className="h-3.5 w-3.5" />;
  return <Radio className="h-3.5 w-3.5" />;
}

function when(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString();
}

/**
 * Recent inbound webhook deliveries — the signature-verified, de-duped events APEX has received.
 * A compact activity strip backed by GET /api/v1/webhooks/events.
 */
export function WebhookActivityFeed() {
  const { data, isLoading, isError } = useWebhookEvents(10);
  const items = data ?? [];

  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b px-6 py-4">
        <Radio className="h-4 w-4 text-slate-700" />
        <h2 className="text-base font-semibold text-slate-900">Inbound webhook activity</h2>
      </div>
      {isLoading ? (
        <p className="px-6 py-5 text-sm text-slate-400">Loading recent deliveries…</p>
      ) : isError ? (
        <p className="px-6 py-5 text-sm text-red-600">Failed to load webhook activity.</p>
      ) : items.length === 0 ? (
        <p className="px-6 py-5 text-sm text-slate-500">
          No inbound deliveries yet. Signature-verified GitHub / Jira events appear here once received
          (duplicates are de-duped and never shown twice).
        </p>
      ) : (
        <ul className="divide-y">
          {items.map((e: WebhookEvent) => (
            <li key={`${e.source}:${e.delivery_id}`} className="flex items-center gap-3 px-6 py-2.5">
              <span className="flex items-center gap-1.5 text-slate-600">
                <SourceIcon source={e.source} />
                <span className="text-xs font-medium capitalize">{e.source}</span>
              </span>
              <span className="font-mono text-xs text-slate-800">{e.event_type}</span>
              <span className="ml-auto text-xs text-slate-400">{when(e.received_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
