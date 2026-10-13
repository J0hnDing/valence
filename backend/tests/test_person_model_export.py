from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm.attributes import flag_modified

from app.core.person_model_export import EXPORT_SCHEMA, export_person_model
from app.db.models import PersonModelVersion
from app.schemas import default_model


def create_version(client):
    person = client.post("/api/persons", json={"name": "Ada 🌱"}).json()
    version = client.get(f"/api/persons/{person['id']}/model").json()
    return person, version


def export_path(person, version):
    return f"/api/persons/{person['id']}/model-versions/{version['id']}/export"


def test_exports_selected_saved_version_without_conversion_rounding_or_latest_fallback(client, app):
    person, first = create_version(client)
    raw = deepcopy(first["model"])
    raw["features"]["goal_progress"]["positive_sensitivity"] = 1.2345678901234567
    raw["homeostasis"]["needs"]["mental_stimulation"]["lower"] = 0.6123456789012345
    raw["resources"]["money_value"] = 2  # Keep the stored numeric representation too.
    with app.state.database.sessions.begin() as session:
        session.get(PersonModelVersion, first["id"]).model = raw
    newer = deepcopy(raw)
    newer["features"]["goal_progress"]["positive_sensitivity"] = 10
    second = client.put(f"/api/persons/{person['id']}/model", json=newer).json()

    response = client.get(export_path(person, first))
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/json"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="person-{person["id"]}-v1-{first["id"]}.valence.json"')
    assert "🌱" in response.content.decode("utf-8")
    assert b"1.2345678901234567" in response.content
    assert response.json() == {
        "format": "valence.person-model", "schema_version": 1,
        "model_contract_version": "7",
        "source": {"person_id": person["id"], "person_name": person["name"],
                   "model_version_id": first["id"], "model_version": 1,
                   "model_created_at": first["created_at"]}, "model": raw,
    }
    assert type(response.json()["model"]["resources"]["money_value"]) is int
    assert client.get(export_path(person, second)).json()["model"] == newer
    with app.state.database.sessions() as session:
        assert session.get(PersonModelVersion, first["id"]).model == raw


def test_export_checks_owner_missing_version_and_deleted_person(client):
    person, version = create_version(client)
    other, _ = create_version(client)
    assert client.get(export_path(other, version)).status_code == 404
    assert client.get(export_path(person, {"id": "missing"})).status_code == 404
    assert client.get(export_path({"id": "missing"}, version)).status_code == 404
    client.delete(f"/api/persons/{person['id']}")
    assert client.get(export_path(person, version)).status_code == 404


def test_integral_float_exports_exact_integer_literal_without_changing_its_numeric_value(client, app):
    person, version = create_version(client)
    raw = deepcopy(version["model"])
    raw["resources"]["time_value"] = 1e100
    raw["resources"]["money_value"] = -0.0
    with app.state.database.sessions.begin() as session:
        stored = session.get(PersonModelVersion, version["id"])
        stored.model = raw
        flag_modified(stored, "model")
    response = client.get(export_path(person, version))
    assert response.status_code == 200, response.text
    assert f'"time_value": {int(1e100)}' in response.text
    assert '"money_value": -0.0' in response.text
    assert '1e+100' not in response.text
    assert float(response.json()["model"]["resources"]["time_value"]) == 1e100
    assert response.json()["model"] == raw
    with app.state.database.sessions() as session:
        persisted = session.get(PersonModelVersion, version["id"]).model["resources"]["time_value"]
        assert type(persisted) is float and persisted == 1e100


@pytest.mark.parametrize("invalid", ["legacy", "missing", "extra", "string", "boolean", "infinite", "reversed", "boundary", "family", "integer_precision"])
def test_export_rejects_incompatible_stored_models_with_review_instruction(client, app, invalid):
    person, version = create_version(client)
    raw = deepcopy(version["model"])
    if invalid == "legacy":
        raw.pop("homeostasis")
    elif invalid == "missing":
        raw["transient"].pop("stress_negative_multiplier")
    elif invalid == "extra":
        raw["resources"]["currency"] = "CAD"
    elif invalid == "string":
        raw["resources"]["time_value"] = "0"
    elif invalid == "boolean":
        raw["resources"]["time_value"] = False
    elif invalid == "infinite":
        raw["resources"]["time_value"] = float("inf")
    elif invalid == "integer_precision":
        raw["resources"]["time_value"] = 9007199254740993
    elif invalid == "reversed":
        raw["homeostasis"]["needs"]["physical_activity"]["lower"] = .9
    elif invalid == "boundary":
        raw["homeostasis"]["needs"]["physical_activity"]["upper"] = 1
    elif invalid == "family":
        raw["features"]["mental_effort"] = {"family": "reward", "reward_sensitivity": 1, "curvature": 1}
    with app.state.database.sessions.begin() as session:
        stored = session.get(PersonModelVersion, version["id"])
        stored.model = raw
        flag_modified(stored, "model")
    response = client.get(export_path(person, version))
    assert response.status_code == 422
    assert "save a new version" in response.json()["detail"]
    assert "content-disposition" not in response.headers


def paths(value, prefix=()):
    for key, child in value.items():
        path = (*prefix, key)
        yield path
        if isinstance(child, dict):
            yield from paths(child, path)


def test_every_model_field_is_required_including_fields_with_computational_defaults():
    raw = default_model().model_dump(mode="json")
    person = SimpleNamespace(id="person", name="Ada")
    version = SimpleNamespace(id="version", version=1, created_at="2026-10-12T12:00:00Z", model=raw)
    for path in paths(raw):
        incomplete = deepcopy(raw)
        node = incomplete
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]
        version.model = incomplete
        with pytest.raises(ValueError, match="requires exactly"):
            export_person_model(person, version)


def test_published_schema_is_exact_and_contains_no_defaults():
    schema_path = Path(__file__).resolve().parents[2] / "docs/person-model-export.schema.json"
    assert json.loads(schema_path.read_text(encoding="utf-8")) == EXPORT_SCHEMA
    assert '"default":' not in schema_path.read_text(encoding="utf-8")
