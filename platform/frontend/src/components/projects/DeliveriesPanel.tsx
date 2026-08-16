"use client";

import { AlertCircle, Github, ExternalLink, ListChecks } from "lucide-react";
import { useProjectDeliveries, usePublishDelivery } from "@/lib/queries/deliveries";
import {
  Delivery,
  DeliveryPriority,
  DeliveryStatus,
  DELIVERY_PRIORITY_LABELS,
  DELIVERY_STATUS_LABELS,
  isPublishable,
} from "@/types/delivery";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<DeliveryStatus, string> = {
  proposed: "bg-slate-100 text-slate-700 border-slate-200",
  planned: "bg-blue-100 text-blue-800 border-blue-200",
  in_progress: "bg-amber-100 text-amber-800 border-amber-200",
  done: "bg-green-100 text-green-800 border-green-200",
  dropped: "bg-slate-100 text-slate-400 border-slate-200",
};

const PRIORITY_COLORS: Record<DeliveryPriority, string> = {
  low: "bg-slate-100 text-slate-600 border-slate-200",
  medium: "bg-sky-100 text-sky-800 border-sky-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  critical: "bg-red-100 text-red-800 border-red-200",
};

function DeliveryRow({ delivery, projectId }: { delivery: Delivery; projectId: string }) {
  const publish = usePublishDelivery(projectId);
  const publishable = isPublishable(delivery);

  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-3 last:border-0">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-slate-900">{delivery.title}</span>
          <Badge variant="outline" className={cn("text-xs", STATUS_COLORS[delivery.status])}>
            {DELIVERY_STATUS_LABELS[delivery.status]}
          </Badge>
          <Badge variant="outline" className={cn("text-xs", PRIORITY_COLORS[delivery.priority])}>
            {DELIVERY_PRIORITY_LABELS[delivery.priority]}
          </Badge>
          {delivery.source === "agent" && (
            <Badge variant="outline" className="text-xs bg-violet-100 text-violet-800 border-violet-200">
              agent
            </Badge>
          )}
          {delivery.estimate_points !== null && (
            <span className="text-xs text-slate-400">{delivery.estimate_points} pts</span>
          )}
        </div>
        {delivery.description && (
          <p className="mt-1 text-xs text-slate-500 line-clamp-2">{delivery.description}</p>
        )}
        {delivery.target_ref && (
          <a
            href={delivery.target_ref}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
            {delivery.target_ref}
          </a>
        )}
        {publish.isError && (
          <p className="mt-1 text-xs text-red-600">
            {publish.error instanceof Error ? publish.error.message : "Publish failed"}
          </p>
        )}
      </div>
      {publishable && (
        <Button
          variant="outline"
          size="sm"
          className="shrink-0 gap-1.5"
          disabled={publish.isPending}
          onClick={() => publish.mutate(delivery.id)}
        >
          <Github className="h-4 w-4" />
          {publish.isPending ? "Publishing…" : "Publish"}
        </Button>
      )}
    </div>
  );
}

export function DeliveriesPanel({ projectId }: { projectId: string }) {
  const { data, isLoading, isError, error } = useProjectDeliveries(projectId);

  return (
    <div className="rounded-lg border bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <ListChecks className="h-4 w-4 text-slate-500" />
        <h2 className="text-base font-semibold text-slate-900">Deliveries</h2>
      </div>

      {isError && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <p className="text-xs">
            {error instanceof Error ? error.message : "Failed to load deliveries"}
          </p>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : !data || data.length === 0 ? (
        <p className="text-sm text-slate-500">
          No deliveries yet. Propose a backlog with the planning agent, then publish accepted items to
          GitHub.
        </p>
      ) : (
        <div>
          {data.map((delivery) => (
            <DeliveryRow key={delivery.id} delivery={delivery} projectId={projectId} />
          ))}
        </div>
      )}
    </div>
  );
}
