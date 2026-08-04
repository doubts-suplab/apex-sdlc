"use client";

import { Coins, Cpu, Timer } from "lucide-react";
import { useReferenceMetrics } from "@/lib/queries/metrics";
import { PersonaMetrics, ReferenceMetrics } from "@/types/metrics";
import { PERSONA_LABELS, Persona } from "@/types/project";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function personaLabel(key: string): string {
  return PERSONA_LABELS[key as Persona] ?? key;
}

function fmtUsd(v: number): string {
  return `$${v.toFixed(4)}`;
}

function fmtTokens(v: number): string {
  return v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${v}`;
}

function TotalStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 shadow-sm">
      {icon}
      <div className="leading-tight">
        <div className="text-sm font-semibold text-slate-800">{value}</div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </div>
  );
}

function PersonaRow({ metric, highlighted }: { metric: PersonaMetrics; highlighted: boolean }) {
  return (
    <tr className={cn(highlighted && "bg-indigo-50")}>
      <td className="px-3 py-2 text-sm font-medium text-slate-800">
        {personaLabel(metric.persona)}
        {highlighted && (
          <Badge variant="outline" className="ml-2 border-indigo-200 bg-indigo-100 text-indigo-700 text-[10px]">
            you
          </Badge>
        )}
      </td>
      <td className="px-3 py-2 text-right text-sm tabular-nums text-slate-600">{metric.runs}</td>
      <td className="px-3 py-2 text-right text-sm tabular-nums text-slate-600">
        {fmtTokens(metric.input_tokens)} / {fmtTokens(metric.output_tokens)}
      </td>
      <td className="px-3 py-2 text-right text-sm tabular-nums font-medium text-slate-800">
        {fmtUsd(metric.cost_usd)}
      </td>
      <td className="px-3 py-2 text-right text-sm tabular-nums text-slate-600">
        {metric.avg_latency_ms.toFixed(1)} ms
      </td>
    </tr>
  );
}

/**
 * Presentational per-persona metering panel. Source-agnostic — fed by either the reference journey or a
 * persisted project. Renders loading / error / empty states.
 */
export function MetricsPanel({
  data,
  isLoading,
  isError,
  errorMsg,
  selectedPersona,
  emptyState,
  action,
}: {
  data?: ReferenceMetrics;
  isLoading: boolean;
  isError: boolean;
  errorMsg?: string;
  selectedPersona?: string;
  emptyState?: React.ReactNode;
  action?: React.ReactNode;
}) {
  if (isLoading) {
    return <Skeleton className="h-64 w-full rounded-lg" />;
  }
  if (isError || !data) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Could not load metrics{errorMsg ? `: ${errorMsg}` : ""}.
      </div>
    );
  }

  const { personas, totals, pricing_model } = data;

  return (
    <div className="rounded-lg border bg-slate-50 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Cost · Tokens · Latency by persona</h3>
          <p className="text-xs text-slate-500">
            Real token counts + latency from the governed journey. Cost is illustrative, priced at{" "}
            <code className="rounded bg-slate-200 px-1">{pricing_model}</code>.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <TotalStat
            icon={<Cpu className="h-4 w-4 text-indigo-500" />}
            label="tokens (in/out)"
            value={`${fmtTokens(totals.input_tokens)} / ${fmtTokens(totals.output_tokens)}`}
          />
          <TotalStat icon={<Coins className="h-4 w-4 text-amber-500" />} label="est. cost" value={fmtUsd(totals.cost_usd)} />
          <TotalStat icon={<Timer className="h-4 w-4 text-emerald-500" />} label="total runs" value={`${totals.runs}`} />
          {action}
        </div>
      </div>
      {personas.length === 0 ? (
        <div className="rounded-md border border-dashed bg-white p-6 text-center text-sm text-slate-500">
          {emptyState ?? "No metered runs yet."}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border bg-white">
          <table className="w-full min-w-[32rem]">
            <thead>
              <tr className="border-b bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2 text-left font-medium">Persona</th>
                <th className="px-3 py-2 text-right font-medium">Runs</th>
                <th className="px-3 py-2 text-right font-medium">Tokens in/out</th>
                <th className="px-3 py-2 text-right font-medium">Est. cost</th>
                <th className="px-3 py-2 text-right font-medium">Avg latency</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {personas.map((m) => (
                <PersonaRow key={m.persona} metric={m} highlighted={m.persona === selectedPersona} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** The reference-journey cost dashboard (offline, no project). Used on the /journey page. */
export function CostDashboard({ selectedPersona }: { selectedPersona?: string }) {
  const { data, isLoading, isError, error } = useReferenceMetrics();
  return (
    <MetricsPanel
      data={data}
      isLoading={isLoading}
      isError={isError}
      errorMsg={error instanceof Error ? error.message : undefined}
      selectedPersona={selectedPersona}
    />
  );
}
