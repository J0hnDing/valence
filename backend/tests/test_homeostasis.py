"""Independent homeostatic equations, state boundaries, and immutable history."""
from copy import deepcopy
import math

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.core.compatibility import normalize_model
from app.core.homeostasis import energy_modifier, need_pressure
from app.core.initialization import initialize_from_quiz, QUESTION_BY_ID
from app.core.ontology import FEATURE_KEYS
from app.core.utility import evaluate, model_preview
from app.db.models import DailyState, Evaluation, EvaluationResult, PersonModelVersion
from app.main import create_app
from app.schemas import ActionInput, PersonModel, TransientState, default_model
from app.schemas.models import NEED_KEYS, NeedParameters


def action(duration=60, exposures=None, **features):
    return ActionInput(title="Needs", duration_minutes=duration, net_money_cost=0,
                       feature_duration_minutes=exposures,
                       features={key: features.get(key, 0) for key in FEATURE_KEYS})


def need(result, key):
    return next(t for t in result["need_traces"] if t["need_key"] == key)


@pytest.mark.parametrize("current,feature_value,pressure", [
    (0, 1, 1),
    (.2, -1, (.4 / .6) ** 2),
    (.6, .4, 0),
    (.8, .4, 0),
    (1, -1, -1),
    (.9, 1, -.25),
])
def test_current_need_pressure_adjusts_action_utility(current, feature_value, pressure):
    state = TransientState(need_satisfaction={"goal_progression": current})
    result = evaluate(action(goal_progress=feature_value), default_model(), state, 0)
    trace = need(result, "goal_progression")
    utility = pressure * feature_value
    assert trace["pressure"] == pytest.approx(pressure)
    assert trace["feature_value"] == feature_value
    assert trace["utility_contribution"] == pytest.approx(utility)
    assert result["needs_utility"] == pytest.approx(utility)
    assert result["total_utility"] == pytest.approx(feature_value + utility)


def test_unknown_state_is_neutral_and_partial_need_state_does_not_fabricate_values():
    model = default_model()
    model.resources.time_value = 2
    model.resources.money_value = 3
    encoded = action(120, mental_effort=.5, physical_effort=.25, learning_gain=.4, goal_progress=.8)
    encoded.net_money_cost = -2
    result = evaluate(encoded, model, TransientState(), 0)
    # Intrinsic costs use two hours; outcomes count once; income is credited.
    expected = -1 - .5 + .4 + .8 - 4 + 6
    assert result["total_utility"] == pytest.approx(expected)
    assert result["base_utility"] == result["total_utility"]
    assert result["needs_utility"] == result["energy_utility"] == 0
    assert all(not t["available"] and t["current_satisfaction"] is None and t["pressure"] == 0 for t in result["need_traces"])
    partial = evaluate(encoded, model, TransientState(need_satisfaction={"goal_progression": 0}), 0)
    assert sum(t["available"] for t in partial["need_traces"]) == 1
    assert need(partial, "goal_progression")["current_satisfaction"] == 0


def test_action_scoring_weights_zero_exposure_and_one_time_outcomes():
    encoded = action(60, mental_effort=1, learning_gain=1, physical_effort=1,
                     social_exposure=1, relatedness_intimacy=-1, goal_progress=-1)
    state = TransientState(need_satisfaction={key: .5 for key in NEED_KEYS})
    model = default_model()
    normal = evaluate(encoded, model, state, 0)
    assert [t["feature_value"] for t in normal["need_traces"]] == [1, 1, 1, -1, -1]
    encoded.feature_duration_minutes = {"mental_effort": 0, "physical_effort": 0, "social_exposure": 0, "relatedness_intimacy": 0}
    filtered = evaluate(encoded, model, state, 0)
    assert [t["feature_value"] for t in filtered["need_traces"]] == [0, .6, 0, 0, -1]
    model.homeostasis.mental_effort_weight = 1
    assert need(evaluate(encoded, model, state, 0), "mental_stimulation")["feature_value"] == 0
    encoded.duration_minutes = 0
    zero = evaluate(encoded, default_model(), state, 0)
    assert zero["energy_utility"] == 0 and zero["utility_per_action_hour"] is None
    assert [t["feature_value"] for t in zero["need_traces"]] == [0, .6, 0, 0, -1]


def test_need_contributions_count_once_for_any_positive_exposure_not_per_hour():
    state = TransientState(need_satisfaction={key: .1 for key in NEED_KEYS})
    first = evaluate(action(30, physical_effort=1, relatedness_intimacy=.8, learning_gain=1), default_model(), state, 0)
    second = evaluate(action(600, physical_effort=1, relatedness_intimacy=.8, learning_gain=1), default_model(), state, 0)
    assert first["need_traces"] == second["need_traces"]
    assert second["during_utility"] == pytest.approx(first["during_utility"] * 20)


