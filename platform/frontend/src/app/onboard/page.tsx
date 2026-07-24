"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, CheckCircle2, Rocket } from "lucide-react";
import { useOnboardPreview, useOnboard } from "@/lib/queries/onboarding";
import {
  OnboardingManifest,
  OnboardingResult,
  OPTIONS,
  emptyManifest,
} from "@/types/onboarding";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Step = "form" | "preview" | "done";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400";

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
}) {
  return (
    <select className={inputCls} value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

function availabilityClass(a: string): string {
  if (a === "built") return "border-green-200 bg-green-50 text-green-700";
  if (a === "stub") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-slate-200 bg-slate-50 text-slate-500";
}

function PreviewPanel({ result }: { result: OnboardingResult }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-slate-600">Enters APEX at</span>
        <Badge variant="secondary" className="capitalize">
          {result.entry_phase}
        </Badge>
        {result.governance_required && (
          <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
            AI governance required
          </Badge>
        )}
      </div>

      <div>
        <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
          Capability packs ({result.packs.length})
        </div>
        <div className="flex flex-wrap gap-2">
          {result.packs.map((p) => (
            <span
              key={p.name}
              title={`selected by ${p.selected_by.join(", ")}`}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs",
                availabilityClass(p.availability)
              )}
            >
              <span className="font-mono">{p.name}</span>
              <span className="opacity-70">· {p.availability}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
            Reviews required
          </div>
          <p className="text-sm text-slate-600">
            {result.reviews_required.join(", ") || "none"}
          </p>
        </div>
        <div>
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
            Recommended agents
          </div>
          <p className="text-sm text-slate-600">{result.recommended_agents.join(", ")}</p>
        </div>
      </div>

      <div>
        <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
          Scaffold plan
        </div>
        <pre className="max-h-72 overflow-auto rounded-lg border bg-slate-50 p-3 text-xs text-slate-700">
          {result.scaffold_plan}
        </pre>
      </div>
    </div>
  );
}

export default function OnboardPage() {
  const [step, setStep] = useState<Step>("form");
  const [manifest, setManifest] = useState<OnboardingManifest>(emptyManifest());
  const [result, setResult] = useState<OnboardingResult | null>(null);

  const preview = useOnboardPreview();
  const onboard = useOnboard();

  const set = (patch: Partial<OnboardingManifest>) => setManifest((m) => ({ ...m, ...patch }));

  const runPreview = () => {
    preview.mutate(manifest, {
      onSuccess: (r) => {
        setResult(r);
        setStep("preview");
      },
    });
  };

  const runOnboard = () => {
    onboard.mutate(manifest, {
      onSuccess: (r) => {
        setResult(r);
        setStep("done");
      },
    });
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-6 py-8">
      <div>
        <div className="flex items-center gap-2 text-slate-500">
          <Rocket className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase tracking-wide">Onboarding</span>
        </div>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">Onboard a project</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Describe the project as an eeik manifest. APEX resolves its capability packs, generates a scaffold
          (<code>CLAUDE.md</code> + plan), and registers it at the Requirements phase — the entry to the
          spec-driven spine.
        </p>
      </div>

      {step === "form" && (
        <div className="space-y-6 rounded-lg border bg-white p-6 shadow-sm">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Project name">
              <input
                className={inputCls}
                placeholder="payment-gateway"
                value={manifest.project.name}
                onChange={(e) => set({ project: { ...manifest.project, name: e.target.value } })}
              />
            </Field>
            <Field label="Owner">
              <input
                className={inputCls}
                placeholder="payments-engineering"
                value={manifest.project.owner}
                onChange={(e) => set({ project: { ...manifest.project, owner: e.target.value } })}
              />
            </Field>
            <Field label="Description">
              <input
                className={inputCls}
                placeholder="One-line description"
                value={manifest.project.description}
                onChange={(e) =>
                  set({ project: { ...manifest.project, description: e.target.value } })
                }
              />
            </Field>
            <Field label="Domain">
              <Select
                value={manifest.project.domain}
                onChange={(v) => set({ project: { ...manifest.project, domain: v } })}
                options={OPTIONS.domain}
              />
            </Field>
            <Field label="Project type">
              <Select
                value={manifest.project.project_type}
                onChange={(v) => set({ project: { ...manifest.project, project_type: v } })}
                options={OPTIONS.project_type}
              />
            </Field>
            <Field label="Backend language">
              <Select
                value={manifest.technology.backend.language}
                onChange={(v) =>
                  set({
                    technology: {
                      ...manifest.technology,
                      backend: { ...manifest.technology.backend, language: v },
                    },
                  })
                }
                options={OPTIONS.backend_language}
              />
            </Field>
            <Field label="Backend framework">
              <Select
                value={manifest.technology.backend.framework ?? "spring-boot"}
                onChange={(v) =>
                  set({
                    technology: {
                      ...manifest.technology,
                      backend: { ...manifest.technology.backend, framework: v },
                    },
                  })
                }
                options={OPTIONS.backend_framework}
              />
            </Field>
            <Field label="Frontend">
              <Select
                value={manifest.technology.frontend.framework}
                onChange={(v) =>
                  set({ technology: { ...manifest.technology, frontend: { framework: v } } })
                }
                options={OPTIONS.frontend}
              />
            </Field>
            <Field label="Architecture">
              <Select
                value={manifest.architecture.style}
                onChange={(v) => set({ architecture: { ...manifest.architecture, style: v } })}
                options={OPTIONS.architecture}
              />
            </Field>
            <Field label="Cloud">
              <Select
                value={manifest.cloud.provider}
                onChange={(v) => set({ cloud: { ...manifest.cloud, provider: v } })}
                options={OPTIONS.cloud}
              />
            </Field>
            <Field label="AI pattern">
              <Select
                value={manifest.ai.pattern}
                onChange={(v) => set({ ai: { enabled: v !== "none", pattern: v } })}
                options={OPTIONS.ai_pattern}
              />
            </Field>
            <Field label="Governance profile">
              <Select
                value={manifest.governance.profile}
                onChange={(v) => set({ governance: { profile: v } })}
                options={OPTIONS.governance}
              />
            </Field>
          </div>

          {preview.isError && (
            <p className="text-sm text-red-600">
              {preview.error instanceof Error ? preview.error.message : "Preview failed"}
            </p>
          )}

          <div className="flex justify-end">
            <Button onClick={runPreview} disabled={!manifest.project.name || preview.isPending} className="gap-1.5">
              {preview.isPending ? "Resolving…" : "Preview scaffold"}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {step === "preview" && result && (
        <div className="space-y-6 rounded-lg border bg-white p-6 shadow-sm">
          <PreviewPanel result={result} />
          {onboard.isError && (
            <p className="text-sm text-red-600">
              {onboard.error instanceof Error ? onboard.error.message : "Onboard failed"}
            </p>
          )}
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep("form")} className="gap-1.5">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            <Button onClick={runOnboard} disabled={onboard.isPending} className="gap-1.5">
              {onboard.isPending ? "Onboarding…" : "Onboard project"}
              <Rocket className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {step === "done" && result && (
        <div className="space-y-5 rounded-lg border border-green-200 bg-green-50 p-6">
          <div className="flex items-center gap-2 text-green-800">
            <CheckCircle2 className="h-5 w-5" />
            <h2 className="text-lg font-semibold">{result.project_name} onboarded</h2>
          </div>
          <p className="text-sm text-green-800">
            Registered at the <strong>{result.entry_phase}</strong> phase with{" "}
            {result.packs.length} capability packs. The spec-driven spine can now run.
          </p>
          <div className="flex gap-3">
            <Link href="/journey">
              <Button variant="outline" className="gap-1.5 bg-white">
                See the reference journey
              </Button>
            </Link>
            <Link href="/">
              <Button variant="outline" className="bg-white">
                Back to projects
              </Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
