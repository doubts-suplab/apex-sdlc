"""Seed an APEX organisation from a descriptor file — the generic replacement for hardcoded seeds.

Reads a tool-agnostic *organisation descriptor* (organisation identity + member projects, each naming a
``github_repo`` + ``manifest_path``) and ingests it via :class:`ManifestIngestService` using a
:class:`LocalWorkspaceResolver` rooted at a local multi-repo checkout. No organisation is named in code —
the composition is *data*. Idempotent, so it is safe to run repeatedly.

    python -m app.seeds.from_descriptor <descriptor.yaml> --workspace-root <dir>

Example (the Aether ecosystem, which lives entirely as data in its own hub repo):

    python -m app.seeds.from_descriptor \\
        ../../../aether-ecosystem/aether/ecosystem/ecosystem.yaml \\
        --workspace-root ../../../aether-ecosystem
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import yaml
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.onboarding.ingest import IngestReport, ManifestIngestService
from app.onboarding.resolver import LocalWorkspaceResolver

logger = get_logger(__name__)


async def seed_from_descriptor(
    db: AsyncSession,
    descriptor_path: str | Path,
    *,
    workspace_root: str | Path,
    mode: str | None = None,
) -> IngestReport:
    """Ingest an org descriptor from disk, resolving each member's manifest from a local checkout."""
    descriptor = yaml.safe_load(Path(descriptor_path).read_text()) or {}
    resolver = LocalWorkspaceResolver(workspace_root)
    service = ManifestIngestService(db, mode=mode)
    return await service.ingest_org(descriptor, resolver)


async def _main(descriptor_path: str, workspace_root: str, mode: str | None) -> None:
    # Imported lazily so `--help` works without a database configured.
    from app.core.config import get_settings
    from app.db.session import get_engine, init_engine

    init_engine(get_settings())
    factory = async_sessionmaker(bind=get_engine(), class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        report = await seed_from_descriptor(
            session, descriptor_path, workspace_root=workspace_root, mode=mode
        )
        await session.commit()

    print(f"Organisation '{report.organisation_slug}' — engine: {report.engine}")
    for p in report.projects:
        flag = "created" if p.created else "updated"
        print(f"  ✓ {p.slug:<16} {flag:<8} packs: {', '.join(p.resolved_packs) or '—'}")
    for s in report.skipped:
        print(f"  ✗ {s['slug']:<16} skipped — {s['reason']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed an APEX org from a descriptor file (offline).")
    parser.add_argument("descriptor", help="Path to an org descriptor YAML.")
    parser.add_argument(
        "--workspace-root",
        required=True,
        help="Local root holding sibling repo checkouts (to resolve each project-manifest.yaml).",
    )
    parser.add_argument(
        "--mode", default=None, help="eeik engine mode: sdk | mcp (default: env EEIK_MODE then sdk)."
    )
    args = parser.parse_args()
    asyncio.run(_main(args.descriptor, args.workspace_root, args.mode))


if __name__ == "__main__":
    main()
