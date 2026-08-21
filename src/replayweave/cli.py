"""Command line interface for ReplayWeave."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from .bundle import load_bundle, save_bundle
from .diff import render_diff, semantic_diff
from .importers import from_har, from_jsonl
from .replay import FixtureTransport, HttpTransport, replay_interaction
from .report import build_report
from .sanitize import sanitize_bundle


@click.group()
def main() -> None:
    """Capture, sanitize, replay, and gate distributed workflow behavior."""


@main.command("import")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("destination", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--format", "input_format", type=click.Choice(["har", "jsonl"]), default=None)
@click.option("--name", default=None, help="Bundle name; defaults to the input filename.")
def import_bundle(
    source: Path, destination: Path, input_format: str | None, name: str | None
) -> None:
    """Import SOURCE HAR or JSONL into a portable bundle."""
    selected = input_format or ("har" if source.suffix.lower() == ".har" else "jsonl")
    try:
        bundle = from_har(source, name) if selected == "har" else from_jsonl(source, name)
        save_bundle(bundle, destination)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"imported {len(bundle.interactions)} interaction(s) -> {destination}")


@main.command()
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("destination", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--ignore-path", multiple=True, help="JSON-like dot path to redact in addition to secrets."
)
@click.option(
    "--allow-unsafe", is_flag=True, help="Do not fail when high-confidence secrets remain."
)
def sanitize(
    source: Path, destination: Path, ignore_path: tuple[str, ...], allow_unsafe: bool
) -> None:
    """Sanitize SOURCE bundle into DESTINATION."""
    try:
        bundle = load_bundle(source)
        safe = sanitize_bundle(bundle, ignore_path, strict=not allow_unsafe)
        save_bundle(safe, destination)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"sanitized {len(safe.interactions)} interaction(s) -> {destination}")


@main.command()
@click.argument("baseline", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("observed", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--ignore-path", multiple=True)
@click.option("--numeric-tolerance", type=float, default=0.0, show_default=True)
@click.option("--unordered-path", multiple=True, help="Array path whose order should be ignored.")
@click.option("--json-output", is_flag=True)
def diff(
    baseline: Path,
    observed: Path,
    ignore_path: tuple[str, ...],
    numeric_tolerance: float,
    unordered_path: tuple[str, ...],
    json_output: bool,
) -> None:
    """Compare two JSON documents or bundles at a semantic level."""
    try:
        expected: Any = json.loads(baseline.read_text(encoding="utf-8"))
        actual: Any = json.loads(observed.read_text(encoding="utf-8"))
        result = semantic_diff(expected, actual, ignore_path, numeric_tolerance, unordered_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise click.ClickException(f"cannot compare inputs: {exc}") from exc
    if json_output:
        click.echo(
            json.dumps(
                {
                    "outcome": result.outcome,
                    "differences": [d.__dict__ for d in result.differences],
                },
                default=str,
            )
        )
    else:
        click.echo(render_diff(result))
    if not result.equivalent:
        raise click.exceptions.Exit(1)


@main.command()
@click.argument("bundle_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--mode", type=click.Choice(["fixture", "http"]), default="fixture", show_default=True
)
@click.option("--ignore-path", multiple=True)
@click.option("--numeric-tolerance", type=float, default=0.0, show_default=True)
@click.option("--unordered-path", multiple=True, help="Array path whose order should be ignored.")
@click.option("--json-output", is_flag=True)
def replay(
    bundle_path: Path,
    mode: str,
    ignore_path: tuple[str, ...],
    numeric_tolerance: float,
    unordered_path: tuple[str, ...],
    json_output: bool,
) -> None:
    """Replay a bundle and gate on semantic regressions."""
    try:
        bundle = load_bundle(bundle_path)
        transport = FixtureTransport(bundle.interactions) if mode == "fixture" else HttpTransport()
        results = [
            replay_interaction(item, transport, ignore_path, numeric_tolerance, unordered_path)
            for item in bundle.interactions
        ]
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    finally:
        if mode == "http" and "transport" in locals() and isinstance(transport, HttpTransport):
            transport.close()
    report = build_report(bundle.name, results)
    if json_output:
        click.echo(json.dumps(report.to_dict(), default=str, sort_keys=True))
    else:
        for item in results:
            suffix = f" ({item.error})" if item.error else ""
            click.echo(f"{item.interaction_id}: {item.status}{suffix}")
        click.echo(f"summary: {report.passed}/{report.total} equivalent")
    if not report.equivalent:
        raise click.exceptions.Exit(report.exit_code)


@main.command()
@click.argument("bundle_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def check(bundle_path: Path) -> None:
    """Validate a bundle and enforce strict sanitization."""
    try:
        bundle = load_bundle(bundle_path)
        sanitize_bundle(bundle, strict=True)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"safe: {bundle.name} ({len(bundle.interactions)} interaction(s))")
