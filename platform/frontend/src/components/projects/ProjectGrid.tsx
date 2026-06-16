"use client";

import { useProjects } from "@/lib/queries/projects";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { EmptyState } from "@/components/projects/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Plus, AlertCircle } from "lucide-react";

function ProjectCardSkeleton() {
  return (
    <div className="rounded-lg border bg-white p-6 space-y-4">
      <div className="space-y-2">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-2/3" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="h-5 w-24 rounded-full" />
      </div>
    </div>
  );
}

export function ProjectGrid() {
  const { data, isLoading, isError, error } = useProjects();

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            APEX SDLC Platform
          </h1>
          <p className="mt-2 text-slate-600">
            AI-powered SDLC for your organisation
          </p>
        </div>
        <Button disabled variant="default" className="gap-2">
          <Plus className="h-4 w-4" />
          Onboard Project
        </Button>
      </div>

      {isError && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700 mb-6">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <div>
            <p className="font-medium text-sm">Failed to load projects</p>
            <p className="text-xs mt-0.5 text-red-600">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <ProjectCardSkeleton />
          <ProjectCardSkeleton />
          <ProjectCardSkeleton />
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState message="No projects yet. Onboard your first project to get started." />
      ) : (
        <>
          <p className="text-sm text-slate-500 mb-4">
            {data.total} project{data.total !== 1 ? "s" : ""}
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
