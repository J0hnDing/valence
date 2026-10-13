from fastapi.testclient import TestClient

from app.core.ontology import FEATURE_KEYS
from app.main import create_app
from app.seed import seed_standard_actions
from app.standard_actions import standard_actions


def test_starter_library_is_editable_and_evaluable(tmp_path):
    url = "sqlite:///" + (tmp_path / "starter.db").as_posix()
    assert seed_standard_actions(url) == {"created_actions": 12}
    with TestClient(create_app(url)) as client:
        actions = client.get("/api/actions").json()
        assert len(actions) == 12
        assert {"Eat a meal", "Sleep", "Play League of Legends", "Study",
                "Go for a walk", "Watch a movie", "Build a project"} <= {a["title"] for a in actions}
        assert client.get("/api/persons").json() == []
        for action in actions:
            assert set(action["features"]) == set(FEATURE_KEYS)
            assert set(action["feature_notes"]) == set(FEATURE_KEYS)
            assert action["net_money_cost"] == 0
        person = client.post("/api/persons", json={"name": "Starter test"}).json()
        result = client.post("/api/evaluations", json={
            "person_id": person["id"], "action_ids": [a["id"] for a in actions],
            "state": {"mental_energy": .7, "physical_energy": .7, "acute_stress": 0,
                      "date": "2026-10-12", "need_satisfaction": {}},
            "horizon_hours": 168,
        })
        assert result.status_code == 201, result.text
        historical = result.json()
        original = actions[0]
        replacement = {key: original[key] for key in (
            "title", "duration_minutes", "net_money_cost", "features", "feature_notes",
            "feature_duration_minutes")}
        replacement["duration_minutes"] = 15
        replacement["net_money_cost"] = 9
        assert client.put(f"/api/actions/{original['id']}", json=replacement).status_code == 200
        assert seed_standard_actions(url) == {"created_actions": 0}
        edited = client.get(f"/api/actions/{original['id']}").json()
        assert edited["duration_minutes"] == 15 and edited["net_money_cost"] == 9
        assert len(client.get("/api/actions").json()) == 12
        assert client.get("/api/persons").json() == [person]
        assert client.get(f"/api/evaluations/{historical['id']}").json() == historical
        assert client.post(f"/api/evaluations/{historical['id']}/reproduce").json()["matches"] is True


def test_seed_preserves_unrelated_actions_and_does_not_run_at_startup(tmp_path):
    url = "sqlite:///" + (tmp_path / "existing.db").as_posix()
    with TestClient(create_app(url)) as client:
        assert client.get("/api/actions").json() == []
        custom = next(standard_actions()).model_dump(mode="json")
        custom["title"] = "My custom action"
        created = client.post("/api/actions", json=custom).json()
        assert seed_standard_actions(url) == {"created_actions": 12}
        assert client.get(f"/api/actions/{created['id']}").json() == created
        assert seed_standard_actions(url) == {"created_actions": 0}
        assert len(client.get("/api/actions").json()) == 13
