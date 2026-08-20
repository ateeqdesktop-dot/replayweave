"""Import normalized JSONL and HAR captures into portable replay bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .bundle import bundle_from_interactions
from .models import Interaction, ReplayBundle, Request, Response


def _json_or_text(value: str | None) -> Any:
    if value is None or value == "":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def relative_url(value: str) -> str:
    """Remove scheme and authority so a capture cannot choose the replay origin."""
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    return value if value.startswith("/") else f"/{value}"


def _headers(items: list[dict[str, Any]] | None) -> dict[str, str]:
    return {
        str(item.get("name", "")): str(item.get("value", ""))
        for item in items or []
        if item.get("name")
    }


def from_jsonl(path: str | Path, name: str | None = None) -> ReplayBundle:
    """Read one normalized interaction object per line."""
    interactions: list[Interaction] = []
    source = Path(path)
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item: Any = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"JSONL line {line_number} must be an object")
        request = Request(
            method=str(item.get("method", "GET")),
            url=relative_url(str(item.get("path", item.get("url", "/")))),
            headers={str(k): str(v) for k, v in (item.get("headers") or {}).items()},
            body=item.get("body"),
        )
        response_data = item.get("response") or {}
        response = Response(
            status=int(str(response_data.get("status", item.get("status", 200)))),
            headers={str(k): str(v) for k, v in (response_data.get("headers") or {}).items()},
            body=response_data.get("body", item.get("response_body")),
            duration_ms=response_data.get("duration_ms", item.get("duration_ms")),
        )
        interactions.append(
            Interaction(
                id=str(item.get("id", f"interaction-{line_number}")),
                request=request,
                response=response,
                metadata={"imported_from": "jsonl", **(item.get("metadata") or {})},
            )
        )
    if not interactions:
        raise ValueError("JSONL input contains no interactions")
    return bundle_from_interactions(name or source.stem, interactions, {"format": "jsonl"})


def from_har(path: str | Path, name: str | None = None) -> ReplayBundle:
    """Import HAR 1.2 entries while preserving only origin-relative requests."""
    source = Path(path)
    try:
        document: Any = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read HAR {source}: {exc}") from exc
    entries = document.get("log", {}).get("entries", []) if isinstance(document, dict) else []
    interactions: list[Interaction] = []
    for index, entry in enumerate(entries, 1):
        request_data = entry.get("request", {})
        response_data = entry.get("response", {})
        post_data = request_data.get("postData", {})
        content = response_data.get("content", {})
        body = post_data.get("text")
        response_body = content.get("text")
        interactions.append(
            Interaction(
                id=str(entry.get("_replayweave_id", f"har-{index}")),
                request=Request(
                    method=str(request_data.get("method", "GET")),
                    url=relative_url(str(request_data.get("url", "/"))),
                    headers=_headers(request_data.get("headers")),
                    body=_json_or_text(body),
                ),
                response=Response(
                    status=int(response_data.get("status", 200)),
                    headers=_headers(response_data.get("headers")),
                    body=_json_or_text(response_body),
                    duration_ms=entry.get("time"),
                ),
                metadata={"imported_from": "har"},
            )
        )
    if not interactions:
        raise ValueError("HAR contains no log.entries")
    return bundle_from_interactions(name or source.stem, interactions, {"format": "har"})
