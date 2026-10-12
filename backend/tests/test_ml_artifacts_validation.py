"""Negative tests for missing, empty, and corrupt ML artifacts."""
import json

from app.ml.predictor import validate_artifacts


def test_artifact_validation_reports_all_missing_required_files(tmp_path):
    problems = validate_artifacts(tmp_path)
    assert len(problems) == 7
    assert any("cpu_model.pkl" in problem for problem in problems)


def test_artifact_validation_rejects_empty_and_corrupt_artifacts(tmp_path):
    for name in ["cpu", "memory", "network", "cost", "carbon"]:
        (tmp_path / f"{name}_model.pkl").write_bytes(b"not-a-pickle")
    (tmp_path / "metrics.json").write_text("{bad json")
    (tmp_path / "feature_importance.json").write_text(json.dumps({}))
    problems = validate_artifacts(tmp_path)
    assert any("could not deserialize" in problem for problem in problems)
    assert any("could not parse JSON" in problem for problem in problems)
    assert any("missing metric data" in problem for problem in problems)


def test_artifact_validation_rejects_empty_files(tmp_path):
    for name in ["cpu_model.pkl", "memory_model.pkl", "network_model.pkl", "cost_model.pkl", "carbon_model.pkl", "metrics.json", "feature_importance.json"]:
        (tmp_path / name).write_bytes(b"")
    problems = validate_artifacts(tmp_path)
    assert len(problems) == 7
    assert all("missing or empty" in problem for problem in problems)
