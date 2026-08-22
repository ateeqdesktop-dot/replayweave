"""Optional pytest integration for ReplayWeave bundles."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from .bundle import load_bundle
from .replay import FixtureTransport, ReplayResult, replay_interaction
from .report import ReplayReport, build_report

pytest: Any = importlib.import_module("pytest")


class ReplayWeaveAssertions:
    """Small pytest-facing facade with no global state."""

    def run(
        self,
        path: str | Path,
        *,
        ignore_paths: tuple[str, ...] = (),
        numeric_tolerance: float = 0.0,
        unordered_paths: tuple[str, ...] = (),
    ) -> ReplayReport:
        bundle = load_bundle(Path(path))
        transport = FixtureTransport(bundle.interactions)
        results: list[ReplayResult] = [
            replay_interaction(
                interaction,
                transport,
                ignore_paths,
                numeric_tolerance,
                unordered_paths,
            )
            for interaction in bundle.interactions
        ]
        return build_report(bundle.name, results)

    def assert_bundle(
        self,
        path: str | Path,
        *,
        ignore_paths: tuple[str, ...] = (),
        numeric_tolerance: float = 0.0,
        unordered_paths: tuple[str, ...] = (),
    ) -> ReplayReport:
        report = self.run(
            path,
            ignore_paths=ignore_paths,
            numeric_tolerance=numeric_tolerance,
            unordered_paths=unordered_paths,
        )
        if not report.equivalent:
            failures = "; ".join(
                f"{item['interaction_id']}: {item['status']}"
                for item in report.results
                if item["status"] != "equivalent"
            )
            pytest.fail(f"ReplayWeave regression in {report.bundle}: {failures}")
        return report


@pytest.fixture  # type: ignore[untyped-decorator]
def replayweave() -> ReplayWeaveAssertions:
    """Provide a stateless helper for replay assertions."""
    return ReplayWeaveAssertions()


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        "replayweave: marks a test that asserts a ReplayWeave bundle",
    )
