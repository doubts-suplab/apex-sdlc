import { FolderOpen } from "lucide-react";

interface EmptyStateProps {
  message?: string;
}

export function EmptyState({
  message = "No projects yet. Onboard your first project to get started.",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
        <FolderOpen className="h-8 w-8 text-slate-400" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-slate-900">
        No projects found
      </h3>
      <p className="mt-2 max-w-sm text-sm text-slate-500">{message}</p>
    </div>
  );
}
