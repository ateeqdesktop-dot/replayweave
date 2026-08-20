import json

from click.testing import CliRunner

from replayweave.cli import main


def write_json(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def bundle():
    return {
        "schema_version": "1.0",
        "name": "cli-demo",
        "bundle_id": "cli-1",
        "metadata": {},
        "interactions": [
            {
                "id": "one",
                "request": {
                    "method": "GET",
                    "url": "https://example.test",
                    "headers": {},
                    "body": None,
                },
                "response": {"status": 200, "headers": {}, "body": {"ok": True}},
                "metadata": {},
            }
        ],
    }


def test_cli_check_and_replay(tmp_path):
    source = write_json(tmp_path, "bundle.json", bundle())
    runner = CliRunner()
    checked = runner.invoke(main, ["check", str(source)])
    replayed = runner.invoke(main, ["replay", str(source)])
    assert checked.exit_code == 0
    assert "safe:" in checked.output
    assert replayed.exit_code == 0
    assert "one: equivalent" in replayed.output


def test_cli_sanitize_writes_destination(tmp_path):
    raw = bundle()
    raw["interactions"][0]["request"]["headers"] = {"Authorization": "Bearer secret"}
    source = write_json(tmp_path, "raw.json", raw)
    destination = tmp_path / "safe.json"
    result = CliRunner().invoke(main, ["sanitize", str(source), str(destination)])
    assert result.exit_code == 0
    assert (
        json.loads(destination.read_text())["interactions"][0]["request"]["headers"][
            "Authorization"
        ]
        == "[REDACTED]"
    )


def test_cli_diff_returns_nonzero_for_change(tmp_path):
    baseline = write_json(tmp_path, "baseline.json", {"status": "ok", "request_id": "a"})
    observed = write_json(tmp_path, "observed.json", {"status": "failed", "request_id": "b"})
    result = CliRunner().invoke(
        main, ["diff", str(baseline), str(observed), "--ignore-path", "request_id"]
    )
    assert result.exit_code == 1
    assert "changed" in result.output


def test_cli_import_jsonl_and_unordered_diff(tmp_path):
    capture = tmp_path / "capture.jsonl"
    capture.write_text(
        '{"id":"one","method":"GET","url":"https://prod.test/items",'
        '"response":{"status":200,"body":{"items":[2,1]}}}\n',
        encoding="utf-8",
    )
    destination = tmp_path / "capture.bundle.json"
    imported = CliRunner().invoke(
        main, ["import", str(capture), str(destination), "--format", "jsonl"]
    )
    assert imported.exit_code == 0, imported.output
    imported_bundle = json.loads(destination.read_text())
    assert imported_bundle["interactions"][0]["request"]["url"] == "/items"

    baseline = write_json(tmp_path, "baseline.json", {"items": [1, 2]})
    observed = write_json(tmp_path, "observed.json", {"items": [2, 1]})
    diffed = CliRunner().invoke(
        main, ["diff", str(baseline), str(observed), "--unordered-path", "items"]
    )
    assert diffed.exit_code == 0, diffed.output
