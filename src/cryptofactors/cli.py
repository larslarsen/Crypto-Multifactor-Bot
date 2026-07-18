from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True, help="Crypto multifactor platform CLI")


@app.command()
def version() -> None:
    """Print the scaffold version."""
    from cryptofactors import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
