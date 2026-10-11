"""Likert scoring directions, conservative defaults, and atomic creation."""
from copy import deepcopy
import json
import math

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from app.core.initialization import (BRANCH_ITEMS, ITEMS, PARAMETER_SIGNALS, QUESTION_BY_ID, SIGNALS, VERSION,
                                     initialize_from_quiz, quiz_schema)
from app.db.models import Person, PersonModelVersion
from app.main import create_app
from app.schemas import PersonModel, default_model


def preview(client, answers, version=VERSION):
    return client.post("/api/person-initialization-quiz/preview", json={"version": version, "answers": answers})


def create(client, initialization=None):
    body = {"name": "Person", "description": "Initialization test"}
    if initialization is not None:
        body["initialization"] = initialization
    return client.post("/api/persons", json=body)


def model(client, person_id):
    return client.get(f"/api/persons/{person_id}/model").json()


def counts(app):
    with app.state.database.sessions() as session:
        return tuple(session.scalar(select(func.count()).select_from(cls)) for cls in (Person, PersonModelVersion))


def leaf_parameters(model):
    result = {}
    def visit(value, prefix=""):
        for key, member in value.items():
            if key == "family":
                continue
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(member, dict):
                visit(member, path)
            else:
                result[path] = member
    visit(model)
    return result


def test_flat_schema_is_short_friendly_likert_without_calibration_fields(client):
    schema = client.get("/api/person-initialization-quiz").json()
    assert schema == quiz_schema()
    assert set(schema) == {"version", "instructions", "options", "questions"}
    assert schema["version"] == "5"
    assert len(schema["questions"]) == len(ITEMS) == 44
    assert len({q["id"] for q in schema["questions"]}) == len(ITEMS)
    assert schema["options"] == [
        {"label": "Strongly disagree", "value": 1}, {"label": "Disagree", "value": 2},
        {"label": "Neither agree nor disagree", "value": 3}, {"label": "Agree", "value": 4},
        {"label": "Strongly agree", "value": 5}]
    for question in schema["questions"]:
        assert set(question) == {"id", "prompt", "example"}
        assert "you" in question["prompt"].lower()
        assert len(question["prompt"]) < 130 and question["example"]
    # Direct branch signals may use one statement, with conservative shrinkage.
    # Their evidence cannot be borrowed from the opposite branch.
    for weights in SIGNALS.values():
        assert len(weights) >= 1
        assert set(weights) <= set(QUESTION_BY_ID)
    baseline = leaf_parameters(default_model().model_dump(mode="json"))
    assert set(PARAMETER_SIGNALS) == {path for path in baseline if not path.endswith("curvature") and not path.startswith(("resources.", "homeostasis."))}


def test_neutral_skipped_and_all_null_answers_preserve_the_default_model(client, app):
    baseline = default_model().model_dump(mode="json")
    for answers in ({}, {key: None for key in QUESTION_BY_ID}, {key: 3 for key in QUESTION_BY_ID}):
        response = preview(client, answers)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["model"] == baseline
        assert result["total"] == len(ITEMS)
        assert 3 <= len(result["insights"]) <= 6
        assert result["answered"] == sum(value is not None for value in answers.values())
        if result["answered"] == 0:
            assert set(result["defaulted"]) == set(leaf_parameters(baseline))
    assert counts(app) == (0, 0)


def test_curvatures_are_explicit_defaults_for_every_response_shape(client):
    result = preview(client, {key: 5 for key in QUESTION_BY_ID}).json()
    baseline = leaf_parameters(default_model().model_dump(mode="json"))
    actual = leaf_parameters(result["model"])
    for path, value in baseline.items():
        if path.endswith("curvature"):
            assert actual[path] == value
            assert path in result["defaulted"]
    assert any("curvatures" in warning for warning in result["warnings"])


def test_one_answer_changes_related_fields_but_remains_shrunk_toward_defaults(client):
    result = preview(client, {"explore_ideas": 5}).json()
    features = result["model"]["features"]
    assert features["curiosity_engagement"]["reward_sensitivity"] == 1.25
    assert features["learning_gain"]["reward_sensitivity"] == 1
    assert features["mental_rest"]["reward_sensitivity"] == 1
    assert features["mental_effort"]["cost_sensitivity"] == 1
    assert features["goal_progress"] == default_model().features["goal_progress"].model_dump()
    assert features["stimulation_novelty"] == default_model().features["stimulation_novelty"].model_dump()
    assert result["model"]["aftereffects"]["inspiration"]["sensitivity"] > .3
    all_curiosity = preview(client, {"explore_ideas": 5, "learning_satisfies": 5}).json()
    assert all_curiosity["model"]["features"]["curiosity_engagement"]["reward_sensitivity"] == 1.25
    assert all_curiosity["model"]["features"]["learning_gain"]["reward_sensitivity"] == 1.25
    assert result["answered"] == 1
    assert "features.physical_pleasure.reward_sensitivity" in result["defaulted"]


