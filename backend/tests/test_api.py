from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import math
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.ontology import ONTOLOGY
from app.db.database import default_database_url
from app.db.models import Evaluation, EvaluationResult, PersonModelVersion
from app.schemas import default_model
from app.seed import seed
from app.main import create_app


def state():
    return {"mental_energy": 0.5, "physical_energy": 0.5, "acute_stress": 0,
            "date": "2026-10-06", "notes": None}


def action(title="Test action", **values):
    features = {feature["key"]: 0 for feature in ONTOLOGY}
    features.update(values)
    return {"title": title, "duration_minutes": 60, "net_money_cost": 0, "features": features,
            "feature_notes": {"goal_progress": "Caller-provided test encoding"}}


def person(client):
    response = client.post("/api/persons", json={"name": "Ada", "description": "Manually parameterized"})
    assert response.status_code == 201, response.text
    return response.json()


def new_action(client, **values):
    response = client.post("/api/actions", json=action(**values))
    assert response.status_code == 201, response.text
    return response.json()


def evaluate_actions(client, person_id, action_ids, **overrides):
    body = {"person_id": person_id, "action_ids": action_ids, "state": state(), "horizon_hours": 168}
    body.update(overrides)
    return client.post("/api/evaluations", json=body)


def test_health_ontology_and_empty_startup(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/ontology").json() == {"features": ONTOLOGY}
    assert len(ONTOLOGY) == 19
    assert client.get("/api/persons").json() == []
    assert client.get("/api/actions").json() == []


def test_delete_person_preserves_history_and_blocks_person_operations(client):
    created = person(client)
    other = person(client)
    path = f"/api/persons/{created['id']}"
    version = client.get(f"{path}/model").json()
    client.put(f"{path}/model", json=version["model"])
    encoded = new_action(client, goal_progress=0.6)
    historical = evaluate_actions(client, created["id"], [encoded["id"]]).json()
    assert client.put("/api/daily-state", json={"person_id": created["id"], "state": state()}).status_code == 200
    response = client.delete(path)
    assert response.status_code == 204 and response.content == b""
    assert client.get("/api/persons").json() == [other]
    assert client.get(f"/api/persons/{other['id']}/model").status_code == 200
    assert client.get("/api/actions").json() == [encoded]
    assert client.get(f"/api/evaluations/{historical['id']}").json() == historical
    assert client.get("/api/evaluations").json()[0]["id"] == historical["id"]
    assert client.post(f"/api/evaluations/{historical['id']}/reproduce").json()["matches"] is True
    for suffix in ("", "/model", "/model-versions", f"/model-versions/{version['id']}"):
        assert client.get(path + suffix).status_code == 404
    assert client.put(path, json={"name": "Restored"}).status_code == 404
    assert client.put(f"{path}/model", json=version["model"]).status_code == 404
    assert client.get("/api/daily-state", params={"person_id": created["id"], "date": state()["date"]}).status_code == 404
    assert client.put("/api/daily-state", json={"person_id": created["id"], "state": state()}).status_code == 404
    assert evaluate_actions(client, created["id"], [encoded["id"]], model_version_id=version["id"]).status_code == 404
    assert client.delete(path).status_code == 404
    assert client.delete("/api/persons/missing").status_code == 404
    assert client.get(f"/api/evaluations/{historical['id']}").json() == historical


def test_delete_last_person_leaves_empty_list(client):
    created = person(client)
    assert client.delete(f"/api/persons/{created['id']}").status_code == 204
    assert client.get("/api/persons").json() == []
    replacement = person(client)
    assert replacement["id"] != created["id"]
    assert client.get("/api/persons").json() == [replacement]


def test_legacy_database_upgrade_preserves_snapshots_and_deleted_person_stays_deleted(tmp_path):
    database_path = tmp_path / "legacy.db"
    database_url = "sqlite:///" + database_path.as_posix()
    with TestClient(create_app(database_url)) as initial:
        created = person(initial)
        encoded = new_action(initial, goal_progress=0.6)
        historical = evaluate_actions(initial, created["id"], [encoded["id"]]).json()
        versions = initial.get(f"/api/persons/{created['id']}/model-versions").json()
    # The prior schema has identical tables except for this new nullable column.
    with sqlite3.connect(database_path) as connection:
        connection.execute("ALTER TABLE persons DROP COLUMN deleted_at")
    with TestClient(create_app(database_url)) as upgraded:
        assert upgraded.get("/api/persons").json() == [created]
        assert upgraded.get(f"/api/persons/{created['id']}/model-versions").json() == versions
        assert upgraded.get(f"/api/evaluations/{historical['id']}").json() == historical
        assert upgraded.delete(f"/api/persons/{created['id']}").status_code == 204
    with TestClient(create_app(database_url)) as reopened:
        assert reopened.get("/api/persons").json() == []
        assert reopened.get(f"/api/evaluations/{historical['id']}").json() == historical
        assert reopened.post(f"/api/evaluations/{historical['id']}/reproduce").json()["matches"] is True
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_person_and_model_versions_are_immutable(client, app):
    created = person(client)
    assert client.get(f"/api/persons/{created['id']}").json() == created
    assert client.get("/api/persons").json() == [created]
    initial = client.get(f"/api/persons/{created['id']}/model").json()
    assert initial["version"] == 1
    assert initial["model"] == default_model().model_dump(mode="json")
    modified = deepcopy(initial["model"])
    modified["features"]["goal_progress"]["positive_sensitivity"] = 3.5
    response = client.put(f"/api/persons/{created['id']}/model", json=modified)
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2
    assert response.json()["id"] != initial["id"]
    with app.state.database.sessions() as session:
        assert session.get(PersonModelVersion, initial["id"]).model == initial["model"]


def test_edit_person_metadata_preserves_model_versions_and_history(client, monkeypatch):
    created = person(client)
    path = f"/api/persons/{created['id']}"
    initial_model = client.get(f"{path}/model").json()
    encoded = new_action(client, goal_progress=0.6)
    historical = evaluate_actions(client, created["id"], [encoded["id"]]).json()
    edited_at = "2030-01-01T00:00:00+00:00"
    monkeypatch.setattr("app.api.routes.timestamp", lambda: edited_at)

    response = client.put(path, json={"name": "  Grace  ", "description": "Edited description"})
    assert response.status_code == 200, response.text
    expected = created | {"name": "Grace", "description": "Edited description", "updated_at": edited_at}
    assert response.json() == expected
    assert client.get(path).json() == expected
    assert client.get("/api/persons").json() == [expected]
    assert client.get(f"{path}/model").json() == initial_model
    assert client.get(f"{path}/model-versions").json() == [initial_model]
    assert client.get(f"/api/evaluations/{historical['id']}").json() == historical
    assert client.get("/api/evaluations").json()[0]["person_name"] == "Ada"
    assert client.post(f"/api/evaluations/{historical['id']}/reproduce").json()["matches"] is True
    current = evaluate_actions(client, created["id"], [encoded["id"]]).json()
    assert current["person_name"] == "Grace"
    assert current["model_version_id"] == initial_model["id"]
    assert client.put(path, json={"name": "Grace"}).json()["description"] is None


@pytest.mark.parametrize("body", [
    {"name": "  "},
    {"name": "x" * 201},
    {"name": "Ada", "description": "x" * 20001},
    {"name": "Ada", "unexpected": True},
    {"description": "Missing name"},
])
def test_edit_person_validates_input_without_mutation(client, body):
    created = person(client)
    path = f"/api/persons/{created['id']}"
    assert client.put(path, json=body).status_code == 422
    assert client.get(path).json() == created
    assert len(client.get(f"{path}/model-versions").json()) == 1
    assert client.put("/api/persons/missing", json={"name": "Ada"}).status_code == 404


def test_browse_model_versions_returns_exact_models_newest_first_and_checks_ownership(client):
    created = person(client)
    other = person(client)
    path = f"/api/persons/{created['id']}"
    initial = client.get(f"{path}/model").json()
    modified = deepcopy(initial["model"])
    modified["features"]["goal_progress"]["positive_sensitivity"] = 3.5
    second = client.put(f"{path}/model", json=modified).json()
    modified["features"]["goal_progress"]["positive_sensitivity"] = 7
    third = client.put(f"{path}/model", json=modified).json()

    response = client.get(f"{path}/model-versions")
    assert response.status_code == 200, response.text
    assert response.json() == [third, second, initial]
    for version in [initial, second, third]:
        response = client.get(f"{path}/model-versions/{version['id']}")
        assert response.status_code == 200, response.text
        assert response.json() == version
    assert client.get(f"{path}/model").json() == third
    other_path = f"/api/persons/{other['id']}/model-versions"
    assert len(client.get(other_path).json()) == 1
    assert client.get(f"{other_path}/{initial['id']}").status_code == 404
    assert client.get(f"{path}/model-versions/missing").status_code == 404
    assert client.get("/api/persons/missing/model-versions").status_code == 404
    assert client.get(f"/api/persons/missing/model-versions/{initial['id']}").status_code == 404


def test_evaluation_can_select_older_model_version_and_default_remains_latest(client):
    created = person(client)
    path = f"/api/persons/{created['id']}/model"
    initial = client.get(path).json()
    encoded = new_action(client, goal_progress=0.6)
    historical = evaluate_actions(client, created["id"], [encoded["id"]]).json()
    modified = deepcopy(initial["model"])
    modified["features"]["goal_progress"]["positive_sensitivity"] = 20
    latest = client.put(path, json=modified).json()

    response = evaluate_actions(client, created["id"], [encoded["id"]], model_version_id=initial["id"])
    assert response.status_code == 201, response.text
    selected = response.json()
    assert selected["model_version_id"] == initial["id"]
    assert selected["model_version"] == 1
    assert selected["model_snapshot"] == initial["model"]
    assert selected["results"] == historical["results"]
    assert client.get(f"/api/evaluations/{selected['id']}").json() == selected
    assert client.post(f"/api/evaluations/{selected['id']}/reproduce").json()["matches"] is True
    for overrides in ({}, {"model_version_id": None}, {"model_version_id": latest["id"]}):
        current = evaluate_actions(client, created["id"], [encoded["id"]], **overrides).json()
        assert current["model_version_id"] == latest["id"]
        assert current["model_version"] == 2
        assert current["model_snapshot"] == latest["model"]
        assert current["results"][0]["total_utility"] != selected["results"][0]["total_utility"]


def test_evaluation_rejects_missing_and_cross_person_versions_atomically(client, app):
    created = person(client)
    other = person(client)
    other_version = client.get(f"/api/persons/{other['id']}/model").json()
    encoded = new_action(client, goal_progress=0.6)
    for version_id in ("missing", "", other_version["id"]):
        response = evaluate_actions(client, created["id"], [encoded["id"]], model_version_id=version_id)
        assert response.status_code == 404, response.text
    with app.state.database.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Evaluation)) == 0
        assert session.scalar(select(func.count()).select_from(EvaluationResult)) == 0


