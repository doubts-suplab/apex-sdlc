"use client";

import { useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Gavel,
  Lock,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import {
  useReferenceJourney,
  useReferenceGates,
  useAuthorityModel,
} from "@/lib/queries/journey";
import { usePersona } from "@/lib/persona";
import { CostDashboard } from "@/components/projects/CostDashboard";
import { ArtifactChip } from "@/components/journey/ArtifactChip";
import { PERSONA_LABELS, PHASE_LABELS, PHASE_ORDER, Persona, PhaseType } from "@/types/project";
import { GateResult, JourneyPhase } from "@/types/journey";
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

/**
 * Surfaces the confidence gate for a phase: the threshold its confidence had to clear to auto-enforce,
 * or — for SUGGEST/OBSERVE phases — that it can never auto-enforce (gate rule G-5).
 */
function ThresholdBadge({
  threshold,
  confidence,
}: {
  threshold: number | null | undefined;
  confidence: number;
}) {
  if (threshold === null || threshold === undefined) {
    return (
      <Badge
        variant="outline"
        className="gap-1 border-amber-200 bg-amber-50 text-xs font-medium text-amber-700"
        title="SUGGEST/OBSERVE authority can never auto-enforce — always routed to a human (harness gate rule G-5)."
      >
        <Lock className="h-3 w-3" />
        never auto-enforces · G-5
      </Badge>
    );
  }
  const clears = confidence >= threshold;
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-xs font-medium",
        clears
          ? "border-green-200 bg-green-50 text-green-700"
          : "border-slate-200 bg-slate-50 text-slate-600"
      )}
      title={`Auto-enforces only when confidence ≥ ${threshold.toFixed(2)}.`}
    >
      threshold: {threshold.toFixed(2)} {clears ? "✓" : ""}
    </Badge>
  );
}

/**
 * The governance read model: the G-5 rule plus each phase's authority and confidence threshold.
 * Makes "AI drafts; humans approve" visible as a property of the authority ladder, not a claim.
 */
