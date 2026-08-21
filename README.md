# ReplayWeave

[![CI](https://github.com/ateeqdesktop-dot/replayweave/actions/workflows/ci.yml/badge.svg)](https://github.com/ateeqdesktop-dot/replayweave/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Capture behavior once. Replay it safely. Gate regressions before production.**

ReplayWeave is a local-first, CI-first toolkit for turning distributed workflow runs into sanitized, reviewable replay bundles. It replays fixtures without network access and reports semantic JSON regressions without requiring a hosted observability platform.

## Why ReplayWeave?

A unit test can prove that a function works, while a real workflow still regresses because a downstream response changed, a field became nullable, or a tool call was omitted. Existing projects solve adjacent problems: VCR.py records HTTP cassettes, Pact verifies consumer/provider contracts, GoReplay replays live traffic, and Langfuse provides LLM observability. ReplayWeave focuses on the developer handoff between those worlds: **capture a meaningful run, sanitize it, replay it, and make a transparent CI decision**.

The MVP deliberately stays small. It is not a hosted dashboard, a traffic sniffer, a contract broker, or an LLM platform. It is a portable artifact format plus a deterministic replay and semantic-diff core.

| Project | Primary strength | ReplayWeave distinction |
|---|---|---|
| [VCR.py](https://vcrpy.readthedocs.io/) | HTTP cassettes for deterministic tests | Adds a workflow-level bundle, sanitization gate, and semantic regression report |
| [Pact](https://github.com/pact-foundation/pact-js) | Consumer/provider contract verification | Does not require a broker and is not limited to a provider contract lifecycle |
| [GoReplay](https://github.com/probelabs/goreplay) | Live HTTP traffic capture and shadow replay | Starts from explicit, reviewable artifacts instead of production packet capture |
| [Langfuse](https://github.com/langfuse/langfuse) | LLM observability and evaluation platform | Runs locally without a hosted observability service or database |

These projects are complementary rather than interchangeable. ReplayWeave is intentionally the narrow layer that turns a selected run into a safe, portable CI decision.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

# Import a sanitized, reviewable bundle from HAR or normalized JSONL.
replayweave import capture.har capture.bundle.json --format har

# Validate that the example bundle is safe.
replayweave check examples/checkout.bundle.json

# Replay entirely offline against the recorded fixture.
replayweave replay examples/checkout.bundle.json --mode fixture

# Emit a stable machine-readable CI report without response payloads.
replayweave replay examples/checkout.bundle.json --json-output

# Compare two JSON documents, ignore a volatile field, and treat an array as unordered.
replayweave diff baseline.json observed.json \\
  --ignore-path request_id \\
  --unordered-path items
```

The fixture command prints an interaction result and a deterministic aggregate summary:

```text
checkout-1: equivalent
summary: 1/1 equivalent
```

With `--json-output`, the command emits a stable report containing `total`, `passed`, `failed`, `outcomes`, per-interaction statuses, `equivalent`, and `exit_code`. Response payloads are never copied into the report, making it suitable for CI artifacts without turning logs into a data-exfiltration channel.

## Bundle model

A bundle is a versioned JSON document containing a human-readable name, stable interaction IDs, request/response envelopes, and optional metadata. It is intentionally diffable in Git. The public Python API can create and validate bundles:

```python
from replayweave import Interaction, Request, Response, bundle_from_interactions, save_bundle

bundle = bundle_from_interactions(
    'checkout',
    [Interaction(
        id='checkout-1',
        request=Request('POST', 'https://example.test/checkout', body={'items': []}),
        response=Response(200, body={'ok': True}),
    )],
)
save_bundle(bundle, 'checkout.bundle.json')
```

## Security by default

Replay bundles are treated as potentially public repository artifacts. ReplayWeave redacts authorization headers, cookies, API-key headers, common token formats, and configured body paths. `replayweave check` runs strict sanitization and exits non-zero if high-confidence secret patterns remain. Payloads are never uploaded, and the default logger does not print bodies.

```bash
replayweave sanitize raw.bundle.json safe.bundle.json \
  --ignore-path checkout-1.request.body.customer.email
replayweave check safe.bundle.json
```

## CI behavior

`replayweave replay` returns exit code `0` only when every interaction is semantically equivalent. Missing fixtures, transport errors, status changes, and JSON differences are non-zero. Use `--json-output` for a stable aggregate report and `--ignore-path`, `--unordered-path`, or `--numeric-tolerance` only when the rule is intentional and reviewed. Imported absolute URLs are normalized to origin-relative paths, and live HTTP replay blocks mutating methods and redirects by default.

## v0.3 release focus

The v0.3 release strengthens ReplayWeave as a CI primitive with an aggregate `ReplayReport` library contract, deterministic outcome counts, stable exit-code metadata, unordered-array policy support in replay, and package discovery metadata. The design remains artifact-first and local-only; capture adapters, OpenTelemetry import, and a pytest plugin remain explicit extension points rather than hidden runtime dependencies.

## Architecture

The core has four deliberately narrow boundaries: the bundle layer owns schema and serialization; the sanitizer owns redaction; the replay core consumes a transport protocol; and the diff engine produces structured, explainable differences. Fixture replay and HTTP replay use the same interaction contract. See [`docs/architecture.md`](docs/architecture.md) for data flow, security, performance, and extension decisions.

## Roadmap

The next release will add a capture middleware for FastAPI/httpx, an official pytest plugin, signed bundles, and OpenTelemetry GenAI span import. The current release already supports HAR/JSONL import, wildcard ignore paths, unordered arrays, and bounded semantic differences. Later milestones can add gRPC and queue adapters, signed bundles, parallel scenario replay, and optional local semantic policies. A hosted service is explicitly out of scope for the core project.

## Contributing

Contributions should include tests and a focused design note for changes to the bundle schema, transport protocol, or diff semantics. Run the same checks used in CI:

```bash
ruff check .
mypy src
pytest --cov=replayweave --cov-report=term-missing
```

## License

Apache-2.0. See [`LICENSE`](LICENSE).

## References

[1]: https://vcrpy.readthedocs.io/ "VCR.py documentation"
[2]: https://github.com/pact-foundation/pact-js "Pact JS repository"
[3]: https://github.com/probelabs/goreplay "GoReplay repository"
[4]: https://github.com/langfuse/langfuse "Langfuse repository"