def test_structure_uncertainty_and_reverse_items_have_independent_signed_directions(client):
    base = default_model().model_dump(mode="json")
    for answers, feature, direction in (
        ({"plan_ahead": 5}, "structure_planning", 1),
        ({"improvise_plan": 5}, "structure_planning", -1),
        ({"improvise_plan": 1}, "structure_planning", 1),
        ({"enjoy_uncertain_outcomes": 5}, "outcome_uncertainty", 1),
        ({"prefer_certainty": 5}, "outcome_uncertainty", -1),
        ({"prefer_certainty": 1}, "outcome_uncertainty", 1),
    ):
        result = preview(client, answers).json()["model"]
        assert direction * result["features"][feature]["preference_sensitivity"] > 0
        other = "outcome_uncertainty" if feature == "structure_planning" else "structure_planning"
        assert result["features"][other] == base["features"][other]
        assert result["features"]["autonomy_control"] == base["features"]["autonomy_control"]
        assert set(result["features"]) == set(base["features"])
    result = preview(client, {"try_new_experiences": 5}).json()["model"]["features"]
    assert result["structure_planning"] == base["features"]["structure_planning"]
    assert result["outcome_uncertainty"] == base["features"]["outcome_uncertainty"]
    assert result["stimulation_novelty"]["reward_sensitivity"] > .8
    assert result["learning_gain"] == base["features"]["learning_gain"]
    assert result["curiosity_engagement"] == base["features"]["curiosity_engagement"]
    assert result["goal_progress"] == base["features"]["goal_progress"]
    familiar = preview(client, {"prefer_familiar": 5}).json()["model"]["features"]
    assert familiar["stimulation_novelty"]["reward_sensitivity"] < .8
    assert familiar["structure_planning"] == base["features"]["structure_planning"]
    assert familiar["outcome_uncertainty"] == base["features"]["outcome_uncertainty"]


def test_social_reward_overload_closeness_and_belonging_remain_distinct(client):
    baseline = default_model().model_dump(mode="json")["features"]
    reward = preview(client, {"enjoy_conversation": 5}).json()["model"]["features"]
    assert reward["social_exposure"]["reward_sensitivity"] > .6
    assert reward["social_exposure"]["overload_sensitivity"] == .8
    assert reward["relatedness_intimacy"] == baseline["relatedness_intimacy"]
    assert reward["belonging_acceptance"] == baseline["belonging_acceptance"]
    overloaded = preview(client, {"crowds_drain": 5}).json()["model"]["features"]
    assert overloaded["social_exposure"]["overload_sensitivity"] > .8
    assert overloaded["social_exposure"]["reward_sensitivity"] == .6
    assert overloaded["relatedness_intimacy"] == baseline["relatedness_intimacy"]
    assert overloaded["belonging_acceptance"] == baseline["belonging_acceptance"]
    close = preview(client, {"value_closeness": 5}).json()["model"]["features"]
    assert close["relatedness_intimacy"]["positive_sensitivity"] > 1
    assert close["belonging_acceptance"] == baseline["belonging_acceptance"]


def test_mental_rest_physical_pleasure_are_separate_from_effort_cost_and_learning(client):
    mental = preview(client, {"enjoy_mental_rest": 5}).json()["model"]["features"]
    assert mental["mental_rest"]["reward_sensitivity"] > 1
    assert mental["mental_effort"]["cost_sensitivity"] == 1
    assert mental["learning_gain"]["reward_sensitivity"] == 1
    assert mental["curiosity_engagement"]["reward_sensitivity"] == 1
    assert mental["competence_mastery"]["positive_sensitivity"] == 1
    bodily = preview(client, {"enjoy_movement": 5}).json()["model"]["features"]
    assert bodily["physical_pleasure"]["reward_sensitivity"] == 1.25
    assert bodily["physical_effort"]["cost_sensitivity"] == 1
    assert bodily["mental_rest"]["reward_sensitivity"] == 1
    cost = preview(client, {"exertion_costly": 5, "concentration_costly": 5}).json()["model"]["features"]
    assert cost["physical_effort"]["cost_sensitivity"] > 1
    assert cost["mental_effort"]["cost_sensitivity"] > 1
    assert cost["physical_pleasure"]["reward_sensitivity"] == 1
    assert cost["mental_rest"]["reward_sensitivity"] == 1