def test_concurrent_model_edits_have_unique_sequential_versions(client):
    created = person(client)
    path = f"/api/persons/{created['id']}/model"
    model = client.get(path).json()["model"]
    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(lambda _: client.put(path, json=model), range(8)))
    assert all(response.status_code == 200 for response in responses)
    assert sorted(response.json()["version"] for response in responses) == list(range(2, 10))


def test_daily_state_is_separate_per_person_and_date(client):
    created = person(client)
    other = person(client)
    params = {"person_id": created["id"], "date": "2026-10-06"}
    assert client.get("/api/daily-state", params=params).json() == state()
    updated = state() | {"mental_energy": 0.1, "notes": "Poor sleep"}
    assert client.put("/api/daily-state", json={"person_id": created["id"], "state": updated}).json() == updated
    assert client.get("/api/daily-state", params=params).json() == updated
    assert client.get("/api/daily-state", params=params | {"person_id": other["id"]}).json() == state()
    assert client.get("/api/daily-state", params=params | {"date": "2026-10-07"}).json()["mental_energy"] == 0.5


def test_action_crud_and_zero_duration(client):
    created = new_action(client, goal_progress=0.8)
    path = f"/api/actions/{created['id']}"
    assert client.get(path).json() == created
    assert client.get("/api/actions").json() == [created]
    body = action("Edited", goal_progress=-0.3) | {"duration_minutes": 0}
    changed = client.put(path, json=body)
    assert changed.status_code == 200
    assert changed.json()["id"] == created["id"]
    assert changed.json()["duration_minutes"] == 0
    who = person(client)
    evaluated = evaluate_actions(client, who["id"], [created["id"]]).json()
    assert evaluated["results"][0]["during_utility"] == 0
    assert evaluated["results"][0]["utility_per_action_hour"] is None
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404


