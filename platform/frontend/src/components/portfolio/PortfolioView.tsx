"use client";

import Link from "next/link";
import { AlertCircle, LayoutGrid, GitBranch } from "lucide-react";
import { useProjects } from "@/lib/queries/projects";
import { usePortfolio } from "@/lib/queries/deliveries";
import {
  DELIVERY_PRIORITY_LABELS,
  DELIVERY_PRIORITY_ORDER,
  DELIVERY_STATUS_LABELS,
  DELIVERY_STATUS_ORDER,
  PortfolioSummary,
} from "@/types/delivery";
import { Skeleton } from "@/components/ui/skeleton";

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

function CountBar({
  title,
  counts,
  order,
  labels,
}: {
  title: string;
  counts: Record<string, number>;
  order: string[];
  labels: Record<string, string>;
}) {
  const total = order.reduce((sum, key) => sum + (counts[key] ?? 0), 0);
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">{title}</p>
      <div className="space-y-2">
        {order.map((key) => {
          const n = counts[key] ?? 0;
          const pct = total > 0 ? Math.round((n / total) * 100) : 0;
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-24 shrink-0 text-xs text-slate-600">{labels[key] ?? key}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-slate-400" style={{ width: `${pct}%` }} />
              </div>
              <span className="w-8 shrink-0 text-right text-xs font-medium text-slate-700">{n}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PortfolioBody({ summary }: { summary: PortfolioSummary }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Projects" value={summary.project_count} />
        <StatTile label="Deliveries" value={summary.delivery_count} />
        <StatTile label="Open" value={summary.open_count} />
        <StatTile label="Estimate (pts)" value={summary.total_estimate_points} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CountBar
          title="By status"
          counts={summary.by_status}
          order={DELIVERY_STATUS_ORDER}
          labels={DELIVERY_STATUS_LABELS}
        />
        <CountBar
          title="By priority"
          counts={summary.by_priority}
          order={DELIVERY_PRIORITY_ORDER}
          labels={DELIVERY_PRIORITY_LABELS}
        />
      </div>

      <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="px-4 py-3 font-medium">Project</th>
              <th className="px-4 py-3 font-medium">Repository</th>
              <th className="px-4 py-3 text-right font-medium">Deliveries</th>
              <th className="px-4 py-3 text-right font-medium">Open</th>
              <th className="px-4 py-3 text-right font-medium">Points</th>
            </tr>
          </thead>
          <tbody>
            {summary.projects.map((row) => (
              <tr key={row.project_id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                <td className="px-4 py-3">
                  <Link
                    href={`/projects/${row.project_id}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {row.name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-500">
                  {row.github_repo ? (
                    <span className="inline-flex items-center gap-1 font-mono text-xs">
                      <GitBranch className="h-3 w-3" />
                      {row.github_repo}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-300">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right text-slate-700">{row.delivery_count}</td>
                <td className="px-4 py-3 text-right text-slate-700">{row.open_count}</td>
                <td className="px-4 py-3 text-right text-slate-700">{row.estimate_points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function PortfolioView() {
  // The app has no org switcher yet; derive the org from the project registry.
  const projects = useProjects();
  const organisationId = projects.data?.items[0]?.organisation_id;
  const portfolio = usePortfolio(organisationId);

  const isLoading = projects.isLoading || (!!organisationId && portfolio.isLoading);
  const isError = projects.isError || portfolio.isError;
  const errorObj = projects.error ?? portfolio.error;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-8 flex items-center gap-2">
        <LayoutGrid className="h-6 w-6 text-slate-700" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Portfolio</h1>
          <p className="mt-1 text-slate-600">Cross-project delivery rollup for your organisation</p>
        </div>
      </div>

      {isError && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <p className="text-sm">
            {errorObj instanceof Error ? errorObj.message : "Failed to load portfolio"}
          </p>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : !organisationId ? (
        <p className="text-sm text-slate-500">
          No organisation found. Onboard a project to build a portfolio.
        </p>
      ) : portfolio.data ? (
        <PortfolioBody summary={portfolio.data} />
      ) : null}
    </div>
  );
}