@pytest.mark.parametrize("answer,feature,branch", [
    ("choose_your_way", "autonomy_control", "positive"), ("help_someone", "contribution_care", "positive"),
    ("value_progress", "goal_progress", "positive"), ("enjoy_recognition", "status_recognition", "positive"),
    ("enjoy_influence", "influence_power", "positive"), ("express_values", "identity_value_alignment", "positive"),
    ("failure_stings", "competence_mastery", "negative"),
    ("exclusion_hurts", "belonging_acceptance", "negative"), ("improve_skill", "competence_mastery", "positive"),
])
def test_specific_preferences_change_their_domain_without_collapsing_domains(client, answer, feature, branch):
    parameters = preview(client, {answer: 5}).json()["model"]["features"]
    other = "negative" if branch == "positive" else "positive"
    assert parameters[feature][f"{branch}_sensitivity"] > 1
    assert parameters[feature][f"{other}_sensitivity"] == 1
    if feature == "status_recognition":
        assert parameters["influence_power"]["positive_sensitivity"] == 1
    if feature == "influence_power":
        assert parameters["status_recognition"]["positive_sensitivity"] == 1


@pytest.mark.parametrize("feature,items", BRANCH_ITEMS.items())
def test_direct_liking_and_harm_answers_initialize_asymmetric_branches(client, feature, items):
    positive, negative = items
    result = preview(client, {positive: 1, negative: 5}).json()
    parameters = result["model"]["features"][feature]
    assert parameters["positive_sensitivity"] < 1
    assert parameters["negative_sensitivity"] > 1
    assert parameters["positive_sensitivity"] != parameters["negative_sensitivity"]
    for branch, item in (("positive", positive), ("negative", negative)):
        other = "negative" if branch == "positive" else "positive"
        partial = preview(client, {item: 5}).json()
        assert partial["model"]["features"][feature][f"{other}_sensitivity"] == 1
        assert f"features.{feature}.{other}_sensitivity" in partial["defaulted"]


def test_mastery_uses_direct_improvement_and_not_rest_or_curiosity_evidence(client):
    direct = preview(client, {"improve_skill": 5}).json()["model"]["features"]
    indirect = preview(client, {"enjoy_mental_rest": 5, "explore_ideas": 5}).json()["model"]["features"]
    assert direct["competence_mastery"]["positive_sensitivity"] == 1.25
    assert indirect["competence_mastery"]["positive_sensitivity"] == 1
    assert direct["physical_pleasure"]["reward_sensitivity"] == 1
    assert indirect["competence_mastery"]["negative_sensitivity"] == 1


def test_state_and_emotional_persistence_have_directional_reverse_scoring(client):
    answers = {"tired_thinking": 5, "tired_movement": 5, "stress_crowds": 5, "stress_setbacks": 5,
               "recover_quickly": 5, "good_feelings_fade": 1, "energy_recovers": 5, "completion_empty": 5}
    result = preview(client, answers).json()["model"]
    for key, baseline in default_model().transient.model_dump().items():
        assert result["transient"][key] > baseline
    effects = result["aftereffects"]
    assert effects["regret"]["half_life_hours"] < 12
    assert effects["guilt"]["half_life_hours"] < 12
    assert effects["accomplishment"]["half_life_hours"] > 12
    assert effects["pride_ego"]["half_life_hours"] > 6
    assert effects["fatigue"]["half_life_hours"] < 4
    assert effects["void"]["sensitivity"] > .3


def test_insights_change_with_answers_and_use_friendly_tendency_descriptions(client):
    curious = preview(client, {"explore_ideas": 5, "learning_satisfies": 5, "enjoy_mental_rest": 5}).json()
    familiar = preview(client, {"prefer_familiar": 5, "try_new_experiences": 1, "plan_ahead": 5}).json()
    assert curious["insights"] != familiar["insights"]
    assert any(i["label"] == "Exploring questions" and "rewarding" in i["description"] for i in curious["insights"])
    assert any(i["label"] == "New experiences" and "familiar" in i["description"] for i in familiar["insights"])
    assert 3 <= len(curious["insights"]) <= 6
    assert all(set(item) == {"label", "description"} for item in curious["insights"])


@pytest.mark.parametrize("choices", [1, 3, 5, "alternating"])
def test_every_parameter_stays_finite_bounded_and_valid_at_extreme_choices(choices):
    answers = {key: (1 if i % 2 else 5) if choices == "alternating" else choices for i, key in enumerate(QUESTION_BY_ID)}
    result = initialize_from_quiz(answers)
    PersonModel.model_validate(result["model"])
    baseline = leaf_parameters(default_model().model_dump(mode="json"))
    for path, value in leaf_parameters(result["model"]).items():
        assert math.isfinite(value)
        if path.endswith("preference_sensitivity"):
            assert -.8 <= value <= .8
        elif path.endswith("curvature"):
            assert value == baseline[path]
        elif path.endswith("half_life_hours"):
            assert .25 * baseline[path] <= value <= 4 * baseline[path]
        else:
            assert .25 * baseline[path] <= value <= 1.75 * baseline[path]