def test_intrinsic_preference_and_need_sensitivity_are_independent_and_bounded():
    model = default_model()
    model.features["physical_effort"].cost_sensitivity = 0
    model.features["goal_progress"].positive_sensitivity = 50
    model.homeostasis.needs["physical_activity"].sensitivity = 64
    first = evaluate(action(physical_effort=1, goal_progress=1), model,
                     TransientState(need_satisfaction={key: 0 for key in NEED_KEYS}), 0)
    model.features["physical_effort"].cost_sensitivity = 20
    second = evaluate(action(physical_effort=1, goal_progress=1), model,
                      TransientState(need_satisfaction={key: 0 for key in NEED_KEYS}), 0)
    assert first["needs_utility"] == second["needs_utility"]
    assert all(abs(t["utility_contribution"]) <= t["parameters"]["sensitivity"] for t in first["need_traces"])
    assert abs(first["needs_utility"]) <= sum(p.sensitivity for p in model.homeostasis.needs.values())
    model.homeostasis.needs["physical_activity"].sensitivity = 0
    assert need(evaluate(action(physical_effort=1), model, TransientState(need_satisfaction={"physical_activity": 0}), 0), "physical_activity")["utility_contribution"] == 0


@pytest.mark.parametrize("energy,alpha,expected", [(None, 64, 1), (.7, 1, 1), (0, 1, 1.7), (1, 1, .7), (0, 64, 2), (1, 64, .5), (.1, 0, 1)])
def test_energy_bounds_and_neutral_values(energy, alpha, expected):
    assert energy_modifier(energy, alpha) == pytest.approx(expected)
    model = default_model()
    model.transient.low_mental_energy_cognitive_multiplier = alpha
    result = evaluate(action(120, {"mental_effort": 30}, mental_effort=1, physical_effort=1, mental_rest=.5), model,
                      TransientState(mental_energy=energy), 0)
    assert result["energy_traces"][0]["base_contribution"] == -.5
    assert result["energy_traces"][0]["adjusted_contribution"] == pytest.approx(-.5 * expected)
    assert result["energy_utility"] == pytest.approx(-.5 * (expected - 1) + max(0, expected - 1))
    assert result["total_utility"] == pytest.approx(result["base_utility"] + result["energy_utility"])
    assert model_preview(model, TransientState(mental_energy=energy))["features"]["mental_effort"]["points"][-1]["y"] == pytest.approx(-expected)


@pytest.mark.parametrize("values", [{"lower": 0}, {"upper": 1}, {"lower": .9, "upper": .8},
                                   {"sensitivity": -1}, {"sensitivity": 64.001}, {"rate": .25},
                                   {"rate": -.001}, {"lower": math.nan}, {"sensitivity": math.inf}])
def test_invalid_need_parameters_are_rejected(values):
    with pytest.raises(ValidationError):
        NeedParameters(**values)


def test_interval_point_optimum_and_extreme_valid_intervals_are_finite():
    assert need_pressure(.5, .5, .5) == 0
    for lower, upper in ((1e-300, 1 - 1e-15), (.6, .8), (.5, .5)):
        for s in (0, lower, upper, 1):
            value = need_pressure(s, lower, upper)
            assert math.isfinite(value) and -1 <= value <= 1


@pytest.mark.parametrize("values", [{"unknown": .5}, {"physical_activity": -1},
                                   {"mental_stimulation": math.inf}, {"close_connection": 1.1},
                                   {"goal_progression": None}])
def test_invalid_need_state_is_rejected(values):
    with pytest.raises(ValidationError):
        TransientState(need_satisfaction=values)


def test_strict_model_keys_and_public_boundary_revalidation():
    model = default_model().model_dump()
    del model["homeostasis"]["needs"]["close_connection"]
    with pytest.raises(ValidationError):
        PersonModel.model_validate(model)
    model = default_model()
    model.homeostasis.needs["unknown"] = NeedParameters()
    with pytest.raises(ValidationError):
        evaluate(action(), model, TransientState())
    state = TransientState()
    state.need_satisfaction["goal_progression"] = math.nan
    with pytest.raises(ValidationError):
        evaluate(action(), default_model(), state)


