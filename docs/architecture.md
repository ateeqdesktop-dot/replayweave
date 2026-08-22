# ReplayWeave Architecture Decision Record

## Product vision

ReplayWeave turns a meaningful system run into a portable, sanitized, replayable regression artifact. The artifact can be created locally, reviewed in a pull request, replayed without network access, and used as a deterministic CI gate. The first implementation targets HTTP and JSON while preserving an adapter boundary for gRPC, queues, and model providers.

## Problem statement

Distributed workflows fail in ways that ordinary unit tests do not capture. A request can succeed while a downstream call changes shape, a retry disappears, a tool invocation is reordered, or a response becomes semantically incompatible. Existing tools solve individual pieces—HTTP cassettes, provider contracts, live traffic shadowing, or observability—but a developer still has to manually translate a run into a safe, reviewable regression test.

## Target users and use cases

The primary user is a backend or platform engineer maintaining an API, microservice workflow, or tool-using agent. The user should be able to capture a run, sanitize it, inspect the artifact, replay it against a local implementation, compare it with a baseline, and make CI fail only for meaningful changes. A security-conscious team should also be able to enforce strict redaction and reject artifacts that still contain secrets.

## MVP boundary

The MVP supports a versioned replay bundle, JSONL interaction records, HTTP request/response capture from an explicit fixture or local adapter, deterministic matching, JSON-aware semantic diffing, redaction, a CLI, and CI-friendly exit codes. It intentionally does not include a hosted dashboard, multi-tenant service, browser automation, automatic production packet sniffing, or an LLM dependency.

| Capability | MVP | Advanced feature | Future direction |
|---|---|---|---|
| Capture | Explicit JSON/JSONL input and local HTTP adapter | Transparent proxy and OTel span ingestion | eBPF or service-mesh capture |
| Replay | Offline fixture replay and local target replay | Parallel scenario execution and load profiles | Distributed replay workers |
| Diff | JSON paths, volatile-field rules, numeric tolerances | Schema-aware and domain plugins | Learned semantic policies with opt-in local models |
| Security | Header/body redaction and strict mode | Secret scanners and signed bundles | KMS-backed keyless attestations |
| Integrations | CLI, Python API, GitHub Actions | pytest plugin, FastAPI middleware | Node/Go SDKs and CI providers |

## Functional requirements

1. A bundle has an explicit schema version and stable identifiers. It contains metadata, interactions, normalization rules, and a manifest of redacted fields.
2. Every recorded interaction is self-contained and replayable. Network access is never required for fixture mode.
3. Matching is deterministic and explainable. A mismatch reports the expected key, observed key, and the reason for rejection.
4. Redaction is deny-by-default for common credentials and configurable for domain-specific fields. Strict mode fails when known secret patterns remain.
5. The semantic diff distinguishes missing, unexpected, changed, equivalent, and transport-error outcomes. It supports JSON Pointer ignore paths and configurable numeric tolerance.
6. The CLI uses stable exit codes so CI can distinguish usage errors, unsafe artifacts, replay failures, and semantic regressions.
7. The core library is usable without the CLI, and adapters can be added without changing the bundle format.

## Non-functional requirements

The core must run on Python 3.11+, have no runtime service dependency, be deterministic under a fixed clock and random seed, avoid logging secrets, and remain testable without internet access. The bundle format must be human-readable, diffable in Git, and forward-compatible through schema versioning. A typical small bundle should load in milliseconds and replay hundreds of interactions without unbounded memory growth.

## Component architecture

```text
                 +---------------------+
                 | CLI / Python API    |
                 +----------+----------+
                            |
       +--------------------+--------------------+
       |                    |                    |
+------v------+      +------v------+      +------v------+
| Bundle I/O  |      | Sanitizer   |      | Diff Engine  |
| JSONL/schema|      | rules/strict|      | semantic JSON |
+------+------+      +------+------+      +------+------+ 
       |                    |                    |
       +--------------------+--------------------+
                            |
                     +------v------+
                     | Replay Core |
                     | match/target|
                     +------+------+ 
                            |
                +-----------+-----------+
                |                       |
        +-------v-------+       +-------v--------+
        | Fixture target|       | HTTP adapter    |
        | offline       |       | local endpoint  |
        +---------------+       +----------------+
```

The bundle layer owns serialization and validation. The sanitizer transforms an input bundle into a safe bundle and records redaction metadata without retaining original secret values. The replay core consumes an abstract `Transport` protocol, making fixture replay and live-target replay interchangeable. The diff engine compares normalized response envelopes and emits structured outcomes consumed by the CLI and CI. The optional pytest plugin is a thin facade over the same fixture transport and report contract; it owns no state, performs no network calls, and does not fork a second execution model.

## Data flow

Capture or import produces an in-memory interaction stream. The sanitizer applies header rules, JSON-pointer rules, and pattern detectors, then serializes a normalized bundle. Replay loads and validates the bundle, selects an interaction by deterministic request key, invokes either the fixture transport or an HTTP transport, normalizes the observed response, and passes both envelopes to the diff engine. The CLI renders a human report while optionally writing machine-readable JSON.

## Error flow

Malformed input is rejected before execution with a schema error. An unsafe bundle is rejected in strict mode before any target call. A missing interaction produces a deterministic replay mismatch, not a generic exception. Transport failures are wrapped with endpoint, interaction ID, timeout, and retry context while excluding request bodies and authorization values. Diff failures remain non-zero even when transport succeeded, because semantic regressions are the product’s primary signal.

## Security model

ReplayWeave assumes bundle files may be committed to a repository and therefore treats them as potentially public. Authorization, cookies, API keys, common token formats, and configurable secret paths are redacted by default. Logs use structured fields with an allowlist rather than dumping request objects. Strict mode scans serialized output and fails if high-confidence credential patterns survive. The tool never sends captured data to a remote service and never evaluates arbitrary code from a bundle.

## Configuration

Configuration is loaded in this order: CLI flags, explicit config file, project config, then safe defaults. Configuration is declarative and validated before replay. Rules are immutable during one run; the resolved configuration is included in the report so a CI result is reproducible.

## Observability

The MVP emits structured local events through Python logging and a JSON report. Each operation has a run ID, bundle ID, interaction ID, elapsed milliseconds, outcome, and error category. No payload is logged by default. An optional OpenTelemetry exporter is a future adapter and is not required for core operation.

## Performance and scalability

The loader streams JSONL records where possible and indexes request keys for O(1) lookup. Diffing is recursive with explicit depth and payload-size limits. Replay concurrency is bounded by a semaphore in the advanced runner; the MVP remains sequential for predictability. Large bundles can later be sharded by scenario without changing the public record format.

## Extensibility

Transport adapters implement a narrow protocol. Normalizers and diff strategies are registered by name and receive typed envelopes. The schema uses additive versioning and rejects unknown major versions. The Python API exposes stable modules for bundle, sanitize, replay, and diff while internal helpers remain private.

## Pytest integration boundary

The pytest entry point is optional and isolated from the core runtime dependencies. Its `replayweave` fixture exposes `run()` for inspection and `assert_bundle()` for a failing test assertion. Both methods use the bundle's own recorded responses through `FixtureTransport`, which makes the integration safe for offline CI and straightforward to test. The plugin is intentionally not a collection-time magic feature: test authors opt in through a normal fixture call, keeping discovery predictable.

## Release quality gates

Every change must pass formatting, linting, type checking, unit tests, property tests for normalization and diff symmetry, integration tests for fixture replay, security tests for redaction, and a CLI smoke test. GitHub Actions will run the same commands used by contributors. Releases will use SemVer and publish a changelog with migration notes.
