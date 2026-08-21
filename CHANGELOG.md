# Changelog

All notable changes to ReplayWeave are documented here.

## [0.3.0] - 2026-08-21

### Added

- Added `ReplayReport` and `build_report` as a stable aggregate CI contract.
- Added deterministic outcome counts, payload-free JSON reports, and explicit `exit_code` metadata.
- Added `--unordered-path` support to `replay` for order-insensitive collection assertions.
- Added package keywords and classifiers for discoverability and distribution metadata.

### Changed

- Human replay output now includes an aggregate `summary` line.
- README now documents machine-readable CI consumption and the v0.3 design boundary.

### Security

- Aggregate reports intentionally include interaction IDs, statuses, and errors only; response bodies are never serialized into reports.

## [0.1.0] - 2026-08-20

### Added

- Versioned replay bundle model with deterministic request keys.
- Local sanitization for common credentials, token patterns, and configurable paths.
- Offline fixture transport and HTTP transport boundary.
- Explainable semantic JSON diff with ignored paths and numeric tolerance.
- CLI commands: `check`, `sanitize`, `replay`, and `diff`.
- Python API, example bundle, CI workflow, architecture documentation, and tests.
