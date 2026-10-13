"""Independent experiences, actual exposures, and persisted v5 timing."""
from copy import deepcopy
import math
import sqlite3

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.core.ontology import FEATURE_KEYS
from app.core.utility import evaluate
from app.main import create_app
from app.schemas import ActionInput, TransientState, default_model


def encoded(duration=60, exposures=None, **features):
    return ActionInput(title="Independent experiences", duration_minutes=duration, net_money_cost=0,
                       features={key: features.get(key, 0) for key in FEATURE_KEYS}, feature_duration_minutes=exposures)


def test_effort_rest_and_bodily_pleasure_can_coexist_with_separate_responses():
    model = default_model()
    model.features["mental_effort"].cost_sensitivity = 2
    model.features["mental_rest"].reward_sensitivity = 3
    model.features["physical_effort"].cost_sensitivity = 3
    model.features["physical_pleasure"].reward_sensitivity = 4
    action = encoded(120, mental_effort=.8, mental_rest=.3, physical_effort=.7, physical_pleasure=.8)
    rested = evaluate(action, model, TransientState(mental_energy=1, physical_energy=1), 0)
    traces = {t["feature_key"]: t for t in rested["feature_traces"]}
    assert traces["mental_effort"]["utility_contribution"] == pytest.approx(-3.2)
    assert traces["mental_rest"]["utility_contribution"] == pytest.approx(1.8)
    assert traces["physical_effort"]["utility_contribution"] == pytest.approx(-4.2)
    assert traces["physical_pleasure"]["utility_contribution"] == pytest.approx(6.4)
    assert rested["during_utility"] == pytest.approx(.8)
    tired = evaluate(action, model, TransientState(mental_energy=0, physical_energy=0), 0)
    tired_traces = {t["feature_key"]: t for t in tired["feature_traces"]}
    assert tired_traces["mental_rest"] == traces["mental_rest"]
    assert tired_traces["physical_pleasure"] == traces["physical_pleasure"]
    assert tired["during_utility"] == pytest.approx(.8)
    assert tired["energy_utility"] == pytest.approx(-.7 * (3.2 + 4.2) + .7 * 1.8)
    assert rested["energy_utility"] == pytest.approx(.3 * (3.2 + 4.2))


def test_structure_uncertainty_and_autonomy_vary_independently():
    model = default_model()
    model.features["structure_planning"].preference_sensitivity = 2
    model.features["outcome_uncertainty"].preference_sensitivity = -3
    free = evaluate(encoded(structure_planning=1, outcome_uncertainty=1, autonomy_control=1), model, TransientState(), 0)
    imposed = evaluate(encoded(structure_planning=1, outcome_uncertainty=1, autonomy_control=-1), model, TransientState(), 0)
    assert free["total_utility"] == 0
    assert imposed["total_utility"] == -2
    assert free["one_time_utility"] == imposed["one_time_utility"] == 0
    model.features["outcome_uncertainty"].preference_sensitivity = 3
    assert evaluate(encoded(structure_planning=1, outcome_uncertainty=1), model, TransientState(), 0)["during_utility"] == 5
    uncertain = evaluate(encoded(outcome_uncertainty=1), model, TransientState())
    assert next(t for t in uncertain["aftereffect_traces"] if t["name"] == "guilt")["trigger"] == 0


def test_knowledge_counts_once_while_brief_closeness_uses_actual_exposure():
    action = encoded(120, {"relatedness_intimacy": 15}, learning_gain=.4, relatedness_intimacy=.8)
    result = evaluate(action, default_model(), TransientState(), 0)
    assert result["one_time_utility"] == .4
    assert result["during_utility"] == pytest.approx(.2)
    assert result["during_rate"] == pytest.approx(.1)
    assert result["total_utility"] == pytest.approx(.6)
    trace = next(t for t in result["feature_traces"] if t["feature_key"] == "relatedness_intimacy")
    assert trace["exposure_duration_minutes"] == 15
    assert trace["exposure_duration_hours"] == .25
    nodes = {n["id"]: n for n in result["graph"]["nodes"]}
    assert nodes["exposure:relatedness_intimacy"]["value"] == .25
    assert nodes["exposure_minutes:relatedness_intimacy"]["kind"] == "input"
    assert nodes["exposure_minutes:relatedness_intimacy"]["value"] == 15
    assert {e["source"] for e in result["graph"]["edges"] if e["target"] == "exposure:relatedness_intimacy"} == {"exposure_minutes:relatedness_intimacy"}
    assert nodes["during_utility"]["formula"] == "sum(rate_response_i * exposure_hours_i)"


