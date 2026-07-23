"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertCircle, GitBranch, Trello, Calendar, Plug, Route } from "lucide-react";
import { useProject } from "@/lib/queries/projects";
import { SDLCTimeline } from "@/components/projects/SDLCTimeline";
import { LiveMetricsBar } from "@/components/projects/LiveMetricsBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  ProjectType,
  ProjectStatus,
  PROJECT_TYPE_LABELS,
} from "@/types/project";

const PROJECT_TYPE_COLORS: Record<ProjectType, string> = {
  "spring-boot": "bg-green-100 text-green-800 border-green-200",
  angular: "bg-red-100 text-red-800 border-red-200",
  "shared-lib": "bg-purple-100 text-purple-800 border-purple-200",
  mainframe: "bg-yellow-100 text-yellow-800 border-yellow-200",
  python: "bg-blue-100 text-blue-800 border-blue-200",
  generic: "bg-slate-100 text-slate-800 border-slate-200",
};

const STATUS_COLORS: Record<ProjectStatus, string> = {
  active: "bg-green-100 text-green-800 border-green-200",
  paused: "bg-yellow-100 text-yellow-800 border-yellow-200",
  archived: "bg-slate-100 text-slate-800 border-slate-200",
};

function ProjectDetailSkeleton() {
  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
        <div className="flex gap-2 mt-2">
          <Skeleton className="h-6 w-24 rounded-full" />
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
      </div>
      <div className="rounded-lg border bg-white p-6">
        <Skeleton className="h-5 w-32 mb-4" />
        <Skeleton className="h-16 w-full" />
      </div>
    </div>
  );
}

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = typeof params.projectId === "string" ? params.projectId : "";
  const { data: project, isLoading, isError, error } = useProject(projectId);

  if (isLoading) {
    return <ProjectDetailSkeleton />;
  }

  if (isError) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
        <AlertCircle className="h-5 w-5 shrink-0" />
        <div>
          <p className="font-medium text-sm">Failed to load project</p>
          <p className="text-xs mt-0.5 text-red-600">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-16 text-slate-500">
        <p>Project not found.</p>
      </div>
    );
  }

  const createdDate = new Date(project.created_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const updatedDate = new Date(project.updated_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            {project.name}
          </h1>
          {project.description && (
            <p className="mt-2 text-slate-600 max-w-2xl">{project.description}</p>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium",
                PROJECT_TYPE_COLORS[project.project_type]
              )}
            >
              {PROJECT_TYPE_LABELS[project.project_type]}
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium capitalize",
                STATUS_COLORS[project.status]
              )}
            >
              {project.status}
            </Badge>
            <span className="text-xs text-slate-400 font-mono">{project.slug}</span>
          </div>
        </div>

        <Link href={`/projects/${projectId}/integrations`} className="shrink-0">
          <Button variant="outline" size="sm" className="gap-1.5">
            <Plug className="h-4 w-4" />
            Integrations
          </Button>
        </Link>
      </div>

      {/* Live Metrics Bar */}
      <LiveMetricsBar projectId={projectId} />

      {/* SDLC Timeline */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900 mb-6">
          SDLC Timeline
        </h2>
        <SDLCTimeline currentPhase={project.current_phase} />
      </div>

      {/* Metrics & Info */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {project.github_repo && (
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-slate-500 mb-2">
              <GitBranch className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wide">
                Repository
              </span>
            </div>
            <a
              href={project.github_repo}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:text-blue-800 hover:underline break-all transition-colors"
            >
              {project.github_repo}
            </a>
          </div>
        )}

        {project.jira_board_id && (
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-slate-500 mb-2">
              <Trello className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wide">
                Jira Board
              </span>
            </div>
            <p className="text-sm text-slate-700 font-mono">
              {project.jira_board_id}
            </p>
          </div>
        )}

        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-slate-500 mb-2">
            <Calendar className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wide">
              Dates
            </span>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-slate-500">
              Created:{" "}
              <span className="text-slate-700 font-medium">{createdDate}</span>
            </p>
            <p className="text-xs text-slate-500">
              Updated:{" "}
              <span className="text-slate-700 font-medium">{updatedDate}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Phase agent runs & the governed journey */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-slate-700">
            <Route className="h-4 w-4" />
            <span className="text-sm font-semibold">Phase agent runs & artifacts</span>
          </div>
          <Link href="/journey">
            <Button variant="outline" size="sm" className="gap-1.5">
              <Route className="h-4 w-4" />
              View reference journey
            </Button>
          </Link>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Each SDLC phase is run by an AI agent on the governed agent-harness — the confidence gate
          decides what auto-enforces and what routes to a human. See the worked reference journey for a
          project walking all seven phases and producing real artifacts.
        </p>
      </div>
    </div>
  );
}
