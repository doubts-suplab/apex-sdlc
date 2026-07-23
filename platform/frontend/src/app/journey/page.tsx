"use client";

import { useState } from "react";
import { AlertCircle, ArrowRight, ShieldCheck, UserCheck } from "lucide-react";
import { useReferenceJourney } from "@/lib/queries/journey";
import { usePersona } from "@/lib/persona";
import { PERSONA_LABELS, PHASE_LABELS, Persona, PhaseType } from "@/types/project";
import { JourneyPhase } from "@/types/journey";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function personaLabel(key: string): string {
  return PERSONA_LABELS[key as Persona] ?? key;
}

function phaseLabel(key: string): string {
  return PHASE_LABELS[key as PhaseType] ?? key;
}

function isRelevant(phase: JourneyPhase, persona: Persona): boolean {
  return phase.persona === persona || phase.stakeholders.includes(persona);
}

function OutcomeBadge({ outcome }: { outcome: string }) {
  const enforced = outcome === "auto-enforced";
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 text-xs font-medium",
        enforced
          ? "border-green-200 bg-green-50 text-green-700"
          : "border-amber-200 bg-amber-50 text-amber-700"
      )}
    >
      {enforced ? <ShieldCheck className="h-3 w-3" /> : <UserCheck className="h-3 w-3" />}
      {enforced ? "Auto-enforced" : "Human review"}
    </Badge>
  );
}

function StatTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border bg-white px-4 py-3 shadow-sm">
      <div className="text-2xl font-bold tabular-nums text-slate-900">{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}

function PhaseCard({
  phase,
  index,
  persona,
}: {
  phase: JourneyPhase;
  index: number;
  persona: Persona;
}) {
  const relevant = isRelevant(phase, persona);
  const owns = phase.persona === persona;
  return (
    <div
      className={cn(
        "rounded-lg border bg-white p-5 shadow-sm transition-all",
        relevant ? "border-slate-300 ring-1 ring-slate-200" : "opacity-60"
      )}
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
          {index + 1}
        </span>
        <h3 className="text-base font-semibold text-slate-900">{phaseLabel(phase.phase)}</h3>
        <Badge variant="secondary" className="text-xs">
          {personaLabel(phase.persona)}
        </Badge>
        {relevant && (
          <Badge
            variant="outline"
            className="border-blue-200 bg-blue-50 text-xs font-medium text-blue-700"
          >
            {owns ? "Your step" : "You contribute"}
          </Badge>
        )}
        <span className="ml-auto font-mono text-xs text-slate-400">{phase.agent_name}</span>
      </div>

      <p className="mt-3 text-sm text-slate-600">{phase.summary}</p>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <Badge variant="outline" className="border-slate-200 text-slate-600">
          authority: {phase.authority}
        </Badge>
        <Badge variant="outline" className="border-slate-200 text-slate-600">
          decision: {phase.action}
        </Badge>
        <Badge variant="outline" className="border-slate-200 text-slate-600">
          confidence: {phase.confidence.toFixed(2)}
        </Badge>
        <OutcomeBadge outcome={phase.outcome} />
      </div>

      <p className="mt-3 border-l-2 border-slate-200 pl-3 text-sm italic text-slate-500">
        {phase.rationale}
      </p>

      <div className="mt-4">
        <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
          Artifacts ({phase.artifacts.length})
        </div>
        <div className="flex flex-wrap gap-2">
          {phase.artifacts.map((a) => (
            <span
              key={a.name}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700"
              title={a.title}
            >
              <span className="font-mono">{a.name}</span>
              <span className="text-slate-400">·</span>
              <span className="text-slate-500">{a.kind}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function JourneySkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-40 w-full rounded-lg" />
      ))}
    </div>
  );
}

export default function JourneyPage() {
  const { persona, mounted } = usePersona();
  const { data, isLoading, isError, error } = useReferenceJourney();
  const [onlyMine, setOnlyMine] = useState(false);

  if (isLoading || !mounted) {
    return (
      <div className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        <Skeleton className="h-9 w-72" />
        <JourneySkeleton />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <div>
            <p className="text-sm font-medium">Failed to load the reference journey</p>
            <p className="mt-0.5 text-xs text-red-600">
              {error instanceof Error ? error.message : "Unknown error"} — is the backend running with{" "}
              <code>LLM_PROVIDER=stub</code>?
            </p>
          </div>
        </div>
      </div>
    );
  }

  const relevantCount = data.phases.filter((p) => isRelevant(p, persona)).length;
  const visiblePhases = onlyMine
    ? data.phases.filter((p) => isRelevant(p, persona))
    : data.phases;

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-6 py-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Reference Journey</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          {data.project.name} — one project walking all seven SDLC phases. Every artifact is generated by
          the governed agent-harness; the confidence gate, not the agent, decides what auto-enforces.
        </p>
        {data.project.description && (
          <p className="mt-1 text-sm text-slate-500">{data.project.description}</p>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Phases" value={data.stats.phase_count} />
        <StatTile label="Artifacts" value={data.stats.artifact_count} />
        <StatTile label="Auto-enforced" value={data.stats.auto_enforced_count} />
        <StatTile label="Human review" value={data.stats.human_review_count} />
        <StatTile label="Audit entries" value={data.stats.audit_entries} />
        <StatTile label="Gate bypasses" value={data.stats.confidence_gate_bypass_total} />
      </div>

      {/* Persona focus */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3">
        <p className="text-sm text-blue-800">
          Viewing as <strong>{personaLabel(persona)}</strong> — {relevantCount} of{" "}
          {data.phases.length} phases involve you. Change persona from the switcher in the top nav.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setOnlyMine((v) => !v)}
          className="gap-1.5 bg-white"
        >
          <ArrowRight className="h-3.5 w-3.5" />
          {onlyMine ? "Show all phases" : "Only my phases"}
        </Button>
      </div>

      {/* Phase walk */}
      <div className="space-y-4">
        {visiblePhases.map((phase) => (
          <PhaseCard
            key={phase.phase}
            phase={phase}
            index={data.phases.findIndex((p) => p.phase === phase.phase)}
            persona={persona}
          />
        ))}
      </div>
    </div>
  );
}
