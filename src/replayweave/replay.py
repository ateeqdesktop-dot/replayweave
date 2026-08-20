"""Replay transports and deterministic interaction matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from .bundle import request_key
from .diff import DiffResult, semantic_diff
from .models import Interaction, Request, Response


class Transport(Protocol):
    def send(self, request: Request) -> Response: ...


class FixtureTransport:
    """Returns the recorded response for an exact request key."""

    def __init__(self, interactions: tuple[Interaction, ...]) -> None:
        self._responses = {request_key(item.request): item.response for item in interactions}

    def send(self, request: Request) -> Response:
        response = self._responses.get(request_key(request))
        if response is None:
            raise LookupError(f"no fixture matched request {request.method} {request.url}")
        return response


class HttpTransport:
    def __init__(self, timeout: float = 10.0) -> None:
        self._client = httpx.Client(timeout=timeout)

    def send(self, request: Request) -> Response:
        response = self._client.request(
            request.method,
            request.url,
            headers=request.headers,
            json=request.body if isinstance(request.body, (dict, list)) else None,
            content=request.body if isinstance(request.body, str) else None,
        )
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        return Response(status=response.status_code, headers=dict(response.headers), body=body)

    def close(self) -> None:
        self._client.close()


@dataclass(frozen=True)
class ReplayResult:
    interaction_id: str
    status: str
    diff: DiffResult | None = None
    error: str | None = None


def replay_interaction(
    interaction: Interaction,
    transport: Transport,
    ignore_paths: tuple[str, ...] = (),
    numeric_tolerance: float = 0.0,
) -> ReplayResult:
    try:
        actual = transport.send(interaction.request)
    except LookupError as exc:
        return ReplayResult(interaction.id, "missing", error=str(exc))
    except Exception as exc:  # transport boundaries must become reportable outcomes
        return ReplayResult(interaction.id, "error", error=f"{type(exc).__name__}: {exc}")
    if actual.status != interaction.response.status:
        return ReplayResult(
            interaction.id,
            "changed",
            diff=DiffResult("changed", ()),
            error=f"status changed: expected {interaction.response.status}, got {actual.status}",
        )
    result = semantic_diff(interaction.response.body, actual.body, ignore_paths, numeric_tolerance)
    return ReplayResult(interaction.id, result.outcome, result)
