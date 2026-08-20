"""Stable data contracts for replay bundles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SCHEMA_VERSION = "1.0"
Outcome = Literal["equivalent", "changed", "missing", "unexpected", "error"]


@dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None


@dataclass(frozen=True)
class Interaction:
    id: str
    request: Request
    response: Response
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayBundle:
    name: str
    interactions: tuple[Interaction, ...]
    schema_version: str = SCHEMA_VERSION
    bundle_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReplayBundle:
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema version: {data.get('schema_version')!r}")
        interactions = tuple(
            Interaction(
                id=item["id"],
                request=Request(**item["request"]),
                response=Response(**item["response"]),
                metadata=item.get("metadata", {}),
            )
            for item in data.get("interactions", [])
        )
        return cls(
            name=data["name"],
            interactions=interactions,
            schema_version=data["schema_version"],
            bundle_id=data.get("bundle_id", ""),
            metadata=data.get("metadata", {}),
        )
