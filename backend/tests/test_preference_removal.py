"""Retired feature rejection, saved-input compatibility, and immutable history."""
from copy import deepcopy

from pydantic import ValidationError
import pytest
from sqlalchemy import select

from app.core.compatibility import normalize_action, normalize_model
from app.core.ontology import FEATURE_KEYS
from app.db.models import Action, Evaluation, EvaluationResult, PersonModelVersion
from app.schemas import ActionInput, PersonModel, default_model


def current_action():
    return {"title": "Saved action", "duration_minutes": 60, "net_money_cost": 0,
            "features": {key: .2 for key in FEATURE_KEYS},
            "feature_notes": {"goal_progress": "Retained note"}}


def earlier_inputs(legacy_order=False):
    action, model = current_action(), default_model().model_dump(mode="json")
    for old_key, effort_key, pleasure_key in (("cognitive_demand", "mental_effort", "mental_rest"),
                                             ("physical_demand", "physical_effort", "physical_pleasure")):
        action["features"][old_key] = action["features"].pop(effort_key)
        del action["features"][pleasure_key]
        effort = model["features"].pop(effort_key)
        pleasure = model["features"].pop(pleasure_key)
        model["features"][old_key] = {"family": "signed_effort", "effort_sensitivity": effort["cost_sensitivity"],
                                       "effort_curvature": effort["curvature"], "pleasure_sensitivity": pleasure["reward_sensitivity"],
                                       "pleasure_curvature": pleasure["curvature"]}
    action["features"]["learning_curiosity"] = action["features"].pop("learning_gain")
    del action["features"]["curiosity_engagement"]
    model["features"]["learning_curiosity"] = model["features"].pop("learning_gain")
    del model["features"]["curiosity_engagement"]
    action["features"]["order_uncertainty"] = action["features"].pop("structure_planning")
    del action["features"]["outcome_uncertainty"]
    model["features"]["order_uncertainty"] = model["features"].pop("structure_planning")
    del model["features"]["outcome_uncertainty"]
    action["features"]["preference_alignment"] = .9
    action["feature_notes"]["preference_alignment"] = "Retired note"
    model["features"]["preference_alignment"] = deepcopy(model["features"]["goal_progress"])
    if legacy_order:
        del action["features"]["order_uncertainty"]
        action["features"].update(closure_order=.8, security_tranquility=-.2)
        action["feature_notes"].update(closure_order="Plan", security_tranquility="Risk")
        del model["features"]["order_uncertainty"]
        for key in ("closure_order", "security_tranquility"):
            model["features"][key] = deepcopy(model["features"]["goal_progress"])
        for key in ("cognitive_demand", "physical_demand"):
            model["features"][key] = {"family": "cost", "cost_sensitivity": 2, "curvature": 1.5}
        del model["resources"]
        del action["net_money_cost"]
    return action, model


@pytest.mark.parametrize("legacy_order", [False, True])
def test_saved_16_and_17_feature_inputs_project_without_mutation(legacy_order):
    action, model = earlier_inputs(legacy_order)
    original = deepcopy((action, model))
    projected_action, converted_action = normalize_action(action)
    projected_model, converted_model = normalize_model(model)
    assert converted_action and converted_model
    assert set(projected_action["features"]) == set(FEATURE_KEYS)
    assert set(projected_model["features"]) == set(FEATURE_KEYS)
    assert "preference_alignment" not in projected_action["feature_notes"]
    assert projected_action["feature_notes"]["goal_progress"] == "Retained note"
    ActionInput.model_validate(projected_action)
    PersonModel.model_validate(projected_model)
    if legacy_order:
        assert projected_action["features"]["structure_planning"] == pytest.approx(.3)
        assert "Plan" in projected_action["feature_notes"]["structure_planning"]
        assert "Risk" in projected_action["feature_notes"]["structure_planning"]
        assert projected_model["features"]["mental_effort"]["cost_sensitivity"] == 2
        assert projected_model["resources"] == {"time_value": 0, "money_value": 0}
    assert (action, model) == original
    assert normalize_action(projected_action) == (projected_action, False)
    assert normalize_model(projected_model) == (projected_model, False)


def test_retired_feature_is_rejected_in_new_action_model_notes_and_quiz(client):
    old_action, old_model = earlier_inputs()
    with pytest.raises(ValidationError):
        ActionInput.model_validate(old_action)
    with pytest.raises(ValidationError):
        PersonModel.model_validate(old_model)
    assert client.post("/api/actions", json=old_action).status_code == 422
    notes_only = current_action()
    notes_only["feature_notes"]["preference_alignment"] = "Retired"
    assert client.post("/api/actions", json=notes_only).status_code == 422
    for identifier in ("strong_likes", "strong_dislikes"):
        assert client.post("/api/person-initialization-quiz/preview",
                           json={"version": "5", "answers": {identifier: 5}}).status_code == 422


