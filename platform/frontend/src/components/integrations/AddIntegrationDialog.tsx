"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  GitBranch,
  Trello,
  FileText,
  Layers,
  Plus,
  ChevronLeft,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAddIntegration } from "@/lib/queries/integrations";
import { IntegrationType } from "@/types/integration";

// ─── Type selection cards ─────────────────────────────────────────────────────

interface TypeOption {
  type: IntegrationType;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

const TYPE_OPTIONS: TypeOption[] = [
  {
    type: "github",
    label: "GitHub",
    description: "Connect a GitHub repository for PR reviews and metrics",
    icon: <GitBranch className="h-6 w-6" />,
    color: "border-slate-300 hover:border-slate-900",
  },
  {
    type: "jira",
    label: "Jira",
    description: "Sync sprints, stories, and board data from Jira",
    icon: <Trello className="h-6 w-6 text-blue-600" />,
    color: "border-slate-300 hover:border-blue-500",
  },
  {
    type: "rally",
    label: "Rally",
    description: "Connect CA Agile Central for iteration tracking",
    icon: <Layers className="h-6 w-6 text-orange-500" />,
    color: "border-slate-300 hover:border-orange-500",
  },
  {
    type: "confluence",
    label: "Confluence",
    description: "Publish AI-generated artifacts to Confluence spaces",
    icon: <FileText className="h-6 w-6 text-teal-600" />,
    color: "border-slate-300 hover:border-teal-500",
  },
];

// ─── Per-type Zod schemas ─────────────────────────────────────────────────────

const GitHubFormSchema = z.object({
  repo: z.string().min(3, "Enter repo as org/repo").regex(/^[\w.-]+\/[\w.-]+$/, {
    message: 'Must be in the format "org/repo"',
  }),
  webhook_secret: z.string().optional(),
});

const JiraFormSchema = z.object({
  project_key: z.string().min(1, "Project key is required").toUpperCase(),
  board_id: z.string().min(1, "Board ID is required"),
});

const RallyFormSchema = z.object({
  project_oid: z.string().min(1, "Project OID is required"),
  workspace_oid: z.string().min(1, "Workspace OID is required"),
});

const ConfluenceFormSchema = z.object({
  space_key: z.string().min(1, "Space key is required"),
});

type GitHubFormValues = z.infer<typeof GitHubFormSchema>;
type JiraFormValues = z.infer<typeof JiraFormSchema>;
type RallyFormValues = z.infer<typeof RallyFormSchema>;
type ConfluenceFormValues = z.infer<typeof ConfluenceFormSchema>;

// ─── Per-type form fields ─────────────────────────────────────────────────────

function FieldRow({
  id,
  label,
  placeholder,
  optional,
  error,
  ...rest
}: {
  id: string;
  label: string;
  placeholder?: string;
  optional?: boolean;
  error?: string;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium text-slate-700">
        {label}
        {optional && (
          <span className="ml-1 text-xs text-slate-400 font-normal">
            (optional)
          </span>
        )}
      </label>
      <input
        id={id}
        placeholder={placeholder}
        className={cn(
          "w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-colors",
          error ? "border-red-400" : "border-slate-300"
        )}
        {...rest}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

function GitHubForm({
  projectId,
  onDone,
}: {
  projectId: string;
  onDone: () => void;
}) {
  const addIntegration = useAddIntegration();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<GitHubFormValues>({ resolver: zodResolver(GitHubFormSchema) });

  const onSubmit = async (values: GitHubFormValues) => {
    const config: Record<string, unknown> = { repo: values.repo };
    if (values.webhook_secret) config["webhook_secret"] = values.webhook_secret;
    await addIntegration.mutateAsync({
      projectId,
      integration_type: "github",
      config,
    });
    onDone();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <FieldRow
        id="gh-repo"
        label="Repository"
        placeholder="org/repo"
        error={errors.repo?.message}
        {...register("repo")}
      />
      <FieldRow
        id="gh-webhook-secret"
        label="Webhook secret"
        placeholder="Optional shared secret"
        optional
        error={errors.webhook_secret?.message}
        {...register("webhook_secret")}
      />
      <DialogFooter>
        <Button type="submit" disabled={isSubmitting} size="sm">
          {isSubmitting ? "Connecting…" : "Connect GitHub"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function JiraForm({
  projectId,
  onDone,
}: {
  projectId: string;
  onDone: () => void;
}) {
  const addIntegration = useAddIntegration();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<JiraFormValues>({ resolver: zodResolver(JiraFormSchema) });

  const onSubmit = async (values: JiraFormValues) => {
    await addIntegration.mutateAsync({
      projectId,
      integration_type: "jira",
      config: { project_key: values.project_key, board_id: values.board_id },
    });
    onDone();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <FieldRow
        id="jira-project-key"
        label="Project key"
        placeholder="e.g. APEX"
        error={errors.project_key?.message}
        {...register("project_key")}
      />
      <FieldRow
        id="jira-board-id"
        label="Board ID"
        placeholder="e.g. 42"
        error={errors.board_id?.message}
        {...register("board_id")}
      />
      <DialogFooter>
        <Button type="submit" disabled={isSubmitting} size="sm">
          {isSubmitting ? "Connecting…" : "Connect Jira"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function RallyForm({
  projectId,
  onDone,
}: {
  projectId: string;
  onDone: () => void;
}) {
  const addIntegration = useAddIntegration();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RallyFormValues>({ resolver: zodResolver(RallyFormSchema) });

  const onSubmit = async (values: RallyFormValues) => {
    await addIntegration.mutateAsync({
      projectId,
      integration_type: "rally",
      config: {
        project_oid: values.project_oid,
        workspace_oid: values.workspace_oid,
      },
    });
    onDone();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <FieldRow
        id="rally-project-oid"
        label="Project OID"
        placeholder="e.g. 12345678"
        error={errors.project_oid?.message}
        {...register("project_oid")}
      />
      <FieldRow
        id="rally-workspace-oid"
        label="Workspace OID"
        placeholder="e.g. 98765432"
        error={errors.workspace_oid?.message}
        {...register("workspace_oid")}
      />
      <DialogFooter>
        <Button type="submit" disabled={isSubmitting} size="sm">
          {isSubmitting ? "Connecting…" : "Connect Rally"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function ConfluenceForm({
  projectId,
  onDone,
}: {
  projectId: string;
  onDone: () => void;
}) {
  const addIntegration = useAddIntegration();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ConfluenceFormValues>({
    resolver: zodResolver(ConfluenceFormSchema),
  });

  const onSubmit = async (values: ConfluenceFormValues) => {
    await addIntegration.mutateAsync({
      projectId,
      integration_type: "confluence",
      config: { space_key: values.space_key },
    });
    onDone();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <FieldRow
        id="conf-space-key"
        label="Space key"
        placeholder="e.g. APEX"
        error={errors.space_key?.message}
        {...register("space_key")}
      />
      <DialogFooter>
        <Button type="submit" disabled={isSubmitting} size="sm">
          {isSubmitting ? "Connecting…" : "Connect Confluence"}
        </Button>
      </DialogFooter>
    </form>
  );
}

// ─── Main dialog ──────────────────────────────────────────────────────────────

interface AddIntegrationDialogProps {
  projectId: string;
}

export function AddIntegrationDialog({ projectId }: AddIntegrationDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<IntegrationType | null>(null);

  const handleDone = () => {
    setOpen(false);
    setSelectedType(null);
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) setSelectedType(null);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Connect Integration
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {selectedType
              ? `Configure ${INTEGRATION_LABELS[selectedType]}`
              : "Connect Integration"}
          </DialogTitle>
          <DialogDescription>
            {selectedType
              ? "Fill in the details below to connect this integration."
              : "Select an integration type to get started."}
          </DialogDescription>
        </DialogHeader>

        {!selectedType ? (
          /* Step 1: type selection */
          <div className="grid grid-cols-2 gap-3 py-2">
            {TYPE_OPTIONS.map((opt) => (
              <button
                key={opt.type}
                type="button"
                onClick={() => setSelectedType(opt.type)}
                className={cn(
                  "flex flex-col items-start gap-2 rounded-lg border-2 p-4 text-left transition-all",
                  opt.color
                )}
              >
                {opt.icon}
                <span className="font-semibold text-sm text-slate-900">
                  {opt.label}
                </span>
                <span className="text-xs text-slate-500 leading-snug">
                  {opt.description}
                </span>
              </button>
            ))}
          </div>
        ) : (
          /* Step 2: form for chosen type */
          <div className="py-2">
            <button
              type="button"
              onClick={() => setSelectedType(null)}
              className="mb-4 flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition-colors"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Back
            </button>

            {selectedType === "github" && (
              <GitHubForm projectId={projectId} onDone={handleDone} />
            )}
            {selectedType === "jira" && (
              <JiraForm projectId={projectId} onDone={handleDone} />
            )}
            {selectedType === "rally" && (
              <RallyForm projectId={projectId} onDone={handleDone} />
            )}
            {selectedType === "confluence" && (
              <ConfluenceForm projectId={projectId} onDone={handleDone} />
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── Label map (exported for reuse) ──────────────────────────────────────────

const INTEGRATION_LABELS: Record<IntegrationType, string> = {
  github: "GitHub",
  jira: "Jira",
  rally: "Rally",
  confluence: "Confluence",
};