def test_evaluation_ranked_by_total_with_deterministic_ties(client):
    who = person(client)
    good = new_action(client, title="Good", goal_progress=0.8)
    bad = new_action(client, title="Bad", goal_progress=-0.8)
    tie = new_action(client, title="Tie", goal_progress=0.8)
    first = evaluate_actions(client, who["id"], [bad["id"], good["id"], tie["id"]])
    assert first.status_code == 201, first.text
    rows = first.json()["results"]
    assert [row["rank"] for row in rows] == [1, 2, 3]
    assert [row["action_id"] for row in rows[:2]] == sorted([good["id"], tie["id"]])
    assert rows[-1]["action_id"] == bad["id"]
    assert rows[0]["total_utility"] > rows[-1]["total_utility"]
    second = evaluate_actions(client, who["id"], [tie["id"], good["id"], bad["id"]])
    assert first.json()["results"] == second.json()["results"]
    history = client.get("/api/evaluations").json()
    assert history[0]["action_count"] == 3
    assert history[0]["top_total_utility"] == rows[0]["total_utility"]
    assert client.get(f"/api/evaluations/{first.json()['id']}").json() == first.json()


def test_historical_evaluation_survives_model_action_edits_and_delete(client):
    who = person(client)
    encoded = new_action(client, title="Original", goal_progress=0.6, mental_effort=0.2)
    historical = evaluate_actions(client, who["id"], [encoded["id"]]).json()
    model_path = f"/api/persons/{who['id']}/model"
    changed_model = client.get(model_path).json()["model"]
    changed_model["features"]["goal_progress"]["positive_sensitivity"] = 20
    client.put(model_path, json=changed_model)
    client.put(f"/api/actions/{encoded['id']}", json=action("Replacement", goal_progress=-0.9))
    current = evaluate_actions(client, who["id"], [encoded["id"]]).json()
    assert current["model_version"] == 2
    assert current["results"][0]["total_utility"] != historical["results"][0]["total_utility"]
    client.delete(f"/api/actions/{encoded['id']}")
    assert client.get(f"/api/evaluations/{historical['id']}").json() == historical
    reproduced = client.post(f"/api/evaluations/{historical['id']}/reproduce").json()
    assert reproduced["matches"] is True
    assert reproduced["results"] == historical["results"]


