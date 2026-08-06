"use client";

import { AlertTriangle, Lock, ScrollText, ShieldAlert } from "lucide-react";
import { useAuthToken } from "@/lib/auth";
import { usePersona } from "@/lib/persona";
import {
  useAuditLog,
  usePiiEvents,
  usePolicyViolations,
} from "@/lib/queries/governance";
import { PERSONA_LABELS, Persona } from "@/types/project";
import { PHASE_LABELS } from "@/types/project";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Mirrors the backend _GOVERNANCE_PERSONAS (CISO/Lead-only).
const GOVERNANCE_PERSONAS: Persona[] = ["ciso", "lead"];

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-800 border-red-200",
  medium: "bg-amber-100 text-amber-800 border-amber-200",
  low: "bg-slate-100 text-slate-700 border-slate-200",
};

function personaLabel(key: string): string {
  return PERSONA_LABELS[key as Persona] ?? key;
}

/**
 * CISO/Lead governance view: the append-only AI-action audit log, PII-guard detections, and policy
 * violations for a project. Persona-gated in the UI (the API is gated too); non-privileged personas
 * see a locked placeholder rather than a guaranteed 403.
 */
export function GovernancePanel({ projectId }: { projectId: string }) {
  const { persona } = usePersona();
  const { ready } = useAuthToken();
  const privileged = GOVERNANCE_PERSONAS.includes(persona);

  const audit = useAuditLog(projectId, ready && privileged);
  const pii = usePiiEvents(projectId, ready && privileged);
  const violations = usePolicyViolations(projectId, ready && privileged);

  if (!privileged) {
    return (
      <div className="rounded-lg border border-dashed bg-slate-50 px-6 py-5">
        <div className="flex items-center gap-2 text-slate-500">
          <Lock className="h-4 w-4" />
          <span className="text-sm font-medium">Governance view</span>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          The audit log, PII events, and policy violations are restricted to CISO and Tech Lead
          personas. You&apos;re viewing as {personaLabel(persona)} — switch persona to inspect them.
        </p>
      </div>
    );
  }

  const auditItems = audit.data ?? [];
  const piiItems = pii.data ?? [];
  const violationItems = violations.data ?? [];
  const loading = !ready || audit.isLoading || pii.isLoading || violations.isLoading;
  const empty =
    !loading && auditItems.length === 0 && piiItems.length === 0 && violationItems.length === 0;

  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b px-6 py-4">
        <ShieldAlert className="h-4 w-4 text-slate-700" />
        <h2 className="text-base font-semibold text-slate-900">Governance</h2>
        <Badge variant="outline" className="ml-1 text-[10px] font-medium uppercase tracking-wide">
          {personaLabel(persona)}
        </Badge>
      </div>

      {loading ? (
        <p className="px-6 py-5 text-sm text-slate-400">Loading governance records…</p>
      ) : empty ? (
        <p className="px-6 py-5 text-sm text-slate-500">
          No governance records yet — run + persist the journey (or a phase) to populate the audit
          log, PII events, and policy checks.
        </p>
      ) : (
        <div className="grid grid-cols-1 divide-y lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          {/* Audit log */}
          <section className="px-6 py-4">
            <div className="mb-3 flex items-center gap-1.5 text-slate-700">
              <ScrollText className="h-3.5 w-3.5" />
              <span className="text-xs font-semibold uppercase tracking-wide">
                Audit log ({auditItems.length})
              </span>
            </div>
            <ul className="space-y-2">
              {auditItems.slice(0, 8).map((a) => (
                <li key={a.id} className="text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-slate-800">{PHASE_LABELS[a.phase]}</span>
                    <span
                      className={cn(
                        "font-medium",
                        a.auto_enforced ? "text-green-700" : "text-amber-700"
                      )}
                    >
                      {a.auto_enforced ? "auto" : "review"}
                    </span>
                  </div>
                  <p className="truncate text-slate-500" title={a.summary}>
                    {a.actor} · {a.action}
                  </p>
                </li>
              ))}
            </ul>
          </section>

          {/* PII events */}
          <section className="px-6 py-4">
            <div className="mb-3 flex items-center gap-1.5 text-slate-700">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span className="text-xs font-semibold uppercase tracking-wide">
                PII events ({piiItems.length})
              </span>
            </div>
            {piiItems.length === 0 ? (
              <p className="text-xs text-slate-400">None detected.</p>
            ) : (
              <ul className="space-y-2">
                {piiItems.slice(0, 8).map((e) => (
                  <li key={e.id} className="flex items-center justify-between gap-2 text-xs">
                    <span className="font-mono text-slate-700">{e.label}</span>
                    <span className="text-slate-500">
                      {e.action} · {e.direction} ×{e.occurrences}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Policy violations */}
          <section className="px-6 py-4">
            <div className="mb-3 flex items-center gap-1.5 text-slate-700">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span className="text-xs font-semibold uppercase tracking-wide">
                Policy ({violationItems.length})
              </span>
            </div>
            {violationItems.length === 0 ? (
              <p className="text-xs text-slate-400">No violations.</p>
            ) : (
              <ul className="space-y-2">
                {violationItems.slice(0, 8).map((v) => (
                  <li key={v.id} className="text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-slate-800">{v.policy}</span>
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[10px] font-medium capitalize",
                          SEVERITY_STYLES[v.severity] ?? SEVERITY_STYLES.low
                        )}
                      >
                        {v.severity}
                      </Badge>
                    </div>
                    <p className="truncate text-slate-500" title={v.detail}>
                      {PHASE_LABELS[v.phase]} · {v.status}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