function GovernanceModelPanel() {
  const { data } = useAuthorityModel();
  const [open, setOpen] = useState(false);
  if (!data) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left"
      >
        <Gavel className="h-4 w-4 shrink-0 text-slate-500" />
        <span className="text-sm font-medium text-slate-800">How governance decides</span>
        <span className="ml-auto text-xs text-slate-500">{open ? "Hide" : "Show"}</span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-slate-200 px-4 py-3">
          <p className="text-sm text-slate-600">{data.gate_rule}</p>
          <p className="text-xs text-slate-500">
            Authority ladder (weakest → strongest):{" "}
            <span className="font-mono">{data.authority_ladder.join(" < ")}</span>
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-slate-400">
                  <th className="py-1 pr-4 font-medium uppercase tracking-wide">Phase</th>
                  <th className="py-1 pr-4 font-medium uppercase tracking-wide">Authority</th>
                  <th className="py-1 pr-4 font-medium uppercase tracking-wide">Auto-enforce threshold</th>
                </tr>
              </thead>
              <tbody className="text-slate-600">
                {data.phases.map((p) => (
                  <tr key={p.phase} className="border-t border-slate-100">
                    <td className="py-1 pr-4">{phaseLabel(p.phase)}</td>
                    <td className="py-1 pr-4 font-mono">{p.authority}</td>
                    <td className="py-1 pr-4">
                      {p.confidence_threshold === null ? (
                        <span className="text-amber-700">never (G-5)</span>
                      ) : (
                        <span className="tabular-nums">≥ {p.confidence_threshold.toFixed(2)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
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

function GateBadge({ status }: { status: GateResult["status"] }) {
  const map = {
    passed: { cls: "border-green-200 bg-green-50 text-green-700", icon: CheckCircle2, label: "Gate passed" },
    pending: { cls: "border-amber-200 bg-amber-50 text-amber-700", icon: Clock, label: "Gate pending" },
    failed: { cls: "border-red-200 bg-red-50 text-red-700", icon: Lock, label: "Gate failed" },
  }[status];
  const Icon = map.icon;
  return (
    <Badge variant="outline" className={cn("gap-1 text-xs font-medium", map.cls)}>
      <Icon className="h-3 w-3" />
      {map.label}
    </Badge>
  );
}

function PhaseCard({
  phase,
  index,
  persona,
  gate,
  approved,
  onToggleApprove,
}: {
  phase: JourneyPhase;
  index: number;
  persona: Persona;
  gate?: GateResult;
  approved: boolean;
  onToggleApprove: () => void;
}) {
  const relevant = isRelevant(phase, persona);
  const owns = phase.persona === persona;
  const canApprove = gate?.status === "pending" && phase.outcome === "human-review";
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
        <div className="ml-auto flex items-center gap-2">
          {gate && <GateBadge status={gate.status} />}
          {canApprove && (
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleApprove}
              className={cn("h-7 text-xs", approved && "border-green-300 bg-green-50 text-green-700")}
            >
              {approved ? "Approved ✓" : "Approve spec"}
            </Button>
          )}
          {approved && !canApprove && (
            <Button variant="outline" size="sm" onClick={onToggleApprove} className="h-7 text-xs">
              Un-approve
            </Button>
          )}
          <span className="font-mono text-xs text-slate-400">{phase.agent_name}</span>
        </div>
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
        <ThresholdBadge threshold={phase.confidence_threshold} confidence={phase.confidence} />
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
            <ArtifactChip key={a.name} artifact={a} />
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
  const [enabledPhases, setEnabledPhases] = useState<PhaseType[]>(PHASE_ORDER);
  // A full spine ⇒ send no `phases` param (identical to the default reference behaviour).
  const phasesArg = enabledPhases.length === PHASE_ORDER.length ? undefined : enabledPhases;
  const { data, isLoading, isError, error } = useReferenceJourney(undefined, phasesArg);
  const [onlyMine, setOnlyMine] = useState(false);
  const [approved, setApproved] = useState<string[]>([]);
  const gatesQuery = useReferenceGates(approved, phasesArg);

  const togglePhase = (ph: PhaseType) =>
    setEnabledPhases((prev) =>
      prev.includes(ph)
        ? prev.length > 1
          ? prev.filter((p) => p !== ph)
          : prev // keep at least one phase enabled
        : PHASE_ORDER.filter((p) => p === ph || prev.includes(p))
    );

  const gateByPhase = new Map((gatesQuery.data?.gates ?? []).map((g) => [g.phase, g]));
  const toggleApprove = (ph: string) =>
    setApproved((prev) => (prev.includes(ph) ? prev.filter((p) => p !== ph) : [...prev, ph]));

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

      {/* How governance decides — the G-5 rule + per-phase confidence thresholds */}
      <GovernanceModelPanel />

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

      {/* Cost / token / latency dashboard, per persona */}
      <CostDashboard selectedPersona={persona} />

      {/* Configurable spine — toggle phases to model a lighter SDLC */}
      <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-slate-700">Spine</span>
          <span className="text-xs text-slate-500">
            Toggle phases to model a lighter SDLC — {enabledPhases.length}/{PHASE_ORDER.length} enabled.
          </span>
          {enabledPhases.length !== PHASE_ORDER.length && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEnabledPhases(PHASE_ORDER)}
              className="ml-auto h-7 text-xs"
            >
              Reset to full spine
            </Button>
          )}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {PHASE_ORDER.map((ph) => {
            const on = enabledPhases.includes(ph);
            return (
              <button
                key={ph}
                type="button"
                onClick={() => togglePhase(ph)}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  on
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-200 bg-slate-50 text-slate-400 line-through"
                )}
              >
                {phaseLabel(ph)}
              </button>
            );
          })}
        </div>
      </div>

      {/* Spine gate status */}
      {gatesQuery.data && (
        <div
          className={cn(
            "flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3",
            gatesQuery.data.all_passed
              ? "border-green-200 bg-green-50 text-green-800"
              : "border-amber-200 bg-amber-50 text-amber-800"
          )}
        >
          <p className="text-sm">
            {gatesQuery.data.all_passed ? (
              <>
                <strong>Spine clear</strong> — every phase gate passed. The project can flow end to end.
              </>
            ) : (
              <>
                <strong>Spine blocked at {phaseLabel(gatesQuery.data.blocking_phase ?? "")}</strong> — a
                phase can&apos;t advance until its spec is approved. Approve the pending specs below.
              </>
            )}
          </p>
          {approved.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => setApproved([])} className="bg-white">
              Reset approvals
            </Button>
          )}
        </div>
      )}

      {/* Phase walk */}
      <div className="space-y-4">
        {visiblePhases.map((phase) => (
          <PhaseCard
            key={phase.phase}
            phase={phase}
            index={data.phases.findIndex((p) => p.phase === phase.phase)}
            persona={persona}
            gate={gateByPhase.get(phase.phase)}
            approved={approved.includes(phase.phase)}
            onToggleApprove={() => toggleApprove(phase.phase)}
          />
        ))}
      </div>
    </div>
  );
}