def test_preview_create_exact_model_equality_atomic_v1_and_restart(tmp_path):
    url = "sqlite:///" + (tmp_path / "quiz.db").as_posix()
    answers = {key: 1 if i % 3 else 5 for i, key in enumerate(QUESTION_BY_ID)}
    with TestClient(create_app(url)) as client:
        expected = preview(client, answers).json()["model"]
        assert client.get("/api/persons").json() == []
        response = create(client, {"method": "quiz", "version": VERSION, "answers": answers})
        assert response.status_code == 201, response.text
        person = response.json()
        stored = model(client, person["id"])
        assert stored["version"] == 1 and stored["model"] == expected
        assert len(client.get(f"/api/persons/{person['id']}/model-versions").json()) == 1
    with TestClient(create_app(url)) as client:
        assert model(client, person["id"])["model"] == expected


def test_default_copy_exact_history_ownership_isolation_and_metadata_contract(client, app):
    source = create(client).json()
    initial = model(client, source["id"])
    assert initial["model"] == default_model().model_dump(mode="json")
    explicit = create(client, {"method": "default"}).json()
    assert model(client, explicit["id"])["model"] == initial["model"]
    edited = deepcopy(initial["model"])
    edited["features"]["goal_progress"]["positive_sensitivity"] = 7
    historical = client.put(f"/api/persons/{source['id']}/model", json=edited).json()
    edited["features"]["goal_progress"]["positive_sensitivity"] = 11
    client.put(f"/api/persons/{source['id']}/model", json=edited)
    target = create(client, {"method": "copy", "person_id": source["id"], "model_version_id": historical["id"]}).json()
    copied = model(client, target["id"])
    assert copied["version"] == 1 and copied["model"] == historical["model"]
    copied["model"]["features"]["goal_progress"]["positive_sensitivity"] = 20
    client.put(f"/api/persons/{target['id']}/model", json=copied["model"])
    assert model(client, source["id"])["model"]["features"]["goal_progress"]["positive_sensitivity"] == 11
    assert client.get(f"/api/persons/{source['id']}/model-versions/{historical['id']}").json() == historical
    path = f"/api/persons/{source['id']}"
    assert client.put(path, json={"name": "Changed", "initialization": {"method": "default"}}).status_code == 422
    before = counts(app)
    for person_id, version_id in (("missing", initial["id"]), (explicit["id"], initial["id"]), (source["id"], "missing")):
        assert create(client, {"method": "copy", "person_id": person_id, "model_version_id": version_id}).status_code == 404
        assert counts(app) == before
    client.delete(path)
    assert create(client, {"method": "copy", "person_id": source["id"], "model_version_id": initial["id"]}).status_code == 404
    assert counts(app) == before


@pytest.mark.parametrize("answers", [
    {"unknown": 1}, {"unknown": None}, {"feature.goal_progress.positive.strong": 5},
    {"enjoy_thinking": 5}, {"try_unplanned": 5}, {"comfortable_uncertainty": 5},
    {"explore_ideas": True}, {"explore_ideas": "3"}, {"explore_ideas": 3.0},
    {"explore_ideas": 2.5}, {"explore_ideas": 0}, {"explore_ideas": 6},
    {"explore_ideas": 10**1000}, {"explore_ideas": []},
])
def test_invalid_choices_are_strict_and_atomic(client, app, answers):
    assert preview(client, answers).status_code == 422
    assert create(client, {"method": "quiz", "version": VERSION, "answers": answers}).status_code == 422
    assert counts(app) == (0, 0)


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_nonfinite_choices_rejected_without_writes(client, app, invalid):
    initialization = {"method": "quiz", "version": VERSION, "answers": {"explore_ideas": invalid}}
    for path, body in (("/api/person-initialization-quiz/preview", {k: v for k, v in initialization.items() if k != "method"}),
                       ("/api/persons", {"name": "Person", "initialization": initialization})):
        result = client.post(path, content=json.dumps(body), headers={"Content-Type": "application/json"})
        assert result.status_code == 422, result.text
    assert counts(app) == (0, 0)


@pytest.mark.parametrize("version", ["1", "2", "3", "4", "6", 5])
def test_old_and_unknown_versions_cannot_be_reinterpreted(client, app, version):
    assert preview(client, {"explore_ideas": 5}, version).status_code == 422
    assert create(client, {"method": "quiz", "version": version, "answers": {"explore_ideas": 5}}).status_code == 422
    assert counts(app) == (0, 0)


def test_invalid_initialization_and_answer_container_are_rejected(client, app):
    for initialization in ({"method": "copy", "person_id": "x"}, {"method": "invented"},
                           {"method": "default", "answers": {}}, {"method": "quiz", "version": VERSION, "answers": []}):
        assert create(client, initialization).status_code == 422
    assert counts(app) == (0, 0)
