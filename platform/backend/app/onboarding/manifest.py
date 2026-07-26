"""ProjectManifest — a Pydantic model mirroring the eeik manifest schema.

Mirrors ``eeik_assets/manifest-schema.json`` (source of truth:
eeik-bootstrap `eeik/schemas/manifest.schema.json`, canonical since eeik v1.4). Kept intentionally permissive on enums
(``str`` with documented allowed values) so a new eeik value never hard-breaks onboarding — the
capability resolver simply finds no packs for an unknown value. Required fields match the eeik schema's
``(required)`` markers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BackendSpec(BaseModel):
    language: str = Field(description="java | python | mixed")
    version: int | float | str | None = Field(default=None, description="e.g. 21, 25, 3.12")
    framework: str | None = None


class FrontendSpec(BaseModel):
    framework: str = "none"  # react | angular | none


class DatabaseSpec(BaseModel):
    type: str | None = None
    migration_tool: str = "flyway"
    orm: str | None = None


class MessagingSpec(BaseModel):
    broker: str = "none"
    pattern: str = "none"


class TechnologySpec(BaseModel):
    backend: BackendSpec
    frontend: FrontendSpec = Field(default_factory=FrontendSpec)
    database: DatabaseSpec = Field(default_factory=DatabaseSpec)
    messaging: MessagingSpec = Field(default_factory=MessagingSpec)


class ArchitectureSpec(BaseModel):
    style: str = Field(description="monolith | modular-monolith | microservices | event-driven | serverless | agentic")
    patterns: list[str] = Field(default_factory=list)
    api_style: str = "rest"


class CloudSpec(BaseModel):
    provider: str = Field(description="aws | azure | gcp | hybrid")
    infra_as_code: str = "cdk"
    regions: list[str] = Field(default_factory=list)
    multi_account: bool = True


class AiSpec(BaseModel):
    enabled: bool = False
    pattern: str = "none"
    framework: str = "none"
    foundation_model: str | None = None
    governance_required: bool = False
    memory_pattern: str = "none"


class GovernanceSpec(BaseModel):
    profile: str = Field(description="basic | standard | regulated | enterprise")
    reviews_required: list[str] = Field(default_factory=list)
    compliance_frameworks: list[str] = Field(default_factory=list)


class ProjectIdentity(BaseModel):
    name: str = Field(description="kebab-case unique identifier")
    description: str = ""
    owner: str = ""
    domain: str = Field(description="insurance | banking | healthcare | retail | generic")
    project_type: str = Field(description="greenfield | modernization | poc | mvp | enterprise-platform | agent-platform")


class ModernizationSpec(BaseModel):
    """Mirrors the eeik manifest-schema `modernization` object (source_platform, strategy, wave_approach).

    Field names/enums match eeik's canonical schema so ``model_dump`` round-trips validate against it
    (the schema is ``additionalProperties: false``). ``strategy`` has no default because eeik's enum has
    no "none" member — it is emitted only when set.
    """

    enabled: bool = False
    source_platform: str = "none"  # ibmi | rpg | cobol | mainframe | oracle-forms | vb6 | mixed | none
    strategy: str | None = None    # strangler-fig | rewrite | lift-and-shift | encapsulate | hybrid
    wave_approach: bool = True


class ProjectManifest(BaseModel):
    """A validated eeik project manifest. Extra keys (delivery, observability, …) are tolerated."""

    model_config = {"extra": "allow"}

    schema_version: str = "1.0"
    project: ProjectIdentity
    technology: TechnologySpec
    architecture: ArchitectureSpec
    cloud: CloudSpec
    ai: AiSpec = Field(default_factory=AiSpec)
    governance: GovernanceSpec
    modernization: ModernizationSpec = Field(default_factory=ModernizationSpec)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectManifest:
        """Validate a raw manifest dict (e.g. parsed from an eeik YAML) into a ProjectManifest."""
        return cls.model_validate(data)