def test_ranking_uses_total_even_when_hourly_utility_has_opposite_order(client):
    who = person(client)
    long_action = client.post("/api/actions", json=action("Long action", competence_mastery=0.5) |
                              {"duration_minutes": 120}).json()
    short_action = new_action(client, title="Short action", competence_mastery=0.8)
    response = evaluate_actions(client, who["id"], [short_action["id"], long_action["id"]],
                                horizon_hours=0)
    assert response.status_code == 201, response.text
    first, second = response.json()["results"]
    assert first["action_id"] == long_action["id"]
    assert first["total_utility"] == 1.0
    assert second["total_utility"] == 0.8
    assert first["utility_per_action_hour"] < second["utility_per_action_hour"]


def test_reproduction_refuses_changed_engine_version_and_retains_saved_trace(client, app):
    who = person(client)
    encoded = new_action(client)
    historical = evaluate_actions(client, who["id"], [encoded["id"]]).json()
    with app.state.database.sessions() as session, session.begin():
        session.get(Evaluation, historical["id"]).engine_version = "future"
    assert client.post(f"/api/evaluations/{historical['id']}/reproduce").status_code == 409
    assert client.get(f"/api/evaluations/{historical['id']}").json()["results"] == historical["results"]


def test_failed_evaluation_is_atomic_and_rejects_duplicate_ids(client, app):
    who = person(client)
    encoded = new_action(client)
    missing = evaluate_actions(client, who["id"], [encoded["id"], "missing"])
    assert missing.status_code == 404
    assert evaluate_actions(client, who["id"], [encoded["id"], encoded["id"]]).status_code == 422
    assert evaluate_actions(client, who["id"], []).status_code == 422
    assert evaluate_actions(client, "missing", [encoded["id"]]).status_code == 404
    with app.state.database.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Evaluation)) == 0
        assert session.scalar(select(func.count()).select_from(EvaluationResult)) == 0


