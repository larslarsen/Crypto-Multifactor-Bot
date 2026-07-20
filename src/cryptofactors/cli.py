from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, Optional, TypeVar

import typer
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from cryptofactors.evidence.repository import EvidenceRepository

_TModel = TypeVar("_TModel", bound=BaseModel)

app = typer.Typer(no_args_is_help=True, help="Crypto multifactor platform CLI")

catalog_app = typer.Typer(help="Control catalog operations")
evidence_app = typer.Typer(help="Evidence registry operations (EVD-001)")


@catalog_app.command("init")
def catalog_init(
    database: Path = typer.Option(
        ..., "--database", help="Path to the SQLite control database"
    ),
) -> None:
    """Initialize or update the control catalog by applying pending migrations."""
    from cryptofactors.catalog.runner import apply_migrations

    apply_migrations(database)
    typer.echo(f"Catalog initialized/updated: {database}")


@catalog_app.command("status")
def catalog_status(
    database: Path = typer.Option(
        ..., "--database", help="Path to the SQLite control database"
    ),
) -> None:
    """Show applied and pending migrations for the control catalog."""
    from cryptofactors.catalog.runner import get_status

    status = get_status(database)
    typer.echo("Applied:")
    for fname, info in status["applied"].items():
        typer.echo(f"  {fname}  {info['checksum'][:12]}  {info['applied_at']}")
    if status["pending"]:
        typer.echo("Pending:")
        for fname in status["pending"]:
            typer.echo(f"  {fname}")
    else:
        typer.echo("Pending: (none)")


app.add_typer(catalog_app, name="catalog")


def _repo(database: Path) -> "EvidenceRepository":
    from cryptofactors.evidence.repository import EvidenceRepository

    return EvidenceRepository(database)


def _fail(message: str) -> NoReturn:
    """Emit a stable CLI error and exit nonzero (no traceback)."""
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


