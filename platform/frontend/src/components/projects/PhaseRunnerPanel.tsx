"use client";

import { useMemo, useState } from "react";
import {
  CheckCircle2,
  CircleDashed,
  FileText,
  Loader2,
  Play,
  ShieldCheck,
  ThumbsUp,
  UserCheck,
  XCircle,
} from "lucide-react";
import { useAuthToken } from "@/lib/auth";
import { usePersona } from "@/lib/persona";
import {
  useAgentRuns,
  useApprovedPhases,
  useApprovePhase,
  useArtifacts,
  useGateStatus,
  useRunPhase,
} from "@/lib/queries/phases";
import { AgentRun, GateStatus, StoredArtifact } from "@/types/agentRun";
import { ArtifactContentDialog } from "@/components/projects/ArtifactContentDialog";
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
 * Per-phase run trigger + approve + stored governed state. Each SDLC phase has an approver-gated "Run"
 * button (runs its agent on the harness and persists the run) and an "Approve" button (durable,
 * identity-bound spec approval that unblocks the gate). Artifact counts expand to the phase's stored
 * artifacts, each opening its content.
 */
export function PhaseRunnerPanel({ projectId }: { projectId: string }) {
  const { persona } = usePersona();
  const { isApprover, ready } = useAuthToken();
  const runs = useAgentRuns(projectId);
  const artifacts = useArtifacts(projectId);
  const gates = useGateStatus(projectId);
  const runPhase = useRunPhase(projectId);
  const approvedPhases = useApprovedPhases(projectId);
  const approvePhase = useApprovePhase(projectId);

  const [expandedPhase, setExpandedPhase] = useState<PhaseType | null>(null);
  const [selected, setSelected] = useState<{ id: string; name: string } | null>(null);

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

  const artifactsByPhase = useMemo(() => {
    const map = new Map<PhaseType, StoredArtifact[]>();
    (artifacts.data ?? []).forEach((a: StoredArtifact) => {
      const list = map.get(a.phase) ?? [];
      list.push(a);
      map.set(a.phase, list);
    });
    return map;
  }, [artifacts.data]);

  const approvedSet = useMemo(
    () => new Set(approvedPhases.data ?? []),
    [approvedPhases.data]
  );

  const pendingPhase = runPhase.isPending ? runPhase.variables : undefined;
  const approvingPhase = approvePhase.isPending ? approvePhase.variables?.phase : undefined;
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
          const phaseArtifacts = artifactsByPhase.get(phase) ?? [];
          const artifactCount = phaseArtifacts.length;
          const isRunning = pendingPhase === phase;
          const isApproving = approvingPhase === phase;
          const approved = approvedSet.has(phase);
          const isExpanded = expandedPhase === phase;
          return (
            <div key={phase} className="px-6 py-3.5">
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
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
                <button
                  type="button"
                  disabled={artifactCount === 0}
                  onClick={() => setExpandedPhase(isExpanded ? null : phase)}
                  className={cn(
                    "flex w-24 shrink-0 items-center gap-1 text-xs",
                    artifactCount > 0
                      ? "text-blue-600 hover:text-blue-800"
                      : "cursor-default text-slate-400"
                  )}
                  title={artifactCount > 0 ? "Show artifacts" : "No artifacts yet"}
                >
                  <FileText className="h-3.5 w-3.5" />
                  {artifactCount} {artifactCount === 1 ? "artifact" : "artifacts"}
                </button>
                {approved ? (
                  <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-green-700">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Approved
                  </span>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="shrink-0 gap-1.5 text-slate-600"
                    disabled={!ready || !isApprover || !run || approvePhase.isPending}
                    onClick={() => approvePhase.mutate({ phase })}
                    title={
                      isApprover
                        ? `Approve the ${PHASE_LABELS[phase]} spec (durable, identity-bound)`
                        : "Approver persona required (Lead / BA / Architect / CISO)"
                    }
                  >
                    {isApproving ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <ThumbsUp className="h-3.5 w-3.5" />
                    )}
                    Approve
                  </Button>
                )}
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
              {isExpanded && artifactCount > 0 && (
                <div className="mt-2 flex flex-wrap gap-2 pl-32">
                  {phaseArtifacts.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => setSelected({ id: a.id, name: a.name })}
                      className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-xs text-slate-600 hover:border-blue-300 hover:text-blue-700"
                    >
                      {a.name}
                    </button>
                  ))}
                </div>
              )}
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

      <ArtifactContentDialog
        projectId={projectId}
        artifactId={selected?.id ?? null}
        artifactName={selected?.name ?? null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
