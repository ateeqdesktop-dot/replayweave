# Contributing to ReplayWeave

Thank you for helping make replay-based regression testing safer and more useful. Before opening an issue, please search existing discussions and describe the smallest reproducible example. For a pull request, explain the behavior change, add focused tests, and update the bundle contract documentation when the schema or diff semantics change.

Run the complete local gate from the repository root:

```bash
pip install -e '.[dev]'
ruff format src tests
ruff check .
mypy src
pytest --cov=replayweave --cov-report=term-missing
```

ReplayWeave values small, composable changes. New transports should implement the narrow transport protocol, avoid leaking payloads into logs, and include an offline test. Changes to redaction rules require a security-focused test. Changes to exit codes or report formats require a short note in `CHANGELOG.md`.

By participating, you agree to maintain a respectful and inclusive project environment.
