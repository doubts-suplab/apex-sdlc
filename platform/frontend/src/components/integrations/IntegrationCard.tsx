"use client";

import { useState } from "react";
import {
  GitBranch,
  Trello,
  FileText,
  Layers,
  RefreshCw,
  Pencil,
  Trash2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useSyncIntegration } from "@/lib/queries/integrations";
import { Integration, IntegrationType } from "@/types/integration";

// ─── Icon map ────────────────────────────────────────────────────────────────

const INTEGRATION_ICONS: Record<IntegrationType, React.ReactNode> = {
  github: <GitBranch className="h-5 w-5" />,
  jira: <Trello className="h-5 w-5" />,
  rally: <Layers className="h-5 w-5" />,
  confluence: <FileText className="h-5 w-5" />,
};

const INTEGRATION_LABELS: Record<IntegrationType, string> = {
  github: "GitHub",
  jira: "Jira",
  rally: "Rally",
  confluence: "Confluence",
};

// ─── Config summary ───────────────────────────────────────────────────────────

function configSummary(
  type: IntegrationType,
  config: Record<string, unknown>
): string {
  switch (type) {
    case "github":
      return typeof config["repo"] === "string" ? config["repo"] : "";
    case "jira":
      return [
        config["project_key"] ? `Key: ${config["project_key"]}` : "",
        config["board_id"] ? `Board: ${config["board_id"]}` : "",
      ]
        .filter(Boolean)
        .join(" · ");
    case "rally":
      return [
        config["project_oid"] ? `Project: ${config["project_oid"]}` : "",
        config["workspace_oid"] ? `Workspace: ${config["workspace_oid"]}` : "",
      ]
        .filter(Boolean)
        .join(" · ");
    case "confluence":
      return config["space_key"]
        ? `Space: ${config["space_key"]}`
        : "";
    default:
      return "";
  }
}

function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  return `${Math.floor(diffHrs / 24)}d ago`;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface IntegrationCardProps {
  integration: Integration;
  onEdit?: (integration: Integration) => void;
  onRemove?: (integration: Integration) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function IntegrationCard({
  integration,
  onEdit,
  onRemove,
}: IntegrationCardProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const sync = useSyncIntegration();

  const label = INTEGRATION_LABELS[integration.integration_type];
  const icon = INTEGRATION_ICONS[integration.integration_type];
  const summary = configSummary(
    integration.integration_type,
    integration.config as Record<string, unknown>
  );

  const handleSync = () => {
    sync.mutate({
      projectId: integration.project_id,
      integrationType: integration.integration_type,
    });
  };

  const handleRemoveConfirmed = () => {
    setShowConfirm(false);
    onRemove?.(integration);
  };

  return (
    <>
      <Card className="flex flex-col">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-slate-600">{icon}</span>
              <span className="font-semibold text-slate-900">{label}</span>
            </div>
            {integration.enabled ? (
              <div className="flex items-center gap-1.5 text-xs text-green-700 font-medium">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                <span>
                  Connected
                  {integration.last_synced_at
                    ? ` · Last synced ${formatRelativeTime(integration.last_synced_at)}`
                    : ""}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs text-red-600 font-medium">
                <XCircle className="h-3.5 w-3.5 text-red-500" />
                <span>Not connected</span>
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="flex flex-col gap-3 flex-1">
          {summary && (
            <Badge
              variant="outline"
              className="w-fit text-xs font-mono text-slate-600 border-slate-200 bg-slate-50"
            >
              {summary}
            </Badge>
          )}

          <div className="flex items-center gap-2 mt-auto pt-2">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1"
              onClick={handleSync}
              disabled={sync.isPending || !integration.enabled}
            >
              <RefreshCw
                className={cn(
                  "h-3 w-3",
                  sync.isPending && "animate-spin"
                )}
              />
              Sync now
            </Button>

            {onEdit && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs gap-1"
                onClick={() => onEdit(integration)}
              >
                <Pencil className="h-3 w-3" />
                Edit
              </Button>
            )}

            {onRemove && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs gap-1 text-red-600 hover:text-red-700 hover:bg-red-50 ml-auto"
                onClick={() => setShowConfirm(true)}
              >
                <Trash2 className="h-3 w-3" />
                Remove
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Remove confirm dialog */}
      <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Remove {label} integration?</DialogTitle>
            <DialogDescription>
              This will disconnect {label} from this project. Agent runs that
              rely on this integration will stop working.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowConfirm(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleRemoveConfirmed}
            >
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