def test_zero_exposure_disables_experience_and_its_aftereffect_signals():
    action = encoded(120, {"competence_mastery": 0, "curiosity_engagement": 0, "mental_effort": 0},
                     competence_mastery=1, curiosity_engagement=1, mental_effort=1)
    result = evaluate(action, default_model(), TransientState())
    assert result["during_utility"] == result["during_rate"] == result["aftereffect_utility"] == 0


def test_fatigue_uses_each_effort_exposure_and_rest_does_not_add_fatigue():
    action = encoded(120, {"mental_effort": 30, "physical_effort": 60},
                     mental_effort=.8, physical_effort=.6, mental_rest=1, physical_pleasure=1)
    result = evaluate(action, default_model(), TransientState())
    fatigue = next(t for t in result["aftereffect_traces"] if t["name"] == "fatigue")
    assert fatigue["trigger"] == pytest.approx(.4 * (1 - math.exp(-.25)) + .3 * (1 - math.exp(-.5)))
    assert next(t for t in evaluate(encoded(mental_rest=1, physical_pleasure=1), default_model(), TransientState())["aftereffect_traces"]
                if t["name"] == "fatigue")["trigger"] == 0


@pytest.mark.parametrize("exposures", [{"mental_rest": -1}, {"mental_rest": 61}, {"mental_rest": math.inf},
                                      {"mental_rest": math.nan}, {"goal_progress": 1}, {"unknown": 1}])
def test_exposure_overrides_reject_invalid_durations_and_one_time_keys(exposures):
    with pytest.raises(ValidationError):
        encoded(exposures=exposures)


def test_exposure_boundary_revalidates_mutated_nested_maps():
    action = encoded(exposures={"mental_rest": 30})
    action.feature_duration_minutes["mental_rest"] = 61
    with pytest.raises(ValidationError):
        evaluate(action, default_model(), TransientState())


def test_exposure_schema_upgrade_and_history_survive_restart(tmp_path):
    path = tmp_path / "exposures.db"
    url = "sqlite:///" + path.as_posix()
    with TestClient(create_app(url)) as initial:
        person = initial.post("/api/persons", json={"name": "Exposure test"}).json()
        action = initial.post("/api/actions", json=encoded().model_dump()).json()
    # Recreate the earlier action table shape; migration is additive/idempotent.
    with sqlite3.connect(path) as db:
        db.execute("ALTER TABLE actions DROP COLUMN feature_duration_minutes")
    with TestClient(create_app(url)) as upgraded:
        assert upgraded.get(f"/api/actions/{action['id']}").json()["feature_duration_minutes"] is None
        update = encoded(120, {"mental_rest": 15}, mental_rest=.8).model_dump()
        saved = upgraded.put(f"/api/actions/{action['id']}", json=update)
        assert saved.status_code == 200, saved.text
        history = upgraded.post("/api/evaluations", json={"person_id": person["id"], "action_ids": [action["id"]], "state": {}, "horizon_hours": 0}).json()
        assert history["engine_version"] == "8"
        assert history["results"][0]["during_utility"] == pytest.approx(.2)
        assert history["results"][0]["action_snapshot"]["feature_duration_minutes"] == {"mental_rest": 15}
        updated = deepcopy(update)
        updated["feature_duration_minutes"]["mental_rest"] = 120
        assert upgraded.put(f"/api/actions/{action['id']}", json=updated).status_code == 200
    with TestClient(create_app(url)) as restarted:
        assert restarted.get(f"/api/evaluations/{history['id']}").json() == history
        assert restarted.post(f"/api/evaluations/{history['id']}/reproduce").json()["matches"] is True
        assert restarted.get(f"/api/actions/{action['id']}").json()["feature_duration_minutes"] == {"mental_rest": 120}
