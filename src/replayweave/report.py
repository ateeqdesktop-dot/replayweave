"""Stable aggregate reports for replay gates."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from .replay import ReplayResult


@dataclass(frozen=True)
class ReplayReport:
    """Machine-readable summary of a bundle replay run."""

    bundle: str
    total: int
    passed: int
    failed: int
    outcomes: dict[str, int]
    results: tuple[dict[str, Any], ...]

    @property
    def equivalent(self) -> bool:
        return self.failed == 0

    @property
    def exit_code(self) -> int:
        return 0 if self.equivalent else 1

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "equivalent": self.equivalent,
            "exit_code": self.exit_code,
        }


def build_report(bundle: str, results: Iterable[ReplayResult]) -> ReplayReport:
    """Build a deterministic aggregate without exposing response payloads."""
    items = tuple(results)
    outcomes: dict[str, int] = {}
    serialized: list[dict[str, Any]] = []
    for item in items:
        outcomes[item.status] = outcomes.get(item.status, 0) + 1
        serialized.append(
            {
                "interaction_id": item.interaction_id,
                "status": item.status,
                "error": item.error,
                "differences": [difference.__dict__ for difference in item.diff.differences]
                if item.diff
                else [],
            }
        )
    passed = outcomes.get("equivalent", 0)
    return ReplayReport(
        bundle=bundle,
        total=len(items),
        passed=passed,
        failed=len(items) - passed,
        outcomes=dict(sorted(outcomes.items())),
        results=tuple(serialized),
    )