@pytest.mark.parametrize("key,value", [("goal_progress", 1.1), ("social_exposure", -0.1), ("mental_effort", 1.01)])
def test_action_domain_validation(client, key, value):
    assert client.post("/api/actions", json=action(**{key: value})).status_code == 422


def test_validation_missing_unknown_features_negative_duration_and_nonfinite(client):
    incomplete = action()
    del incomplete["features"]["goal_progress"]
    assert client.post("/api/actions", json=incomplete).status_code == 422
    assert client.post("/api/actions", json=action(invented_trait=0)).status_code == 422
    assert client.post("/api/actions", json=action() | {"duration_minutes": -1}).status_code == 422
    for invalid in (math.nan, math.inf, -math.inf):
        raw = json.dumps(action(goal_progress=invalid))
        response = client.post("/api/actions", content=raw, headers={"Content-Type": "application/json"})
        assert response.status_code == 422, response.text


def test_invalid_models_states_horizons_and_names(client):
    who = person(client)
    model = default_model().model_dump(mode="json")
    model["aftereffects"]["fatigue"]["half_life_hours"] = 0
    assert client.put(f"/api/persons/{who['id']}/model", json=model).status_code == 422
    assert client.post("/api/persons", json={"name": "  "}).status_code == 422
    assert client.put("/api/daily-state", json={"person_id": who["id"], "state": state() | {"acute_stress": 2}}).status_code == 422
    assert client.get("/api/daily-state", params={"person_id": who["id"], "date": "not a date"}).status_code == 422
    encoded = new_action(client)
    assert evaluate_actions(client, who["id"], [encoded["id"]], horizon_hours=-1).status_code == 422


def test_large_valid_parameters_overflow_is_422_and_atomic(client):
    who = person(client)
    model = default_model().model_dump(mode="json")
    model["features"]["goal_progress"]["positive_sensitivity"] = 1e308
    model["features"]["competence_mastery"]["positive_sensitivity"] = 1e308
    assert client.put(f"/api/persons/{who['id']}/model", json=model).status_code == 200
    encoded = new_action(client, goal_progress=1, competence_mastery=1)
    response = evaluate_actions(client, who["id"], [encoded["id"]])
    assert response.status_code == 422, response.text
    assert client.get("/api/evaluations").json() == []


def test_preview_uses_backend_and_loopback_cors(client):
    response = client.post("/api/model-preview", json={"model": default_model().model_dump(mode="json"), "state": state(), "horizon_hours": 24})
    assert response.status_code == 200, response.text
    assert set(response.json()["features"]) == {feature["key"] for feature in ONTOLOGY}
    assert len(response.json()["aftereffects"]) == 8
    allowed = client.options("/api/actions", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    blocked = client.options("/api/actions", headers={"Origin": "https://example.com", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in blocked.headers


def test_optional_demo_seed_is_labelled_idempotent(tmp_path):
    url = "sqlite:///" + (tmp_path / "demo.db").as_posix()
    assert seed(url) == {"created_demo_person": True, "created_actions": 4}
    assert seed(url) == {"created_demo_person": False, "created_actions": 0}


def test_sqlite_history_survives_application_restart(tmp_path):
    url = "sqlite:///" + (tmp_path / "restart.db").as_posix()
    with TestClient(create_app(url)) as initial:
        who = person(initial)
        encoded = new_action(initial, goal_progress=0.5)
        historical = evaluate_actions(initial, who["id"], [encoded["id"]]).json()
    with TestClient(create_app(url)) as restarted:
        assert restarted.get(f"/api/evaluations/{historical['id']}").json() == historical
        assert restarted.post(f"/api/evaluations/{historical['id']}/reproduce").json()["matches"] is True


def test_default_database_location_is_independent_of_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("VALENCE_DATABASE_URL", raising=False)
    expected = default_database_url()
    monkeypatch.chdir(tmp_path)
    assert default_database_url() == expected
    assert expected.endswith("/backend/data/valence.db")
