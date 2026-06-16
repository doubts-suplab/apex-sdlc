"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Project,
  ProjectType,
  PhaseType,
  ProjectStatus,
  PHASE_LABELS,
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

const PHASE_COLORS: Record<PhaseType, string> = {
  requirements: "bg-orange-100 text-orange-800 border-orange-200",
  architecture: "bg-indigo-100 text-indigo-800 border-indigo-200",
  development: "bg-blue-100 text-blue-800 border-blue-200",
  testing: "bg-teal-100 text-teal-800 border-teal-200",
  cicd: "bg-cyan-100 text-cyan-800 border-cyan-200",
  docs: "bg-slate-100 text-slate-800 border-slate-200",
  governance: "bg-rose-100 text-rose-800 border-rose-200",
};

const STATUS_INDICATOR: Record<ProjectStatus, string> = {
  active: "bg-green-500",
  paused: "bg-yellow-500",
  archived: "bg-slate-400",
};

const STATUS_LABEL: Record<ProjectStatus, string> = {
  active: "Active",
  paused: "Paused",
  archived: "Archived",
};

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link href={`/projects/${project.id}`} className="block group">
      <Card className="h-full transition-shadow group-hover:shadow-md">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base font-semibold text-slate-900 leading-snug group-hover:text-slate-700 transition-colors">
              {project.name}
            </CardTitle>
            <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
              <span
                className={cn(
                  "h-2 w-2 rounded-full shrink-0",
                  STATUS_INDICATOR[project.status]
                )}
                title={STATUS_LABEL[project.status]}
              />
              <span className="text-xs text-slate-500">
                {STATUS_LABEL[project.status]}
              </span>
            </div>
          </div>
          {project.description && (
            <CardDescription className="mt-1 line-clamp-2 text-xs">
              {project.description}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex flex-wrap gap-2">
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
                "text-xs font-medium",
                PHASE_COLORS[project.current_phase]
              )}
            >
              {PHASE_LABELS[project.current_phase]}
            </Badge>
          </div>
          {project.github_repo && (
            <a
              href={project.github_repo}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="mt-3 flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              <span className="truncate">{project.github_repo.replace("https://github.com/", "")}</span>
            </a>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
