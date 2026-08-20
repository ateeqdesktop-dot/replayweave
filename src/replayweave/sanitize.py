"""Deterministic, local-only sanitization for replay bundles."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from .models import Interaction, ReplayBundle, Request, Response

SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key"}
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:sk|pk)_[a-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\b(?:ghp|github_pat)_[a-z0-9_]{20,}\b"),
    re.compile(r"(?i)\beyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),
)
REDACTED = "[REDACTED]"


def sanitize_bundle(
    bundle: ReplayBundle, ignore_paths: tuple[str, ...] = (), strict: bool = True
) -> ReplayBundle:
    redacted: list[str] = []
    interactions: list[Interaction] = []
    for interaction in bundle.interactions:
        request = _sanitize_request(interaction.request, interaction.id, redacted, ignore_paths)
        response = _sanitize_response(interaction.response, interaction.id, redacted, ignore_paths)
        interactions.append(replace(interaction, request=request, response=response))
    sanitized = replace(
        bundle,
        interactions=tuple(interactions),
        metadata={**bundle.metadata, "redactions": redacted},
    )
    if strict:
        leftovers = scan_for_secrets(sanitized)
        if leftovers:
            raise ValueError(
                f"strict sanitization found possible secrets at: {', '.join(leftovers)}"
            )
    return sanitized


def _sanitize_request(
    request: Request, interaction_id: str, redacted: list[str], ignore_paths: tuple[str, ...]
) -> Request:
    headers = {}
    for key, value in request.headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            headers[key] = REDACTED
            redacted.append(f"{interaction_id}.request.headers.{key}")
        else:
            headers[key] = _sanitize_scalar(
                value, f"{interaction_id}.request.headers.{key}", redacted
            )
    body = _sanitize_value(request.body, f"{interaction_id}.request.body", redacted, ignore_paths)
    return replace(request, headers=headers, body=body)


def _sanitize_response(
    response: Response, interaction_id: str, redacted: list[str], ignore_paths: tuple[str, ...]
) -> Response:
    headers = {}
    for key, value in response.headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            headers[key] = REDACTED
            redacted.append(f"{interaction_id}.response.headers.{key}")
        else:
            headers[key] = _sanitize_scalar(
                value, f"{interaction_id}.response.headers.{key}", redacted
            )
    body = _sanitize_value(response.body, f"{interaction_id}.response.body", redacted, ignore_paths)
    return replace(response, headers=headers, body=body)


def _sanitize_value(
    value: Any, path: str, redacted: list[str], ignore_paths: tuple[str, ...]
) -> Any:
    if path in ignore_paths:
        redacted.append(path)
        return REDACTED
    if isinstance(value, dict):
        return {
            str(k): _sanitize_value(v, f"{path}.{k}", redacted, ignore_paths)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            _sanitize_value(v, f"{path}.{i}", redacted, ignore_paths) for i, v in enumerate(value)
        ]
    if isinstance(value, str):
        return _sanitize_scalar(value, path, redacted)
    return value


def _sanitize_scalar(value: str, path: str, redacted: list[str]) -> str:
    result = value
    for pattern in SECRET_PATTERNS:
        if pattern.search(result):
            result = pattern.sub(REDACTED, result)
            redacted.append(path)
    return result


def scan_for_secrets(bundle: ReplayBundle) -> list[str]:
    findings: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}.{index}")
        elif isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_PATTERNS):
            findings.append(path)

    visit(bundle.to_dict(), "bundle")
    return findings
