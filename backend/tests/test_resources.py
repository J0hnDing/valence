"""Resource accounting, temporal units, and immutable pre-resource records."""
from copy import deepcopy
import json
import math
import sqlite3

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.core.compatibility import normalize_action, normalize_model
from app.core.initialization import initialize_from_quiz
from app.core.ontology import FEATURE_KEYS
from app.core.utility import evaluate
from app.main import create_app
from app.schemas.models import ActionInput, PersonModel, TransientState, default_model


def encoded(duration=120, money=4, **features):
    return ActionInput(title="Resource example", duration_minutes=duration, net_money_cost=money,
                       features={key: features.get(key, 0) for key in FEATURE_KEYS})


def resource_model():
    model = default_model()
    model.features["competence_mastery"].positive_sensitivity = 10
    model.features["goal_progress"].positive_sensitivity = 5
    model.resources.time_value = 3
    model.resources.money_value = 2
    return model


def test_costs_subtract_at_end_hourly_metric_excludes_only_time_cost():
    action, model = encoded(competence_mastery=1, goal_progress=.8), resource_model()
    result = evaluate(action, model, TransientState(), 0)
    assert result["during_rate"] == 10
    assert result["during_utility"] == 20
    assert result["one_time_utility"] == 4
    assert result["gross_utility"] == 24
    assert result["time_cost"] == 6
    assert result["money_cost"] == 8
    assert result["resource_cost"] == 14
    assert result["total_utility"] == 10
    assert result["utility_per_action_hour"] == 8
    model.resources.time_value = 7
    changed = evaluate(action, model, TransientState(), 0)
    assert changed["total_utility"] == 2
    assert changed["utility_per_action_hour"] == result["utility_per_action_hour"]
    nodes = {node["id"]: node for node in result["graph"]["nodes"]}
    assert nodes["time_cost"]["value"] == 6
    assert nodes["money_cost"]["value"] == 8
    assert nodes["resource_cost"]["value"] == 14
    assert nodes["total_utility"]["formula"] == "gross_utility - resource_cost"
    incoming = {edge["source"] for edge in result["graph"]["edges"] if edge["target"] == "utility_per_action_hour"}
    assert incoming == {"utility_excluding_time_cost", "duration_hours"}


@pytest.mark.parametrize("duration,money,gross,total,hourly", [
    (120, -4, 24, 26, 16),  # income is added once
    (240, 4, 44, 24, 9),    # money cost stays 8 when duration doubles
    (0, 4, 4, -4, None),    # an instantaneous outcome and spending still count
])
def test_income_duration_and_zero_duration(duration, money, gross, total, hourly):
    result = evaluate(encoded(duration, money, competence_mastery=1, goal_progress=.8), resource_model(), TransientState(), 0)
    assert result["gross_utility"] == gross
    assert result["total_utility"] == total
    assert result["utility_per_action_hour"] == hourly
    assert result["money_cost"] == 2 * money


@pytest.mark.parametrize("key", ["learning_gain", "goal_progress", "status_recognition", "contribution_care"])
def test_whole_action_outcomes_are_independent_of_duration(key):
    model = default_model()
    model.features["structure_planning"].preference_sensitivity = 1
    outputs = [evaluate(encoded(duration, 0, **{key: .5}), model, TransientState(), 0) for duration in (0, 30, 60, 240)]
    for result in outputs:
        assert result["during_rate"] == 0
        assert result["during_utility"] == 0
        assert result["one_time_utility"] == .5
        assert result["total_utility"] == .5
        trace = next(trace for trace in result["feature_traces"] if trace["feature_key"] == key)
        assert trace["temporal_basis"] == "one_time"
        assert trace["utility_rate_contribution"] is None
        assert trace["utility_contribution"] == .5


def test_negative_outcome_also_counts_once_and_ongoing_experience_scales():
    result = evaluate(encoded(180, 0, goal_progress=-.5, competence_mastery=.5), default_model(), TransientState(), 0)
    assert result["one_time_utility"] == -.5
    assert result["during_utility"] == 1.5
    assert result["total_utility"] == 1
    trace = next(t for t in result["feature_traces"] if t["feature_key"] == "competence_mastery")
    assert trace["utility_contribution"] == 1.5
    assert trace["utility_rate_contribution"] == .5


@pytest.mark.parametrize("name", ["time_value", "money_value"])
@pytest.mark.parametrize("invalid", [-1, math.nan, math.inf, -math.inf])
def test_resource_parameters_reject_negative_or_nonfinite(name, invalid):
    values = default_model().model_dump()
    values["resources"][name] = invalid
    with pytest.raises(ValidationError):
        PersonModel.model_validate(values)


def test_money_is_required_finite_and_resource_keys_are_strict():
    action = encoded().model_dump()
    del action["net_money_cost"]
    with pytest.raises(ValidationError):
        ActionInput.model_validate(action)
    for invalid in (None, math.nan, math.inf, -math.inf):
        with pytest.raises(ValidationError):
            ActionInput.model_validate(action | {"net_money_cost": invalid})
    model = default_model().model_dump()
    model["resources"]["invented"] = 0
    with pytest.raises(ValidationError):
        PersonModel.model_validate(model)