def test_graph_closed_and_equations_match_traces_with_no_mutation():
    model = default_model()
    encoded = action(120, physical_effort=.8, learning_gain=.7, goal_progress=-.6)
    state = TransientState(physical_energy=.1, need_satisfaction={key: .15 for key in NEED_KEYS})
    before = deepcopy((model.model_dump(), encoded.model_dump(), state.model_dump()))
    first = evaluate(encoded, model, state, 7)
    assert first == evaluate(encoded, model, state, 7)
    assert before == (model.model_dump(), encoded.model_dump(), state.model_dump())
    nodes = {n["id"]: n for n in first["graph"]["nodes"]}
    assert len(nodes) == len(first["graph"]["nodes"])
    assert all(e["source"] in nodes and e["target"] in nodes for e in first["graph"]["edges"])
    assert all(n["kind"] != "need_prediction" for n in nodes.values())
    for trace in first["need_traces"]:
        key = trace["need_key"]
        assert nodes[f"need:{key}:pressure"]["value"] == trace["pressure"]
        assert set(trace).isdisjoint({"predicted_satisfaction", "impact", "value_before", "value_after"})
        assert "rate" not in trace["parameters"]
        assert nodes[f"need:{key}:utility"]["value"] == trace["utility_contribution"]
    assert first["total_utility"] == pytest.approx(first["base_utility"] + first["needs_utility"] + first["energy_utility"])
    assert first["gross_utility"] == pytest.approx(first["total_utility"] + first["resource_cost"])


def test_caller_updates_current_state_and_pressure_changes_without_state_derivation():
    model = default_model()
    model.features["goal_progress"].positive_sensitivity = 0
    model.features["goal_progress"].negative_sensitivity = 0
    relevant, absent = action(goal_progress=1), action()
    deprived = TransientState(need_satisfaction={"goal_progression": 0})
    overloaded = TransientState(need_satisfaction={"goal_progression": 1})
    assert evaluate(relevant, model, deprived, 0)["total_utility"] > evaluate(absent, model, deprived, 0)["total_utility"]
    assert evaluate(relevant, model, overloaded, 0)["total_utility"] < evaluate(absent, model, overloaded, 0)["total_utility"]
    first = evaluate(relevant, model, deprived, 0)
    assert first["need_traces"] == evaluate(relevant, model, deprived, 168)["need_traces"]
    assert deprived.need_satisfaction == {"goal_progression": 0}
    assert overloaded.need_satisfaction == {"goal_progression": 1}


def test_quiz_does_not_infer_need_parameters_and_legacy_projection_is_read_only():
    baseline = default_model().model_dump()
    assert initialize_from_quiz({key: 5 for key in QUESTION_BY_ID})["model"]["homeostasis"] == baseline["homeostasis"]
    old = deepcopy(baseline)
    del old["homeostasis"]
    old["transient"]["low_mental_energy_cognitive_multiplier"] = .5
    old["transient"]["low_physical_energy_physical_multiplier"] = 100
    before = deepcopy(old)
    projected, converted = normalize_model(old)
    assert converted and old == before
    assert projected["homeostasis"] == baseline["homeostasis"]
    assert projected["transient"]["low_mental_energy_cognitive_multiplier"] == .5
    assert projected["transient"]["low_physical_energy_physical_multiplier"] == 64
    PersonModel.model_validate(projected)


def test_api_state_save_evaluation_reproduction_and_restart_preserve_current_state(tmp_path):
    url = "sqlite:///" + (tmp_path / "needs.db").as_posix()
    with TestClient(create_app(url)) as client:
        person = client.post("/api/persons", json={"name": "Needs test"}).json()
        encoded = client.post("/api/actions", json=action(physical_effort=1, goal_progress=1).model_dump()).json()
        state = TransientState(date="2026-10-10", physical_energy=.2,
                               need_satisfaction={"physical_activity": 0, "goal_progression": .9}).model_dump(mode="json")
        assert client.put("/api/daily-state", json={"person_id": person["id"], "state": state}).json() == state
        request = {"person_id": person["id"], "action_ids": [encoded["id"]], "state": state, "horizon_hours": 0}
        response = client.post("/api/evaluations", json=request)
        assert response.status_code == 201, response.text
        historical = response.json()
        assert historical["engine_version"] == "8"
        result = historical["results"][0]
        assert need(result, "physical_activity")["utility_contribution"] > 0
        assert need(result, "goal_progression")["utility_contribution"] < 0
        assert result["needs_utility"] == pytest.approx(.75)
        assert result["energy_utility"] < 0
        assert need(result, "physical_activity")["pressure"] == 1
        assert client.get("/api/daily-state", params={"person_id": person["id"], "date": state["date"]}).json() == state
        assert client.post(f"/api/evaluations/{historical['id']}/reproduce").json()["matches"]
        unknown = client.post("/api/evaluations", json=request | {"state": {}}).json()
        assert unknown["results"][0]["needs_utility"] == 0
        invalid = client.post("/api/evaluations", json=request | {"state": {"need_satisfaction": {"invalid": 0}}})
        assert invalid.status_code == 422
    with TestClient(create_app(url)) as client:
        assert client.get(f"/api/evaluations/{historical['id']}").json() == historical
        assert client.get("/api/daily-state", params={"person_id": person["id"], "date": state["date"]}).json() == state
        assert client.post(f"/api/evaluations/{historical['id']}/reproduce").json()["matches"]


