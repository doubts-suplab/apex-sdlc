"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, AlertCircle, Plug } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { LLMProviderBadge } from "@/components/integrations/LLMProviderBadge";
import { IntegrationCard } from "@/components/integrations/IntegrationCard";
import { AddIntegrationDialog } from "@/components/integrations/AddIntegrationDialog";
import { useProjectIntegrations } from "@/lib/queries/integrations";
import { Integration, IntegrationType } from "@/types/integration";

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function IntegrationsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4].map((n) => (
        <div key={n} className="rounded-lg border bg-white p-5 space-y-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-8 w-24 rounded-md" />
        </div>
      ))}
    </div>
  );
}

// ─── Which integration types are expected ─────────────────────────────────────

const ALL_TYPES: IntegrationType[] = ["github", "jira", "rally", "confluence"];

// ─── Page content (client) ────────────────────────────────────────────────────

function IntegrationsContent({ projectId }: { projectId: string }) {
  const { data: integrations, isLoading, isError, error } = useProjectIntegrations(projectId);

  if (isLoading) return <IntegrationsSkeleton />;

  if (isError) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
        <AlertCircle className="h-5 w-5 shrink-0" />
        <div>
          <p className="font-medium text-sm">Failed to load integrations</p>
          <p className="text-xs mt-0.5 text-red-600">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  const integrationMap = new Map<IntegrationType, Integration>(
    (integrations ?? []).map((i) => [i.integration_type, i])
  );

  // Jira/Rally are mutually exclusive — show whichever is connected, or Jira as default card
  const trackerTypes: IntegrationType[] = ["jira", "rally"];
  const hasJira = integrationMap.has("jira");
  const hasRally = integrationMap.has("rally");

  // Build display list: github, tracker (jira or rally), confluence
  // If both jira and rally somehow exist, show both
  const displayTypes: IntegrationType[] = [
    "github",
    ...(hasRally && !hasJira ? (["rally"] as IntegrationType[]) : (["jira"] as IntegrationType[])),
    ...(hasRally && hasJira ? (["rally"] as IntegrationType[]) : []),
    "confluence",
  ];

  // Show empty state cards for types with no integration yet
  const notConnectedTypes = ALL_TYPES.filter(
    (t) => !integrationMap.has(t) && !trackerTypes.includes(t) ||
           (trackerTypes.includes(t) && !hasJira && !hasRally && t === "jira")
  );

  return (
    <div className="space-y-6">
      {/* Connected integrations */}
      {integrations && integrations.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
            Connected
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {displayTypes.map((type) => {
              const integration = integrationMap.get(type);
              if (!integration) return null;
              return (
                <IntegrationCard
                  key={integration.id}
                  integration={integration}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Available (not yet connected) */}
      {notConnectedTypes.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Available
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {notConnectedTypes.map((type) => {
              // Show a placeholder "not connected" card
              const placeholder: Integration = {
                id: `placeholder-${type}`,
                project_id: projectId,
                integration_type: type,
                config: {},
                enabled: false,
                last_synced_at: null,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              };
              return <IntegrationCard key={type} integration={placeholder} />;
            })}
          </div>
        </div>
      )}

      {(!integrations || integrations.length === 0) && notConnectedTypes.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-12 text-center">
          <Plug className="h-8 w-8 mx-auto text-slate-400 mb-3" />
          <p className="text-sm font-medium text-slate-600">No integrations yet</p>
          <p className="text-xs text-slate-400 mt-1">
            Connect GitHub, Jira, Rally, or Confluence to enable AI-powered workflows.
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const params = useParams();
  const projectId =
    typeof params.projectId === "string" ? params.projectId : "";

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Link
            href={`/projects/${projectId}`}
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to project
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Integrations
          </h1>
          <p className="text-sm text-slate-500">
            Connect external services to enable AI-driven SDLC automation.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <LLMProviderBadge />
          {projectId && <AddIntegrationDialog projectId={projectId} />}
        </div>
      </div>

      <Separator />

      {/* LLM provider info */}
      <div className="rounded-lg border bg-slate-50 px-4 py-3">
        <p className="text-xs text-slate-600">
          <span className="font-semibold">AI provider:</span> All agent runs in
          this project use the LLM provider shown above. To change the provider,
          update the{" "}
          <code className="font-mono text-slate-700 bg-slate-200 rounded px-1 py-0.5 text-[11px]">
            LLM_PROVIDER
          </code>{" "}
          environment variable and redeploy.
        </p>
      </div>

      {/* Integration cards */}
      {projectId && <IntegrationsContent projectId={projectId} />}
    </div>
  );
}
