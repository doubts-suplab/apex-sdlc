import { z } from "zod";

export const ProjectTypeSchema = z.enum([
  "spring-boot",
  "angular",
  "shared-lib",
  "mainframe",
  "python",
  "generic",
]);
export type ProjectType = z.infer<typeof ProjectTypeSchema>;

export const PhaseTypeSchema = z.enum([
  "requirements",
  "architecture",
  "development",
  "testing",
  "cicd",
  "docs",
  "governance",
]);
export type PhaseType = z.infer<typeof PhaseTypeSchema>;

export const ProjectStatusSchema = z.enum(["active", "paused", "archived"]);
export type ProjectStatus = z.infer<typeof ProjectStatusSchema>;

export const ProjectSchema = z.object({
  id: z.string().uuid(),
  organisation_id: z.string().uuid(),
  name: z.string(),
  slug: z.string(),
  description: z.string().nullable(),
  project_type: ProjectTypeSchema,
  github_repo: z.string().nullable(),
  jira_board_id: z.string().nullable(),
  current_phase: PhaseTypeSchema,
  status: ProjectStatusSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type Project = z.infer<typeof ProjectSchema>;

export const PersonaSchema = z.enum([
  "developer",
  "ba",
  "qa",
  "pm",
  "lead",
  "architect",
  "ciso",
]);
export type Persona = z.infer<typeof PersonaSchema>;

export const PHASE_ORDER: PhaseType[] = [
  "requirements",
  "architecture",
  "development",
  "testing",
  "cicd",
  "docs",
  "governance",
];

export const PHASE_LABELS: Record<PhaseType, string> = {
  requirements: "Requirements",
  architecture: "Architecture",
  development: "Development",
  testing: "Testing",
  cicd: "CI/CD",
  docs: "Docs",
  governance: "Governance",
};

export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  "spring-boot": "Spring Boot",
  angular: "Angular",
  "shared-lib": "Shared Lib",
  mainframe: "Mainframe",
  python: "Python",
  generic: "Generic",
};

export const PERSONA_LABELS: Record<Persona, string> = {
  developer: "Developer",
  ba: "Business Analyst",
  qa: "QA Engineer",
  pm: "Product Manager",
  lead: "Tech Lead",
  architect: "Architect",
  ciso: "CISO",
};
