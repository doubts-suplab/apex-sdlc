"use client";

import Link from "next/link";
import { GitPullRequest, Zap, BarChart2, ArrowRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useProjectIntegrations } from "@/lib/queries/integrations";
import { Integration } from "@/types/integration";

interface LiveMetricsBarProps {
  projectId: string;
}

function StatChip({
  icon,
  label,
  className,
}: {
  icon: React.ReactNode;
  label: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm shadow-sm",
        className
      )}
    >
      {icon}
      <span className="text-slate-700 font-medium">{label}</span>
    </div>
  );
}

function GitHubChip({ integration }: { integration: Integration }) {
  const config = integration.config as Record<string, unknown>;
  const totalPrs = typeof config["total_prs"] === "number" ? config["total_prs"] : null;
  const aiAssistedPrs =
    typeof config["ai_assisted_prs"] === "number"
      ? config["ai_assisted_prs"]
      : null;

  const label =
    totalPrs !== null && aiAssistedPrs !== null
      ? `${aiAssistedPrs} / ${totalPrs} PRs AI-assisted`
      : "GitHub connected";

  return (
    <StatChip
      icon={
        <Badge className="bg-green-100 text-green-800 border-green-200 text-xs px-1.5 py-0 font-normal">
          <GitPullRequest className="h-3 w-3 mr-1" />
          GH
        </Badge>
      }
      label={label}
    />
  );
}

function SprintChip({
  integration,
}: {
  integration: Integration;
}) {
  const isRally = integration.integration_type === "rally";
  const config = integration.config as Record<string, unknown>;

  const iterationLabel = isRally ? "Iteration" : "Sprint";
  const name =
    typeof config["sprint_name"] === "string"
      ? config["sprint_name"]
      : typeof config["iteration_name"] === "string"
      ? config["iteration_name"]
      : null;

  const done =
    typeof config["done_sp"] === "number"
      ? config["done_sp"]
      : typeof config["accepted_points"] === "number"
      ? config["accepted_points"]
      : null;

  const total =
    typeof config["committed_sp"] === "number"
      ? config["committed_sp"]
      : typeof config["planned_velocity"] === "number"
      ? config["planned_velocity"]
      : null;

  const label =
    name !== null && done !== null && total !== null
      ? `${name} · ${done}/${total} SP done`
      : `${iterationLabel} connected`;

  return (
    <StatChip
      icon={
        <Badge className="bg-blue-100 text-blue-800 border-blue-200 text-xs px-1.5 py-0 font-normal">
          <Zap className="h-3 w-3 mr-1" />
          {isRally ? "Rally" : "Jira"}
        </Badge>
      }
      label={label}
    />
  );
}

function CoverageChip({ coverage }: { coverage: number }) {
  const isLow = coverage < 80;
  return (
    <StatChip
      icon={
        <Badge
          className={cn(
            "text-xs px-1.5 py-0 font-normal",
            isLow
              ? "bg-amber-100 text-amber-800 border-amber-200"
              : "bg-green-100 text-green-800 border-green-200"
          )}
        >
          <BarChart2 className="h-3 w-3 mr-1" />
          COV
        </Badge>
      }
      label={`${coverage}% coverage`}
    />
  );
}

export function LiveMetricsBar({ projectId }: LiveMetricsBarProps) {
  const { data: integrations, isLoading } = useProjectIntegrations(projectId);

  if (isLoading) {
    return (
      <div className="flex flex-wrap gap-3">
        <Skeleton className="h-10 w-48 rounded-md" />
        <Skeleton className="h-10 w-44 rounded-md" />
        <Skeleton className="h-10 w-36 rounded-md" />
      </div>
    );
  }

  if (!integrations || integrations.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <span>No integrations connected.</span>
        <Link
          href={`/projects/${projectId}/integrations`}
          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium transition-colors"
        >
          Connect integrations
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    );
  }

  const github = integrations.find(
    (i) => i.integration_type === "github" && i.enabled
  );
  const jira = integrations.find(
    (i) => i.integration_type === "jira" && i.enabled
  );
  const rally = integrations.find(
    (i) => i.integration_type === "rally" && i.enabled
  );
  const tracker = jira ?? rally;

  // Coverage is stored in GitHub config if available
  const coverageRaw =
    github?.config &&
    typeof (github.config as Record<string, unknown>)["coverage_pct"] === "number"
      ? (github.config as Record<string, number>)["coverage_pct"]
      : null;

  return (
    <div className="flex flex-wrap gap-3">
      {github && <GitHubChip integration={github} />}
      {tracker && <SprintChip integration={tracker} />}
      {coverageRaw !== null && <CoverageChip coverage={coverageRaw} />}
      <Link
        href={`/projects/${projectId}/integrations`}
        className="inline-flex items-center gap-1.5 rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-500 hover:border-slate-400 hover:text-slate-700 transition-colors"
      >
        Manage integrations
        <ArrowRight className="h-3 w-3" />
      </Link>
    </div>
  );
}