def _load_json_object(path: Path) -> dict[str, object]:
    """Read a JSON object payload; map I/O and parse failures to nonzero exit."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _fail(f"cannot read payload: {exc}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        _fail(f"invalid JSON payload: {exc}")
    if not isinstance(data, dict):
        _fail("payload must be a JSON object")
    return data


def _parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp; require timezone awareness."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _fail(f"invalid ISO-8601 datetime: {value!r} ({exc})")
    if dt.tzinfo is None:
        _fail(f"datetime must be timezone-aware: {value!r}")
    return dt


def _fixed_utc_now() -> str:
    """Fixed-width UTC timestamp for registry audit fields."""
    utc = datetime.now(timezone.utc)
    return (
        f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d}"
        f"T{utc.hour:02d}:{utc.minute:02d}:{utc.second:02d}"
        f".{utc.microsecond:06d}Z"
    )


def _validate_model(model_cls: type[_TModel], data: dict[str, object]) -> _TModel:
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        _fail(f"invalid payload model: {exc}")


@evidence_app.command("list-hypotheses")
def evidence_list_hypotheses(
    database: Path = typer.Option(..., "--database", help="SQLite control database"),
) -> None:
    """List registered hypotheses."""
    from cryptofactors.evidence.repository import EvidenceRegistryError

    try:
        rows = _repo(database).list_hypotheses()
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(json.dumps(rows, indent=2, sort_keys=True))


@evidence_app.command("show-hypothesis")
def evidence_show_hypothesis(
    hypothesis_id: str = typer.Argument(..., help="Hypothesis ID (H-NNN)"),
    database: Path = typer.Option(..., "--database", help="SQLite control database"),
) -> None:
    """Show versions and decisions for one hypothesis."""
    from cryptofactors.evidence.repository import EvidenceRegistryError

    try:
        data = _repo(database).show_hypothesis(hypothesis_id)
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(json.dumps(data, indent=2, sort_keys=True, default=str))


@evidence_app.command("list-evidence")
def evidence_list_evidence(
    database: Path = typer.Option(..., "--database", help="SQLite control database"),
) -> None:
    """List registered evidence items."""
    from cryptofactors.evidence.repository import EvidenceRegistryError

    try:
        rows = _repo(database).list_evidence()
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(json.dumps(rows, indent=2, sort_keys=True))


@evidence_app.command("register-hypothesis")
def evidence_register_hypothesis(
    payload: Path = typer.Option(
        ..., "--payload", help="JSON file with HypothesisVersion fields"
    ),
    database: Path = typer.Option(..., "--database", help="SQLite control database"),
    actor: str = typer.Option(..., "--actor", help="Registering actor"),
) -> None:
    """Register an immutable hypothesis version from a JSON payload."""
    from cryptofactors.evidence.models import HypothesisVersion
    from cryptofactors.evidence.repository import EvidenceRegistryError

    data = _load_json_object(payload)
    hyp = _validate_model(HypothesisVersion, data)
    try:
        digest = _repo(database).register_hypothesis(
            hyp, actor=actor, created_at=_fixed_utc_now()
        )
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(f"registered {hyp.hypothesis_id} v{hyp.version} content_sha256={digest}")


@evidence_app.command("add-evidence")
def evidence_add_evidence(
    payload: Path = typer.Option(
        ..., "--payload", help="JSON file with EvidenceItem fields"
    ),
    database: Path = typer.Option(..., "--database", help="SQLite control database"),
) -> None:
    """Register an immutable evidence item."""
    from cryptofactors.evidence.models import EvidenceItem
    from cryptofactors.evidence.repository import EvidenceRegistryError

    data = _load_json_object(payload)
    item = _validate_model(EvidenceItem, data)
    try:
        _repo(database).add_evidence(item)
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(f"registered evidence {item.evidence_id}")


@evidence_app.command("link-evidence")
def evidence_link_evidence(
    payload: Path = typer.Option(
        ..., "--payload", help="JSON file with HypothesisEvidenceLink fields"
    ),
    database: Path = typer.Option(..., "--database", help="SQLite control database"),
) -> None:
    """Link evidence to a hypothesis version."""
    from cryptofactors.evidence.models import HypothesisEvidenceLink
    from cryptofactors.evidence.repository import EvidenceRegistryError

    data = _load_json_object(payload)
    link = _validate_model(HypothesisEvidenceLink, data)
    try:
        _repo(database).link_evidence(link)
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(
        f"linked {link.evidence_id} -> {link.hypothesis_id} v{link.hypothesis_version}"
    )


@evidence_app.command("snapshot")
def evidence_snapshot(
    hypothesis_id: str = typer.Option(..., "--hypothesis-id"),
    version: int = typer.Option(..., "--version", min=1),
    database: Path = typer.Option(..., "--database"),
    as_of: Optional[str] = typer.Option(
        None, "--as-of", help="ISO-8601 UTC timestamp (default: now)"
    ),
) -> None:
    """Build or reuse a deterministic evidence snapshot."""
    from cryptofactors.evidence.repository import EvidenceRegistryError

    when = _parse_utc(as_of) if as_of else datetime.now(timezone.utc)
    try:
        snap = _repo(database).build_snapshot(hypothesis_id, version, as_of=when)
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(
        json.dumps(
            {
                "snapshot_id": snap.snapshot_id,
                "content_sha256": snap.content_sha256,
                "link_count": len(snap.links),
            },
            indent=2,
            sort_keys=True,
        )
    )


@evidence_app.command("decide")
def evidence_decide(
    payload: Path = typer.Option(
        ..., "--payload", help="JSON file with HypothesisDecision fields"
    ),
    database: Path = typer.Option(..., "--database"),
) -> None:
    """Append an append-only decision event (promotion rules enforced)."""
    from cryptofactors.evidence.models import HypothesisDecision
    from cryptofactors.evidence.repository import EvidenceRegistryError

    data = _load_json_object(payload)
    decision = _validate_model(HypothesisDecision, data)
    try:
        _repo(database).append_decision(decision)
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(f"appended decision {decision.decision_id}")


@evidence_app.command("export")
def evidence_export(
    database: Path = typer.Option(..., "--database"),
    format: str = typer.Option("json", "--format", help="json|markdown"),
    output: Optional[Path] = typer.Option(None, "--output", help="Write to file"),
) -> None:
    """Export deterministic current-state JSON or Markdown."""
    from cryptofactors.evidence.repository import EvidenceRegistryError

    try:
        result = _repo(database).export_current_state(format)
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    if isinstance(result, bytes):
        text = result.decode("utf-8")
    else:
        text = result
    if output is not None:
        try:
            output.write_text(text, encoding="utf-8")
        except OSError as exc:
            _fail(f"cannot write export: {exc}")
        typer.echo(f"wrote {output}")
    else:
        typer.echo(text)


@evidence_app.command("seed")
def evidence_seed(
    database: Path = typer.Option(..., "--database"),
    yaml_path: Path = typer.Option(
        Path("research/evidence/hypotheses.yaml"),
        "--yaml",
        help="Seed hypotheses file",
    ),
    actor: str = typer.Option("seed", "--actor"),
) -> None:
    """Idempotently import research/evidence/hypotheses.yaml."""
    from cryptofactors.evidence.repository import (
        EvidenceRegistryError,
        seed_import_hypotheses,
    )

    try:
        n = seed_import_hypotheses(_repo(database), yaml_path, actor=actor)
    except EvidenceRegistryError as exc:
        _fail(str(exc))
    typer.echo(f"seed complete; newly registered versions: {n}")


app.add_typer(evidence_app, name="evidence")


@app.command()
def version() -> None:
    """Print the scaffold version."""
    from cryptofactors import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()

