from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True, help="Crypto multifactor platform CLI")

catalog_app = typer.Typer(help="Control catalog operations")


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


@app.command()
def version() -> None:
    """Print the scaffold version."""
    from cryptofactors import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