def test_v5_saved_models_and_states_are_projected_without_rewriting_history(client, app):
    person = client.post("/api/persons", json={"name": "Legacy"}).json()
    path = f"/api/persons/{person['id']}/model"
    version = client.get(path).json()
    encoded = client.post("/api/actions", json=action(mental_effort=1).model_dump()).json()
    historical = client.post("/api/evaluations", json={"person_id": person["id"], "action_ids": [encoded["id"]], "state": {}}).json()
    old_model = deepcopy(version["model"])
    del old_model["homeostasis"]
    old_model["transient"]["low_mental_energy_cognitive_multiplier"] = .5
    old_state = {"mental_energy": .5, "physical_energy": .5, "acute_stress": 0, "date": "2026-10-10", "notes": None}
    with app.state.database.sessions() as session, session.begin():
        session.get(PersonModelVersion, version["id"]).model = old_model
        record = session.get(Evaluation, historical["id"])
        record.engine_version = "5"
        record.model_snapshot = old_model
        record.state = old_state
        session.add(DailyState(person_id=person["id"], date=old_state["date"], state=old_state))
    historical.update(engine_version="5", model_snapshot=old_model, state=old_state)
    assert client.get(f"/api/evaluations/{historical['id']}").json() == historical
    assert client.post(f"/api/evaluations/{historical['id']}/reproduce").status_code == 409
    projected = client.get(path).json()
    assert projected["converted_from_legacy"] and "homeostasis" in projected["model"]
    assert client.get("/api/daily-state", params={"person_id": person["id"], "date": old_state["date"]}).json() == old_state
    with app.state.database.sessions() as session:
        assert session.get(PersonModelVersion, version["id"]).model == old_model


def test_v6_rates_and_prediction_snapshots_are_preserved_but_not_used_by_v8(client, app):
    person = client.post("/api/persons", json={"name": "Engine 6 history"}).json()
    path = f"/api/persons/{person['id']}/model"
    version = client.get(path).json()
    old_model = deepcopy(version["model"])
    for parameters in old_model["homeostasis"]["needs"].values():
        parameters["rate"] = .25
    encoded = client.post("/api/actions", json=action(goal_progress=1).model_dump()).json()
    historical = client.post("/api/evaluations", json={"person_id": person["id"], "action_ids": [encoded["id"]], "state": {}}).json()
    old_results = deepcopy(historical["results"])
    old_results[0]["need_traces"] = [{"need_key": "goal_progression", "predicted_satisfaction": .25, "impact": 1}]
    with app.state.database.sessions() as session, session.begin():
        session.get(PersonModelVersion, version["id"]).model = old_model
        record = session.get(Evaluation, historical["id"])
        record.engine_version = "6"
        record.model_snapshot = old_model
        row = session.scalar(select(EvaluationResult).where(EvaluationResult.evaluation_id == historical["id"]))
        row.result = row.result | {"need_traces": old_results[0]["need_traces"]}
    historical.update(engine_version="6", model_snapshot=old_model, results=old_results)
    assert client.get(f"/api/evaluations/{historical['id']}").json() == historical
    assert client.post(f"/api/evaluations/{historical['id']}/reproduce").status_code == 409
    projected = client.get(path).json()
    assert projected["converted_from_legacy"]
    assert all("rate" not in p for p in projected["model"]["homeostasis"]["needs"].values())
    assert client.put(path, json={"model": old_model}).status_code == 422
    fresh = client.post("/api/evaluations", json={"person_id": person["id"], "action_ids": [encoded["id"]],
                                                 "state": {"need_satisfaction": {"goal_progression": 0}}, "horizon_hours": 0}).json()
    assert fresh["engine_version"] == "8"
    assert fresh["results"][0]["needs_utility"] == 1
    assert all("predicted_satisfaction" not in t for t in fresh["results"][0]["need_traces"])
    with app.state.database.sessions() as session:
        assert session.get(PersonModelVersion, version["id"]).model == old_model
