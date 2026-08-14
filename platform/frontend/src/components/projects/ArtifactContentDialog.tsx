"use client";

import { Loader2 } from "lucide-react";
import { useArtifactContent } from "@/lib/queries/phases";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  projectId: string;
  artifactId: string | null;
  artifactName: string | null;
  onClose: () => void;
}

/** Shows a stored artifact's content in a modal. Content is fetched on open (GET .../artifacts/{id}). */
export function ArtifactContentDialog({ projectId, artifactId, artifactName, onClose }: Props) {
  const { data, isLoading, isError, error } = useArtifactContent(projectId, artifactId);
  const open = artifactId !== null;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm">
            {data?.title || artifactName || "Artifact"}
          </DialogTitle>
          <DialogDescription>
            {data ? `${data.name} · ${data.kind} · v${data.version}` : "Loading stored content…"}
          </DialogDescription>
        </DialogHeader>
        {isLoading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading content…
          </div>
        ) : isError ? (
          <p className="py-6 text-sm text-red-600">
            {error instanceof Error ? error.message : "Failed to load artifact content."}
          </p>
        ) : (
          <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-xs text-slate-800">
            {data?.content}
          </pre>
        )}
      </DialogContent>
    </Dialog>
  );
}