@pytest.mark.parametrize("historical_version", ["3", "4"])
def test_saved_inputs_still_edit_copy_evaluate_while_earlier_history_stays_exact(client, app, historical_version):
    person = client.post("/api/persons", json={"name": "Earlier person"}).json()
    path = f"/api/persons/{person['id']}"
    version = client.get(path + "/model").json()
    action = client.post("/api/actions", json=current_action()).json()
    request = {"person_id": person["id"], "action_ids": [action["id"]], "state": {}}
    history = client.post("/api/evaluations", json=request).json()
    old_action, old_model = earlier_inputs()
    history["engine_version"] = historical_version
    history["model_snapshot"] = old_model
    history["results"][0]["action_snapshot"] = old_action
    # Historical feature traces remain available, including removed features.
    history["results"][0]["feature_traces"].append({"feature_key": "preference_alignment", "response_value": .9})
    with app.state.database.sessions() as session, session.begin():
        session.get(PersonModelVersion, version["id"]).model = old_model
        saved_action = session.get(Action, action["id"])
        saved_action.features = old_action["features"]
        saved_action.feature_notes = old_action["feature_notes"]
        historical = session.get(Evaluation, history["id"])
        historical.engine_version = historical_version
        historical.model_snapshot = old_model
        result = session.scalars(select(EvaluationResult).where(EvaluationResult.evaluation_id == history["id"])).one()
        result.action_snapshot = old_action
        stored_result = deepcopy(result.result)
        stored_result["feature_traces"] = history["results"][0]["feature_traces"]
        result.result = stored_result
    view = client.get(path + "/model").json()
    assert view["converted_from_legacy"] is True
    assert set(view["model"]["features"]) == set(FEATURE_KEYS)
    viewed_action = client.get(f"/api/actions/{action['id']}").json()
    assert viewed_action["converted_from_legacy"] is True
    assert "preference_alignment" not in viewed_action["features"]
    assert "preference_alignment" not in viewed_action["feature_notes"]
    assert client.get(f"/api/evaluations/{history['id']}").json() == history
    assert client.post(f"/api/evaluations/{history['id']}/reproduce").status_code == 409
    copied = client.post("/api/persons", json={"name": "Copied person", "initialization": {
        "method": "copy", "person_id": person["id"], "model_version_id": version["id"]}})
    assert copied.status_code == 201, copied.text
    assert client.get(f"/api/persons/{copied.json()['id']}/model").json()["model"] == view["model"]
    current = client.post("/api/evaluations", json=request)
    assert current.status_code == 201, current.text
    current = current.json()
    assert current["engine_version"] == "5"
    assert set(current["model_snapshot"]["features"]) == set(FEATURE_KEYS)
    assert {t["feature_key"] for t in current["results"][0]["feature_traces"]} == set(FEATURE_KEYS)
    assert client.post(f"/api/evaluations/{current['id']}/reproduce").json()["matches"] is True
    assert client.put(path + "/model", json=view["model"]).status_code == 200
    assert client.put(f"/api/actions/{action['id']}", json={k: viewed_action[k] for k in current_action()}).status_code == 200
    assert client.get(f"/api/evaluations/{history['id']}").json() == history
    with app.state.database.sessions() as session:
        assert session.get(PersonModelVersion, version["id"]).model == old_model
        assert "preference_alignment" not in session.get(Action, action["id"]).features


def test_legacy_general_mental_pleasure_is_not_inferred_as_rest():
    action, model = earlier_inputs()
    action["features"].update(cognitive_demand=-.8, physical_demand=-.6, order_uncertainty=-.7)
    model["features"]["cognitive_demand"].update(pleasure_sensitivity=7, pleasure_curvature=2)
    model["features"]["physical_demand"].update(pleasure_sensitivity=3, pleasure_curvature=1.5)
    model["features"]["order_uncertainty"]["preference_sensitivity"] = 2
    original = deepcopy((action, model))
    projected_action = normalize_action(action)[0]
    projected_model = normalize_model(model)[0]
    assert projected_action["features"]["mental_effort"] == projected_action["features"]["mental_rest"] == 0
    assert projected_model["features"]["mental_rest"] == {"family": "reward", "reward_sensitivity": 1, "curvature": 1}
    assert projected_action["features"]["physical_effort"] == 0
    assert projected_action["features"]["physical_pleasure"] == .6
    assert projected_model["features"]["physical_pleasure"] == {"family": "reward", "reward_sensitivity": 3, "curvature": 1.5}
    assert projected_action["features"]["structure_planning"] == 0
    assert projected_action["features"]["outcome_uncertainty"] == .7
    assert projected_model["features"]["structure_planning"]["preference_sensitivity"] == 2
    assert projected_model["features"]["outcome_uncertainty"]["preference_sensitivity"] == -2
    assert projected_action["features"]["curiosity_engagement"] == 0
    assert (action, model) == original
