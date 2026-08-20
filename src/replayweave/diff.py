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
    expected: Any,
    actual: Any,
    ignore_paths: tuple[str, ...] = (),
    numeric_tolerance: float = 0.0,
    unordered_paths: tuple[str, ...] = (),
    max_differences: int = 100,
) -> DiffResult:
    if numeric_tolerance < 0:
        raise ValueError("numeric_tolerance must be non-negative")
    if max_differences < 1:
        raise ValueError("max_differences must be positive")
    differences: list[Difference] = []
    _compare(
        expected,
        actual,
        "",
        tuple(ignore_paths),
        tuple(unordered_paths),
        numeric_tolerance,
        max_differences,
        differences,
    )
    return DiffResult("equivalent" if not differences else "changed", tuple(differences))


def _compare(
    expected: Any,
    actual: Any,
    path: str,
    ignored: tuple[str, ...],
    unordered: tuple[str, ...],
    tolerance: float,
    limit: int,
    out: list[Difference],
) -> None:
    if len(out) >= limit or _matches(path, ignored):
        return
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected.keys() - actual.keys():
            out.append(
                Difference(
                    _join(path, str(key)), "missing", expected[key], None, "expected key is missing"
                )
            )
            if len(out) >= limit:
                return
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
            if len(out) >= limit:
                return
        for key in expected.keys() & actual.keys():
            _compare(
                expected[key],
                actual[key],
                _join(path, str(key)),
                ignored,
                unordered,
                tolerance,
                limit,
                out,
            )
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if _matches(path, unordered):
            unmatched = list(actual)
            for expected_item in expected:
                match_index = None
                for index, actual_item in enumerate(unmatched):
                    candidate: list[Difference] = []
                    _compare(
                        expected_item,
                        actual_item,
                        _join(path, "*"),
                        ignored,
                        unordered,
                        tolerance,
                        limit,
                        candidate,
                    )
                    if not candidate:
                        match_index = index
                        break
                if match_index is None:
                    out.append(
                        Difference(
                            path or "$",
                            "missing",
                            expected_item,
                            None,
                            "missing unordered list item",
                        )
                    )
                else:
                    unmatched.pop(match_index)
                if len(out) >= limit:
                    return
            for actual_item in unmatched:
                out.append(
                    Difference(
                        path or "$",
                        "unexpected",
                        None,
                        actual_item,
                        "unexpected unordered list item",
                    )
                )
                if len(out) >= limit:
                    return
            return
        for index in range(min(len(expected), len(actual))):
            _compare(
                expected[index],
                actual[index],
                _join(path, str(index)),
                ignored,
                unordered,
                tolerance,
                limit,
                out,
            )
            if len(out) >= limit:
                return
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
            if len(out) >= limit:
                return
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


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    path_parts = path.split(".") if path else []
    for pattern in patterns:
        if _match_parts(path_parts, pattern.split(".") if pattern else []):
            return True
    return False


def _match_parts(path: list[str], pattern: list[str]) -> bool:
    if not pattern:
        return not path
    if pattern[0] == "**":
        return _match_parts(path, pattern[1:]) or bool(path) and _match_parts(path[1:], pattern)
    return (
        bool(path)
        and (pattern[0] == "*" or pattern[0] == path[0])
        and _match_parts(path[1:], pattern[1:])
    )


def _canonical(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


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
