from pathlib import Path

import pytest


@pytest.mark.replayweave
def test_replayweave_fixture_asserts_bundle(replayweave) -> None:
    report = replayweave.assert_bundle(
        Path(__file__).parents[1] / "examples" / "checkout.bundle.json"
    )
    assert report.equivalent
    assert report.passed == 1


@pytest.mark.replayweave
def test_replayweave_fixture_can_run_without_assertion(replayweave) -> None:
    report = replayweave.run(Path(__file__).parents[1] / "examples" / "checkout.bundle.json")
    assert report.to_dict()["outcomes"] == {"equivalent": 1}
