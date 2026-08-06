"use client";

import { useMemo } from "react";
import {
  CheckCircle2,
  CircleDashed,
  FileText,
  Loader2,
  Play,
  ShieldCheck,
  UserCheck,
  XCircle,
} from "lucide-react";
import { useAuthToken } from "@/lib/auth";
import { usePersona } from "@/lib/persona";
import {
  useAgentRuns,
  useArtifacts,
  useGateStatus,
  useRunPhase,
} from "@/lib/queries/phases";
import { AgentRun, GateStatus, StoredArtifact } from "@/types/agentRun";
import {
  PHASE_ORDER,
  PHASE_LABELS,
  PERSONA_LABELS,
  Persona,
  PhaseType,
} from "@/types/project";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const GATE_STYLES: Record<string, string> = {
  passed: "bg-green-100 text-green-800 border-green-200",
  pending: "bg-amber-100 text-amber-800 border-amber-200",
  failed: "bg-red-100 text-red-800 border-red-200",
};

function GateBadge({ status }: { status?: string }) {
  if (!status) {
    return <span className="text-xs text-slate-400">—</span>;
  }
  const Icon =
    status === "passed" ? CheckCircle2 : status === "failed" ? XCircle : CircleDashed;
  return (
    <Badge
      variant="outline"
      className={cn("gap-1 text-xs font-medium capitalize", GATE_STYLES[status] ?? "")}
    >
      <Icon className="h-3 w-3" />
      {status}
    </Badge>
  );
}

function OutcomeBadge({ run }: { run?: AgentRun }) {
  if (!run) {
    return <span className="text-xs text-slate-400">not run</span>;
  }
  const auto = run.auto_enforced;
  const Icon = auto ? ShieldCheck : UserCheck;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs font-medium",
        auto ? "text-green-700" : "text-amber-700"
      )}
      title={`${run.action} · confidence ${(run.confidence * 100).toFixed(0)}%`}
    >
      <Icon className="h-3.5 w-3.5" />
      {auto ? "auto-enforced" : "human review"}
      <span className="text-slate-400">· {(run.confidence * 100).toFixed(0)}%</span>
    </span>
  );
}

function personaLabel(key: string): string {
  return PERSONA_LABELS[key as Persona] ?? key;
}

/**
 * Per-phase run trigger + stored governed state. Each SDLC phase has an approver-gated "Run" button
 * that runs its agent on the harness and persists the run — the UI surface of the dispatch execution
 * path — then reflects the stored agent run, its gate status, and its artifact count.
 */
export function PhaseRunnerPanel({ projectId }: { projectId: string }) {
  const { persona } = usePersona();
  const { isApprover, ready } = useAuthToken();
  const runs = useAgentRuns(projectId);
  const artifacts = useArtifacts(projectId);
  const gates = useGateStatus(projectId);
  const runPhase = useRunPhase(projectId);

  const runByPhase = useMemo(() => {
    const map = new Map<PhaseType, AgentRun>();
    (runs.data ?? []).forEach((r: AgentRun) => map.set(r.phase, r)); // latest wins (list is ordered)
    return map;
  }, [runs.data]);

  const gateByPhase = useMemo(() => {
    const map = new Map<PhaseType, string>();
    (gates.data ?? []).forEach((g: GateStatus) => map.set(g.phase, g.status));
    return map;
  }, [gates.data]);

  const artifactCountByPhase = useMemo(() => {
    const map = new Map<PhaseType, number>();
    (artifacts.data ?? []).forEach((a: StoredArtifact) =>
      map.set(a.phase, (map.get(a.phase) ?? 0) + 1)
    );
    return map;
  }, [artifacts.data]);

  const pendingPhase = runPhase.isPending ? runPhase.variables : undefined;
  const totalRuns = runs.data?.length ?? 0;

  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Phase agents</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Run any phase&apos;s agent on the governed harness — the confidence gate decides what
            auto-enforces and what routes to a human. Stored runs, gates, and artifacts appear below.
          </p>
        </div>
        {!isApprover && ready && (
          <p className="text-xs text-amber-700">
            Viewing as {personaLabel(persona)} — switch to Lead / BA / Architect / CISO to run a phase.
          </p>
        )}
      </div>

      <div className="divide-y">
        {PHASE_ORDER.map((phase) => {
          const run = runByPhase.get(phase);
          const gate = gateByPhase.get(phase);
          const artifactCount = artifactCountByPhase.get(phase) ?? 0;
          const isRunning = pendingPhase === phase;
          return (
            <div
              key={phase}
              className="flex flex-wrap items-center gap-x-4 gap-y-2 px-6 py-3.5"
            >
              <div className="w-32 shrink-0">
                <span className="text-sm font-medium text-slate-800">
                  {PHASE_LABELS[phase]}
                </span>
              </div>
              <div className="w-28 shrink-0">
                <GateBadge status={gate} />
              </div>
              <div className="min-w-0 flex-1">
                <OutcomeBadge run={run} />
              </div>
              <div className="flex w-24 shrink-0 items-center gap-1 text-xs text-slate-500">
                <FileText className="h-3.5 w-3.5" />
                {artifactCount} {artifactCount === 1 ? "artifact" : "artifacts"}
              </div>
              <Button
                size="sm"
                variant="outline"
                className="shrink-0 gap-1.5 bg-white"
                disabled={!ready || !isApprover || runPhase.isPending}
                onClick={() => runPhase.mutate(phase)}
                title={
                  isApprover
                    ? `Run the ${PHASE_LABELS[phase]} agent and persist the run`
                    : "Approver persona required (Lead / BA / Architect / CISO)"
                }
              >
                {isRunning ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Play className="h-3.5 w-3.5" />
                )}
                {isRunning ? "Running…" : run ? "Re-run" : "Run"}
              </Button>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between gap-3 border-t px-6 py-3 text-xs text-slate-500">
        <span>
          {totalRuns > 0
            ? `${totalRuns} stored run${totalRuns === 1 ? "" : "s"}`
            : "No stored runs yet — run a phase to populate."}
        </span>
        {runPhase.isError && (
          <span className="text-red-600">
            {runPhase.error instanceof Error ? runPhase.error.message : "Run failed."}
            {!isApprover && " (approver persona required)"}
          </span>
        )}
        {runPhase.isSuccess && !runPhase.isError && (
          <span className="text-green-700">
            Ran {PHASE_LABELS[runPhase.data.phase]} → {runPhase.data.outcome} ·{" "}
            {runPhase.data.artifacts} artifact{runPhase.data.artifacts === 1 ? "" : "s"}
          </span>
        )}
      </div>
    </div>
  );
}
