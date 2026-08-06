"""GitHub bootstrap — turn an emitted repo tree into a create-repo plan (offline) or a real push.

``bootstrap_plan`` is pure: it summarises what *would* be created (repo name + the files), so the demo and
API can show the outcome without credentials. ``push_repo_tree`` is the credentialed action — it creates
the repo and commits each file via the GitHub client — and is only reached when a token is configured.
"""

from __future__ import annotations

from typing import Any


def bootstrap_plan(owner: str, repo: str, tree: dict[str, str]) -> dict[str, Any]:
    """A dry-run of the GitHub bootstrap: the target repo and the files that would be committed."""
    return {
        "action": "create_repository",
        "owner": owner,
        "repo": repo,
        "full_name": f"{owner}/{repo}",
        "file_count": len(tree),
        "files": sorted(tree.keys()),
        "executed": False,  # a real push happens only via push_repo_tree with a configured client
    }


async def push_repo_tree(client: Any, owner: str, repo: str, tree: dict[str, str]) -> dict[str, Any]:
    """Create the repo and commit every file (credentialed). Requires a GitHubClient with a token.

    Not exercised offline — the client's methods hit the GitHub API. Kept thin so the live path mirrors
    the dry-run: create the repository, then write each file through the contents API.
    """
    await client.create_repository(name=repo, private=True)
    for path, content in sorted(tree.items()):
        await client.put_file(repo=f"{owner}/{repo}", path=path, content=content,
                              message=f"scaffold: add {path}")
    return {**bootstrap_plan(owner, repo, tree), "executed": True}
