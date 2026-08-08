"use client";

import { useState } from "react";
import { Check, Copy, FileText } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { JourneyArtifact } from "@/types/journey";
import { cn } from "@/lib/utils";

/**
 * A clickable artifact chip that opens a dialog showing the artifact's full generated content.
 * The journey API returns each artifact's content inline, so this is fully offline — no extra fetch.
 */
export function ArtifactChip({ artifact }: { artifact: JourneyArtifact }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard may be unavailable (e.g. insecure context) — no-op, the content is still visible.
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          title={`${artifact.title} — click to view content`}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100"
        >
          <FileText className="h-3 w-3 text-slate-400" />
          <span className="font-mono">{artifact.name}</span>
          <span className="text-slate-400">·</span>
          <span className="text-slate-500">{artifact.kind}</span>
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="pr-8">{artifact.title}</DialogTitle>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
            <Badge variant="outline" className="border-slate-200 font-mono text-slate-600">
              {artifact.name}
            </Badge>
            <Badge variant="outline" className="border-slate-200 text-slate-600">
              {artifact.kind}
            </Badge>
            <Badge variant="outline" className="border-slate-200 text-slate-600">
              {artifact.format}
            </Badge>
          </div>
        </DialogHeader>
        <div className="relative">
          <Button
            variant="outline"
            size="sm"
            onClick={onCopy}
            className="absolute right-2 top-2 z-10 h-7 gap-1 bg-white text-xs"
          >
            {copied ? <Check className="h-3 w-3 text-green-600" /> : <Copy className="h-3 w-3" />}
            {copied ? "Copied" : "Copy"}
          </Button>
          <pre
            className={cn(
              "max-h-[60vh] overflow-auto rounded-md border border-slate-200 bg-slate-50 p-4",
              "whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-slate-800"
            )}
          >
            {artifact.content}
          </pre>
        </div>
      </DialogContent>
    </Dialog>
  );
}
