"""Rest responds to exhaustion without changing effort, aftereffects, or state."""
from copy import deepcopy

import pytest
from app.core.ontology import FEATURE_KEYS
from app.core.utility import evaluate, model_preview
from app.db.models import Evaluation
from app.schemas import ActionInput, TransientState, default_model


def action(duration=60, exposure=None, **values):
    return ActionInput(title="Rest and effort", duration_minutes=duration, net_money_cost=0,
                       features={key: values.get(key, 0) for key in FEATURE_KEYS},
                       feature_duration_minutes={"mental_rest": exposure} if exposure is not None else None)


def energy_trace(result, key):
    return next(t for t in result["energy_traces"] if t["feature_key"] == key)


@pytest.mark.parametrize("energy,alpha,multiplier", [
    (None, 64, 1), (.7, 2, 1), (1, 64, 1), (.2, 0, 1),
    (.2, 1, 1.5), (.192, 2, 2), (0, 64, 2),
])
def test_low_mental_energy_boosts_only_rest_reward_with_bounded_response(energy, alpha, multiplier):
    model = default_model()
    model.transient.low_mental_energy_cognitive_multiplier = alpha
    encoded = action(mental_rest=.5, physical_pleasure=.5)
    supplied = TransientState(mental_energy=energy, physical_energy=0)
    result = evaluate(encoded, model, supplied, 0)
    trace = energy_trace(result, "mental_rest")
    assert trace["modifier"] == pytest.approx(multiplier)
    assert trace["base_contribution"] == .5
    assert trace["adjusted_contribution"] == pytest.approx(.5 * multiplier)
    assert trace["utility_contribution"] == pytest.approx(.5 * (multiplier - 1))
    assert result["total_utility"] == pytest.approx(1 + .5 * (multiplier - 1))
    preview = model_preview(model, supplied, 0)
    assert preview["features"]["mental_rest"]["points"][50]["y"] == pytest.approx(.5 * multiplier)
    assert preview["features"]["physical_pleasure"]["points"][50]["y"] == .5


@pytest.mark.parametrize("duration,exposure,expected", [(120, None, 1.5), (120, 15, .1875),
                                                        (120, 0, 0), (0, None, 0)])
def test_rest_bonus_respects_curvature_and_actual_exposure(duration, exposure, expected):
    model = default_model()
    model.features["mental_rest"].reward_sensitivity = 3
    model.features["mental_rest"].curvature = 2
    model.transient.low_mental_energy_cognitive_multiplier = 2
    result = evaluate(action(duration, exposure, mental_rest=.5), model, TransientState(mental_energy=0), 0)
    assert energy_trace(result, "mental_rest")["base_contribution"] == pytest.approx(expected)
    assert result["energy_utility"] == pytest.approx(expected)
    assert result["total_utility"] == pytest.approx(2 * expected)


def test_rest_bonus_and_effort_penalty_coexist_without_double_counting_or_state_mutation():
    model = default_model()
    model.transient.low_mental_energy_cognitive_multiplier = 2
    encoded = action(120, 30, mental_effort=.6, mental_rest=.8, structure_planning=.5)
    exhausted = TransientState(mental_energy=.192, physical_energy=1)
    before = deepcopy((model.model_dump(), encoded.model_dump(), exhausted.model_dump()))
    result = evaluate(encoded, model, exhausted)
    neutral = evaluate(encoded, model, TransientState(mental_energy=.7, physical_energy=1))
    assert energy_trace(result, "mental_effort")["utility_contribution"] == pytest.approx(-1.2)
    assert energy_trace(result, "mental_rest")["utility_contribution"] == pytest.approx(.4)
    assert result["energy_utility"] == pytest.approx(-.8)
    assert result["aftereffect_traces"] == neutral["aftereffect_traces"]
    assert result["total_utility"] == pytest.approx(result["base_utility"] + result["needs_utility"] - .8)
    assert result["gross_utility"] == pytest.approx(result["during_utility"] + result["one_time_utility"] + result["aftereffect_utility"] + result["needs_utility"] + result["energy_utility"])
    assert result["utility_per_action_hour"] == pytest.approx(result["gross_utility"] / 2)
    assert (model.model_dump(), encoded.model_dump(), exhausted.model_dump()) == before
    nodes = {n["id"]: n for n in result["graph"]["nodes"]}
    assert nodes["energy:mental_rest:adjusted"]["kind"] == "energy_reward"
    assert nodes["modifier:mental_rest"]["value"] == 2
    assert all(e["source"] in nodes and e["target"] in nodes for e in result["graph"]["edges"])
    assert "energy:mental_rest:utility" in {e["source"] for e in result["graph"]["edges"] if e["target"] == "energy_utility"}


def test_current_api_rest_bonus_reproduces_and_v7_history_is_not_reinterpreted(client, app):
    person = client.post("/api/persons", json={"name": "Rest test"}).json()
    encoded = client.post("/api/actions", json=action(mental_rest=1).model_dump()).json()
    request = {"person_id": person["id"], "action_ids": [encoded["id"]],
               "state": {"mental_energy": .2}, "horizon_hours": 0}
    fresh = client.post("/api/evaluations", json=request).json()
    assert fresh["engine_version"] == "8"
    assert fresh["results"][0]["total_utility"] == 1.5
    assert client.post(f"/api/evaluations/{fresh['id']}/reproduce").json()["matches"]
    historical = deepcopy(fresh)
    historical["engine_version"] = "7"
    with app.state.database.sessions.begin() as session:
        session.get(Evaluation, fresh["id"]).engine_version = "7"
    assert client.get(f"/api/evaluations/{fresh['id']}").json() == historical
    assert client.post(f"/api/evaluations/{fresh['id']}/reproduce").status_code == 409
    current = client.post("/api/evaluations", json=request).json()
    assert current["engine_version"] == "8"
    assert client.get(f"/api/evaluations/{fresh['id']}").json() == historical