@pytest.mark.parametrize("name,duration,money", [("time_value", 120, 0), ("money_value", 60, 2)])
def test_resource_multiplication_overflow_is_rejected(name, duration, money):
    model = default_model()
    setattr(model.resources, name, 1e308)
    with pytest.raises(ValueError, match="double-precision"):
        evaluate(encoded(duration, money), model, TransientState(), 0)


def test_quiz_does_not_guess_resource_coefficients_and_adapters_do_not_mutate():
    quiz = initialize_from_quiz({})
    assert quiz["model"]["resources"] == {"time_value": 0, "money_value": 0}
    assert {"resources.time_value", "resources.money_value"} <= set(quiz["defaulted"])
    old_model = default_model().model_dump()
    del old_model["resources"]
    old_action = encoded().model_dump()
    del old_action["net_money_cost"]
    original = deepcopy((old_model, old_action))
    model, converted = normalize_model(old_model)
    assert converted and model["resources"] == {"time_value": 0, "money_value": 0}
    action, converted = normalize_action(old_action)
    assert converted and action["net_money_cost"] == 0
    assert (old_model, old_action) == original


def test_api_resource_ranking_snapshot_and_reproduction(client):
    person = client.post("/api/persons", json={"name": "Resources"}).json()
    path = f"/api/persons/{person['id']}/model"
    version = client.put(path, json=resource_model().model_dump()).json()
    expensive = client.post("/api/actions", json=encoded(120, 4, competence_mastery=1, goal_progress=.8).model_dump()).json()
    cheap = client.post("/api/actions", json=encoded(60, 0, competence_mastery=1, goal_progress=.8).model_dump()).json()
    request = {"person_id": person["id"], "model_version_id": version["id"], "action_ids": [expensive["id"], cheap["id"]], "state": {}, "horizon_hours": 0}
    evaluation = client.post("/api/evaluations", json=request).json()
    assert evaluation["engine_version"] == "5"
    assert [r["action_id"] for r in evaluation["results"]] == [cheap["id"], expensive["id"]]
    assert [r["total_utility"] for r in evaluation["results"]] == [11, 10]
    assert evaluation["results"][1]["action_snapshot"]["net_money_cost"] == 4
    assert evaluation["model_snapshot"]["resources"] == {"time_value": 3, "money_value": 2}
    client.put(f"/api/actions/{expensive['id']}", json=encoded(120, -4).model_dump())
    assert client.get(f"/api/evaluations/{evaluation['id']}").json() == evaluation
    assert client.post(f"/api/evaluations/{evaluation['id']}/reproduce").json()["matches"] is True
    body = encoded().model_dump()
    del body["net_money_cost"]
    assert client.post("/api/actions", json=body).status_code == 422


def test_pre_resource_database_upgrade_keeps_models_history_and_zero_costs(tmp_path):
    path = tmp_path / "v2.db"
    url = "sqlite:///" + path.as_posix()
    with TestClient(create_app(url)) as initial:
        person = initial.post("/api/persons", json={"name": "Earlier person"}).json()
        action = initial.post("/api/actions", json=encoded(60, 0, goal_progress=.5).model_dump()).json()
        model_version = initial.get(f"/api/persons/{person['id']}/model").json()
        history = initial.post("/api/evaluations", json={"person_id": person["id"], "action_ids": [action["id"]], "state": {}, "horizon_hours": 0}).json()
    old_model = deepcopy(model_version["model"])
    del old_model["resources"]
    # Emulate the earlier database shape and immutable historical payload.
    historical_model = deepcopy(history["model_snapshot"])
    del historical_model["resources"]
    history["model_snapshot"] = historical_model
    history["engine_version"] = "2"
    snapshot = history["results"][0]["action_snapshot"]
    del snapshot["net_money_cost"]
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE actions DROP COLUMN net_money_cost")
        connection.execute("UPDATE person_model_versions SET model=? WHERE id=?", (json.dumps(old_model), model_version["id"]))
        connection.execute("UPDATE evaluations SET engine_version='2', model_snapshot=? WHERE id=?", (json.dumps(historical_model), history["id"]))
        connection.execute("UPDATE evaluation_results SET action_snapshot=? WHERE evaluation_id=?", (json.dumps(snapshot), history["id"]))
    for _ in range(2):  # migration is idempotent across restarts
        with TestClient(create_app(url)) as upgraded:
            assert upgraded.get(f"/api/actions/{action['id']}").json()["net_money_cost"] == 0
            view = upgraded.get(f"/api/persons/{person['id']}/model").json()
            assert view["model"]["resources"] == {"time_value": 0, "money_value": 0}
            assert view["converted_from_legacy"] is True
            assert upgraded.get(f"/api/evaluations/{history['id']}").json() == history
            assert upgraded.post(f"/api/evaluations/{history['id']}/reproduce").status_code == 409
            copy = upgraded.post("/api/persons", json={"name": "Copy", "initialization": {"method": "copy", "person_id": person["id"], "model_version_id": model_version["id"]}}).json()
            assert upgraded.get(f"/api/persons/{copy['id']}/model").json()["model"]["resources"] == {"time_value": 0, "money_value": 0}
    with sqlite3.connect(path) as connection:
        assert json.loads(connection.execute("SELECT model FROM person_model_versions WHERE id=?", (model_version["id"],)).fetchone()[0]) == old_model
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
