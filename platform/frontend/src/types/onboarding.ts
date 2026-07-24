import { z } from "zod";
// mirrors backend app/onboarding/scaffold.py (OnboardingResult) and app/onboarding/manifest.py

/** The manifest the wizard collects and POSTs (subset the backend ProjectManifest validates). */
export interface OnboardingManifest {
  schema_version: string;
  project: {
    name: string;
    description: string;
    owner: string;
    domain: string;
    project_type: string;
  };
  technology: {
    backend: { language: string; version?: string; framework?: string };
    frontend: { framework: string };
    database: { type?: string; migration_tool: string };
  };
  architecture: { style: string; api_style: string };
  cloud: { provider: string; infra_as_code: string };
  ai: { enabled: boolean; pattern: string };
  governance: { profile: string };
}

export const ResolvedPackSchema = z.object({
  name: z.string(),
  availability: z.string(),
  selected_by: z.array(z.string()),
});
export type ResolvedPack = z.infer<typeof ResolvedPackSchema>;

export const OnboardingResultSchema = z.object({
  project_name: z.string(),
  entry_phase: z.string(),
  packs: z.array(ResolvedPackSchema),
  reviews_required: z.array(z.string()),
  compliance_hints: z.array(z.string()),
  recommended_agents: z.array(z.string()),
  governance_required: z.boolean(),
  claude_md: z.string(),
  manifest_yaml: z.string(),
  scaffold_plan: z.string(),
  registration: z
    .object({
      name: z.string(),
      slug: z.string(),
      project_type: z.string(),
      current_phase: z.string(),
      status: z.string(),
    })
    .optional(),
});
export type OnboardingResult = z.infer<typeof OnboardingResultSchema>;

// Enum options for the wizard selects (mirror the eeik manifest schema allowed values).
export const OPTIONS = {
  domain: ["generic", "insurance", "banking", "healthcare", "retail"],
  project_type: ["greenfield", "modernization", "poc", "mvp", "enterprise-platform", "agent-platform"],
  backend_language: ["java", "python", "mixed"],
  backend_framework: ["spring-boot", "quarkus", "fastapi", "django"],
  frontend: ["none", "react", "angular"],
  database: ["postgresql", "aurora-postgresql", "dynamodb", "mysql", "db2", "oracle"],
  architecture: ["monolith", "modular-monolith", "microservices", "event-driven", "serverless", "agentic"],
  api_style: ["rest", "graphql", "grpc", "event", "mixed"],
  cloud: ["aws", "azure", "gcp", "hybrid"],
  iac: ["cdk", "terraform", "both", "none"],
  ai_pattern: ["none", "rag", "single-agent", "multi-agent", "enterprise-agent-platform"],
  governance: ["basic", "standard", "regulated", "enterprise"],
} as const;

export function emptyManifest(): OnboardingManifest {
  return {
    schema_version: "1.0",
    project: { name: "", description: "", owner: "", domain: "generic", project_type: "greenfield" },
    technology: {
      backend: { language: "java", version: "21", framework: "spring-boot" },
      frontend: { framework: "none" },
      database: { type: "aurora-postgresql", migration_tool: "flyway" },
    },
    architecture: { style: "microservices", api_style: "rest" },
    cloud: { provider: "aws", infra_as_code: "cdk" },
    ai: { enabled: false, pattern: "none" },
    governance: { profile: "standard" },
  };
}
