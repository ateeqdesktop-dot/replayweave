from replayweave import (
    FixtureTransport,
    Interaction,
    ReplayBundle,
    Request,
    Response,
    bundle_from_interactions,
    replay_interaction,
    sanitize_bundle,
    semantic_diff,
)


def interaction() -> Interaction:
    return Interaction(
        id="checkout-1",
        request=Request(
            "POST",
            "https://example.test/checkout",
            {"Authorization": "Bearer secret", "Content-Type": "application/json"},
            {"email": "user@example.com", "token": "sk_test_1234567890123456"},
        ),
        response=Response(
            200, {"Content-Type": "application/json"}, {"ok": True, "request_id": "abc"}
        ),
    )


def test_semantic_diff_ignores_paths_and_tolerates_numbers() -> None:
    result = semantic_diff({"id": "a", "latency": 1.0}, {"id": "b", "latency": 1.01}, ("id",), 0.02)
    assert result.equivalent


def test_semantic_diff_explains_missing_and_unexpected() -> None:
    result = semantic_diff({"a": 1}, {"b": 2})
    assert result.outcome == "changed"
    assert {item.kind for item in result.differences} == {"missing", "unexpected"}


def test_sanitize_removes_headers_and_secret_patterns() -> None:
    bundle = bundle_from_interactions("demo", [interaction()])
    safe = sanitize_bundle(bundle)
    item = safe.interactions[0]
    assert item.request.headers["Authorization"] == "[REDACTED]"
    assert item.request.body["token"] == "[REDACTED]"
    assert safe.metadata["redactions"]


def test_fixture_replay_is_deterministic() -> None:
    item = interaction()
    transport = FixtureTransport((item,))
    result = replay_interaction(item, transport)
    assert result.status == "equivalent"


def test_bundle_round_trip() -> None:
    bundle = ReplayBundle(name="round-trip", interactions=(interaction(),))
    assert ReplayBundle.from_dict(bundle.to_dict()) == bundle


def test_strict_sanitization_rejects_unknown_secret() -> None:
    item = Interaction(
        id="secret",
        request=Request(
            "GET",
            "https://example.test",
            body={"value": "ghp_" + "abcdefghijklmnopqrstuvwxyz123456"},
        ),
        response=Response(200, body={"ok": True}),
    )
    safe = sanitize_bundle(bundle_from_interactions("secret", [item]))
    assert safe.interactions[0].request.body["value"] == "[REDACTED]"


def test_fixture_replay_reports_missing_request() -> None:
    item = interaction()
    other = Interaction(
        "other", Request("GET", "https://example.test/other"), Response(200, body={})
    )
    result = replay_interaction(item, FixtureTransport((other,)))
    assert result.status == "missing"
    assert result.error is not None


def test_replay_reports_status_change() -> None:
    expected = interaction()
    changed = Interaction(expected.id, expected.request, Response(201, body=expected.response.body))
    result = replay_interaction(expected, FixtureTransport((changed,)))
    assert result.status == "changed"
    assert "status changed" in (result.error or "")


def test_bundle_rejects_duplicate_ids() -> None:
    item = interaction()
    try:
        bundle_from_interactions("bad", [item, item])
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate IDs must be rejected")
