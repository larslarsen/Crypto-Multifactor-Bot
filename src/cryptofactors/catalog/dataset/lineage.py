"""Lineage validation and cycle detection (MAN-001)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from cryptofactors.catalog.dataset.errors import LineageError, MissingInputError
from cryptofactors.catalog.dataset.models import DependencyKind, DependencyRef


def validate_dependencies(
    dependencies: Sequence[DependencyRef],
    *,
    raw_exists: Callable[[str], bool],
    dataset_exists: Callable[[str], bool],
    dataset_upstreams: Callable[[str], Sequence[str]],
) -> None:
    """Ensure all inputs exist and introducing this dataset would not form a cycle.

    ``dataset_upstreams(dataset_id)`` returns direct upstream dataset IDs already
    registered in the catalog.
    """
    seen_edges: set[tuple[str, str, str]] = set()
    upstream_datasets: list[str] = []

    for dep in dependencies:
        if not dep.id or not dep.role:
            raise LineageError(
                "dependency id and role must be non-empty",
                context={"dep": str(dep)},
            )
        edge = (dep.kind.value, dep.id, dep.role)
        if edge in seen_edges:
            raise LineageError(
                "duplicate dependency edge",
                context={"kind": dep.kind.value, "id": dep.id, "role": dep.role},
            )
        seen_edges.add(edge)

        if dep.kind is DependencyKind.RAW_OBJECT:
            if not dep.id.startswith("raw_"):
                raise LineageError(
                    "raw object id must start with raw_",
                    context={"id": dep.id},
                )
            if not raw_exists(dep.id):
                raise MissingInputError(
                    f"raw object not found: {dep.id}",
                    context={"raw_object_id": dep.id},
                )
        elif dep.kind is DependencyKind.DATASET:
            if not dep.id.startswith("ds_"):
                raise LineageError(
                    "dataset id must start with ds_",
                    context={"id": dep.id},
                )
            if not dataset_exists(dep.id):
                raise MissingInputError(
                    f"upstream dataset not found: {dep.id}",
                    context={"dataset_id": dep.id},
                )
            upstream_datasets.append(dep.id)
        else:
            raise LineageError(
                f"unsupported dependency kind: {dep.kind}",
                context={"kind": str(dep.kind)},
            )

    # Cycle detection: none of the upstreams may already reach a path that would
    # include a new node pointing back — for a new dataset_id we only need to ensure
    # the upstream graph itself is acyclic when edges are added. Detect if any
    # upstream already depends (transitively) on another that creates a cycle among
    # the closed set. For a brand-new id, cycles only arise if the declared
    # upstream graph already has a cycle, or if we later add an edge from ancestor
    # to new id (impossible at registration time). Still reject if walking
    # upstreams from any declared input re-encounters a node among declared inputs
    # in a way that indicates an existing cycle.

    # Stronger: if the new dataset_id is known and appears in any upstream closure,
    # that would be a cycle (retry / supersession cases).
    def closure(start: str) -> set[str]:
        seen: set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            for up in dataset_upstreams(node):
                if up in seen:
                    # back-edge within walk from start
                    continue
                stack.append(up)
        return seen

    # Detect existing cycles among catalog by DFS colors on each upstream root.
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> None:
        if node in visiting:
            raise LineageError(
                "lineage cycle detected among upstream datasets",
                context={"node": node},
            )
        if node in visited:
            return
        visiting.add(node)
        for up in dataset_upstreams(node):
            dfs(up)
        visiting.remove(node)
        visited.add(node)

    for u in upstream_datasets:
        dfs(u)
