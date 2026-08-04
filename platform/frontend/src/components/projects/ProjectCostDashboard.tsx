"use client";

import { Loader2, Play } from "lucide-react";
import { useAuthToken } from "@/lib/auth";
import { usePersona } from "@/lib/persona";
import { useProjectMetrics, usePersistJourney } from "@/lib/queries/metrics";
import { PERSONA_LABELS, Persona } from "@/types/project";
import { Button } from "@/components/ui/button";
import { MetricsPanel } from "@/components/projects/CostDashboard";

// The stored runs were metered against the offline stub ($0); re-price them illustratively so the
// dashboard shows meaningful dollars. A real provider would carry real cost and need no override.
const ILLUSTRATIVE_MODEL = "claude-opus-4-8";

function personaLabel(key: string): string {
  return PERSONA_LABELS[key as Persona] ?? key;
}

/** A persisted project's cost dashboard, with an approver-gated "Run + persist journey" action. */
export function ProjectCostDashboard({ projectId }: { projectId: string }) {
  const { persona } = usePersona();
  const { isApprover, ready } = useAuthToken();
  const metrics = useProjectMetrics(projectId, ILLUSTRATIVE_MODEL);
  const persist = usePersistJourney(projectId);

  const runJourney = () => persist.mutate();

  const persistButton = (
    <Button
      size="sm"
      variant="outline"
      className="gap-1.5 bg-white"
      disabled={!ready || !isApprover || persist.isPending}
      onClick={runJourney}
      title={
        isApprover
          ? "Run the governed journey and store its runs, artifacts, and gates"
          : `${personaLabel(persona)} can't approve — switch to Lead, BA, Architect, or CISO`
      }
    >
      {persist.isPending ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Play className="h-3.5 w-3.5" />
      )}
      {persist.isPending ? "Persisting…" : "Run + persist journey"}
    </Button>
  );

  return (
    <div className="space-y-2">
      <MetricsPanel
        data={metrics.data}
        isLoading={metrics.isLoading || !ready}
        isError={metrics.isError}
        errorMsg={metrics.error instanceof Error ? metrics.error.message : undefined}
        selectedPersona={persona}
        action={persistButton}
        emptyState={
          <>
            No stored runs for this project yet.{" "}
            {isApprover
              ? "Run the governed journey to populate its cost dashboard."
              : `Switch to an approver persona (Lead / BA / Architect / CISO) to run it — you're viewing as ${personaLabel(persona)}.`}
          </>
        }
      />
      {persist.isError && (
        <p className="text-xs text-red-600">
          {persist.error instanceof Error ? persist.error.message : "Failed to persist the journey."}
          {!isApprover && " (approver persona required)"}
        </p>
      )}
    </div>
  );
}
