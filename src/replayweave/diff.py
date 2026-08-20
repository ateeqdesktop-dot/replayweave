"""Explainable semantic comparison for JSON-like values."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any

from .models import Outcome


@dataclass(frozen=True)
class Difference:
    path: str
    kind: str
    expected: Any
    actual: Any
    message: str


@dataclass(frozen=True)
class DiffResult:
    outcome: Outcome
    differences: tuple[Difference, ...] = ()

    @property
    def equivalent(self) -> bool:
        return self.outcome == "equivalent"


def semantic_diff(
    expected: Any, actual: Any, ignore_paths: tuple[str, ...] = (), numeric_tolerance: float = 0.0
) -> DiffResult:
    differences: list[Difference] = []
    _compare(expected, actual, "", set(ignore_paths), numeric_tolerance, differences)
    return DiffResult("equivalent" if not differences else "changed", tuple(differences))


def _compare(
    expected: Any,
    actual: Any,
    path: str,
    ignored: set[str],
    tolerance: float,
    out: list[Difference],
) -> None:
    if path in ignored:
        return
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected.keys() - actual.keys():
            out.append(
                Difference(
                    _join(path, str(key)), "missing", expected[key], None, "expected key is missing"
                )
            )
        for key in actual.keys() - expected.keys():
            out.append(
                Difference(
                    _join(path, str(key)),
                    "unexpected",
                    None,
                    actual[key],
                    "unexpected key was returned",
                )
            )
        for key in expected.keys() & actual.keys():
            _compare(expected[key], actual[key], _join(path, str(key)), ignored, tolerance, out)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        for index in range(min(len(expected), len(actual))):
            _compare(
                expected[index], actual[index], _join(path, str(index)), ignored, tolerance, out
            )
        for index in range(len(expected), len(actual)):
            out.append(
                Difference(
                    _join(path, str(index)),
                    "unexpected",
                    None,
                    actual[index],
                    "unexpected list item",
                )
            )
        for index in range(len(actual), len(expected)):
            out.append(
                Difference(
                    _join(path, str(index)), "missing", expected[index], None, "missing list item"
                )
            )
        return
    if (
        isinstance(expected, (int, float))
        and isinstance(actual, (int, float))
        and not isinstance(expected, bool)
        and not isinstance(actual, bool)
        and isclose(float(expected), float(actual), rel_tol=tolerance, abs_tol=tolerance)
    ):
        return
    if expected != actual:
        out.append(Difference(path or "$", "changed", expected, actual, "values differ"))


def _join(path: str, part: str) -> str:
    return f"{path}.{part}" if path else part


def render_diff(result: DiffResult) -> str:
    if result.equivalent:
        return "equivalent: no semantic differences"
    lines = [f"{result.outcome}: {len(result.differences)} difference(s)"]
    for difference in result.differences:
        lines.append(
            f"- {difference.path}: {difference.message} "
            f"(expected={difference.expected!r}, actual={difference.actual!r})"
        )
    return "\n".join(lines)
