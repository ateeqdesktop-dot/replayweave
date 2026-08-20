"""Bundle serialization, validation, and stable request keys."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import Interaction, ReplayBundle, Request


def request_key(request: Request) -> str:
    payload = {
        "method": request.method.upper(),
        "url": request.url,
        "headers": {
            k.lower(): v
            for k, v in sorted(request.headers.items())
            if k.lower() not in {"date", "user-agent"}
        },
        "body": request.body,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()[:20]


def save_bundle(bundle: ReplayBundle, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(bundle.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_bundle(path: str | Path) -> ReplayBundle:
    source = Path(path)
    try:
        data: Any = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read bundle {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("bundle root must be a JSON object")
    bundle = ReplayBundle.from_dict(data)
    validate_bundle(bundle)
    return bundle


def validate_bundle(bundle: ReplayBundle) -> None:
    if not bundle.name.strip():
        raise ValueError("bundle name must not be empty")
    seen: set[str] = set()
    for interaction in bundle.interactions:
        if not interaction.id.strip():
            raise ValueError("interaction id must not be empty")
        if interaction.id in seen:
            raise ValueError(f"duplicate interaction id: {interaction.id}")
        seen.add(interaction.id)
        if not interaction.request.method.strip() or not interaction.request.url.strip():
            raise ValueError(f"invalid request in interaction {interaction.id}")
        if (
            not isinstance(interaction.response.status, int)
            or not 100 <= interaction.response.status <= 599
        ):
            raise ValueError(f"invalid response status in interaction {interaction.id}")


def bundle_from_interactions(
    name: str, interactions: list[Interaction], metadata: dict[str, Any] | None = None
) -> ReplayBundle:
    bundle = ReplayBundle(name=name, interactions=tuple(interactions), metadata=metadata or {})
    validate_bundle(bundle)
    return bundle
