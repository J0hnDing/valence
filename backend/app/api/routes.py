"""HTTP transport and snapshot persistence; all mathematics live in core."""

from datetime import date as Date
import math
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import ENGINE_VERSION
from app.core.compatibility import normalize_action, normalize_model
from app.core.initialization import initialize_from_quiz, quiz_schema, validate_answers
from app.core.person_model_export import export_person_model
from app.core.utility import evaluate, model_preview
from app.db.models import Action, DailyState, Evaluation, EvaluationResult, Person, PersonModelVersion, timestamp
from app.schemas import ActionInput, PersonModel, TransientState, default_model

router = APIRouter(prefix="/api")


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class PersonInput(StrictInput):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Name must contain visible text")
        return value


class QuizInput(StrictInput):
    version: Literal["5"]
    answers: dict[str, int | None]

    @field_validator("answers", mode="before")
    @classmethod
    def valid_answers(cls, value):
        if not isinstance(value, dict):
            raise ValueError("answers must be a question-ID to number/null object")
        return validate_answers(value)


class DefaultInitialization(StrictInput):
    method: Literal["default"]


class CopyInitialization(StrictInput):
    method: Literal["copy"]
    person_id: str
    model_version_id: str


class QuizInitialization(QuizInput):
    method: Literal["quiz"]


class PersonCreateInput(PersonInput):
    initialization: Annotated[DefaultInitialization | CopyInitialization | QuizInitialization,
                              Field(discriminator="method")] = DefaultInitialization(method="default")


class StateInput(StrictInput):
    person_id: str
    state: TransientState


class EvaluationInput(StrictInput):
    person_id: str
    model_version_id: str | None = None
    action_ids: list[str] = Field(min_length=1, max_length=1000)
    state: TransientState
    horizon_hours: float = Field(default=168, ge=0)

    @field_validator("action_ids")
    @classmethod
    def unique_actions(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("Action IDs must be unique")
        return values


class PreviewInput(StrictInput):
    model: PersonModel
    state: TransientState
    horizon_hours: float = Field(default=168, ge=0)


def read_session(request: Request):
    with request.app.state.database.sessions() as session:
        yield session


def write_session(request: Request):
    with request.app.state.database.sessions() as session:
        with session.begin():
            # Serialize writers before reading the current model version. This also
            # makes evaluation snapshot capture atomic with concurrent action edits.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            yield session


ReadSession = Annotated[Session, Depends(read_session)]
# Commit before HTTP success is sent, so commit failures cannot follow a 201.
WriteSession = Annotated[Session, Depends(write_session, scope="function")]


def require(session, cls, identifier):
    item = session.get(cls, identifier)
    if item is None or (cls is Person and item.deleted_at is not None):
        raise HTTPException(404, f"{cls.__name__} not found")
    return item


def latest_model(session, person_id):
    require(session, Person, person_id)
    return session.scalars(
        select(PersonModelVersion).where(PersonModelVersion.person_id == person_id)
        .order_by(PersonModelVersion.version.desc()).limit(1)
    ).one()


def require_model_version(session, person_id, version_id):
    version = require(session, PersonModelVersion, version_id)
    if version.person_id != person_id:
        raise HTTPException(404, "PersonModelVersion not found")
    return version


def person_payload(person):
    return {key: getattr(person, key) for key in ("id", "name", "description", "created_at", "updated_at")}


def model_payload(version):
    payload = {key: getattr(version, key) for key in ("id", "person_id", "version", "created_at")}
    payload["model"], payload["converted_from_legacy"] = normalize_model(version.model)
    return payload


def action_snapshot(action):
    snapshot = {key: getattr(action, key) for key in ("title", "duration_minutes", "net_money_cost", "features", "feature_notes", "feature_duration_minutes")}
    return normalize_action(snapshot)[0]


def action_payload(action):
    snapshot = {key: getattr(action, key) for key in ("title", "duration_minutes", "net_money_cost", "features", "feature_notes", "feature_duration_minutes")}
    normalized, converted = normalize_action(snapshot)
    return {"id": action.id, **normalized, "created_at": action.created_at,
            "updated_at": action.updated_at, "converted_from_legacy": converted}


def assert_finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Computed values exceed finite double-precision range")
    if isinstance(value, dict):
        for item in value.values():
            assert_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            assert_finite(item)


def compute(function, *args):
    try:
        result = function(*args)
        assert_finite(result)
        return result
    except (ValueError, OverflowError, FloatingPointError) as error:
        raise HTTPException(422, f"Unable to calculate finite utility: {error}") from error


def stored_results(session, evaluation_id):
    return session.scalars(select(EvaluationResult).where(
        EvaluationResult.evaluation_id == evaluation_id
    ).order_by(EvaluationResult.rank)).all()


def result_payload(result):
    return {"action_id": result.action_id, "action_snapshot": result.action_snapshot,
            "rank": result.rank, **result.result}


def evaluation_payload(session, evaluation):
    return {key: getattr(evaluation, key) for key in (
        "id", "person_id", "person_name", "model_version_id", "model_version", "model_snapshot",
        "state", "horizon_hours", "created_at", "engine_version"
    )} | {"results": [result_payload(result) for result in stored_results(session, evaluation.id)]}


@router.get("/health")
def health():
    return {"status": "ok", "engine_version": ENGINE_VERSION}


@router.get("/ontology")
def ontology():
    from app.core.ontology import ONTOLOGY
    return {"features": ONTOLOGY}


@router.get("/persons")
def list_persons(session: ReadSession):
    return [person_payload(person) for person in session.scalars(
        select(Person).where(Person.deleted_at.is_(None)).order_by(Person.created_at, Person.id)
    )]


@router.get("/person-initialization-quiz")
def get_initialization_quiz():
    return quiz_schema()


@router.post("/person-initialization-quiz/preview")
def preview_initialization_quiz(body: QuizInput):
    return initialize_from_quiz(body.answers)


@router.post("/persons", status_code=201)
def create_person(body: PersonCreateInput, session: WriteSession):
    initialization = body.initialization
    if initialization.method == "copy":
        require(session, Person, initialization.person_id)
        source = require_model_version(session, initialization.person_id, initialization.model_version_id)
        model = PersonModel.model_validate(normalize_model(source.model)[0]).model_dump(mode="json")
    elif initialization.method == "quiz":
        model = initialize_from_quiz(initialization.answers)["model"]
    else:
        model = default_model().model_dump(mode="json")
    person = Person(**body.model_dump(exclude={"initialization"}))
    session.add(person)
    session.flush()
    session.add(PersonModelVersion(person_id=person.id, version=1, model=model))
    session.flush()
    return person_payload(person)


@router.get("/persons/{person_id}")
def get_person(person_id: str, session: ReadSession):
    return person_payload(require(session, Person, person_id))


@router.put("/persons/{person_id}")
def put_person(person_id: str, body: PersonInput, session: WriteSession):
    person = require(session, Person, person_id)
    for key, value in body.model_dump().items():
        setattr(person, key, value)
    person.updated_at = timestamp()
    session.flush()
    return person_payload(person)


@router.delete("/persons/{person_id}", status_code=204)
def delete_person(person_id: str, session: WriteSession):
    person = require(session, Person, person_id)
    person.deleted_at = timestamp()
    session.flush()
    return Response(status_code=204)


@router.get("/persons/{person_id}/model-versions")
def list_model_versions(person_id: str, session: ReadSession):
    require(session, Person, person_id)
    versions = session.scalars(
        select(PersonModelVersion).where(PersonModelVersion.person_id == person_id)
        .order_by(PersonModelVersion.version.desc())
    )
    return [model_payload(version) for version in versions]


@router.get("/persons/{person_id}/model-versions/{version_id}")
def get_model_version(person_id: str, version_id: str, session: ReadSession):
    require(session, Person, person_id)
    return model_payload(require_model_version(session, person_id, version_id))


@router.get("/persons/{person_id}/model")
def get_model(person_id: str, session: ReadSession):
    return model_payload(latest_model(session, person_id))


@router.get("/persons/{person_id}/model-versions/{version_id}/export")
def export_model_version(person_id: str, version_id: str, session: ReadSession):
    person = require(session, Person, person_id)
    version = require_model_version(session, person_id, version_id)
    try:
        content = export_person_model(person, version)
    except (ValueError, OverflowError) as error:
        raise HTTPException(422, "This saved model is incompatible with exact export. "
                            "Review its current parameters and save a new version before exporting. "
                            f"Details: {error}") from error
    filename = f"person-{person.id}-v{version.version}-{version.id}.valence.json"
    return Response(content=content, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.put("/persons/{person_id}/model")
def put_model(person_id: str, body: PersonModel, session: WriteSession):
    current = latest_model(session, person_id)
    version = PersonModelVersion(person_id=person_id, version=current.version + 1, model=body.model_dump(mode="json"))
    session.add(version)
    require(session, Person, person_id).updated_at = timestamp()
    session.flush()
    return model_payload(version)


@router.get("/daily-state")
def get_daily_state(session: ReadSession, person_id: str, date: Annotated[Date, Query()]):
    require(session, Person, person_id)
    row = session.scalars(select(DailyState).where(DailyState.person_id == person_id, DailyState.date == date.isoformat())).one_or_none()
    return row.state if row else TransientState(date=date).model_dump(mode="json")


@router.put("/daily-state")
def put_daily_state(body: StateInput, session: WriteSession):
    require(session, Person, body.person_id)
    state = body.state.model_dump(mode="json")
    row = session.scalars(select(DailyState).where(DailyState.person_id == body.person_id, DailyState.date == state["date"])).one_or_none()
    if row:
        row.state = state
    else:
        session.add(DailyState(person_id=body.person_id, date=state["date"], state=state))
    session.flush()
    return state


@router.get("/actions")
def list_actions(session: ReadSession):
    return [action_payload(action) for action in session.scalars(select(Action).order_by(Action.created_at, Action.id))]


@router.post("/actions", status_code=201)
def create_action(body: ActionInput, session: WriteSession):
    action = Action(**body.model_dump(mode="json"))
    session.add(action)
    session.flush()
    return action_payload(action)


@router.get("/actions/{action_id}")
def get_action(action_id: str, session: ReadSession):
    return action_payload(require(session, Action, action_id))


@router.put("/actions/{action_id}")
def put_action(action_id: str, body: ActionInput, session: WriteSession):
    action = require(session, Action, action_id)
    for key, value in body.model_dump(mode="json").items():
        setattr(action, key, value)
    action.updated_at = timestamp()
    session.flush()
    return action_payload(action)


@router.delete("/actions/{action_id}", status_code=204)
def delete_action(action_id: str, session: WriteSession):
    session.delete(require(session, Action, action_id))
    session.flush()
    return Response(status_code=204)


@router.post("/model-preview")
def preview(body: PreviewInput):
    return compute(model_preview, body.model, body.state, body.horizon_hours)


@router.post("/evaluations", status_code=201)
def create_evaluation(body: EvaluationInput, session: WriteSession):
    person = require(session, Person, body.person_id)
    version = (latest_model(session, person.id) if body.model_version_id is None
               else require_model_version(session, person.id, body.model_version_id))
    current_model = normalize_model(version.model)[0]
    model = PersonModel.model_validate(current_model)
    results = []
    for action_id in body.action_ids:
        snapshot = action_snapshot(require(session, Action, action_id))
        result = compute(evaluate, ActionInput.model_validate(snapshot), model, body.state, body.horizon_hours)
        results.append((action_id, snapshot, result))
    results.sort(key=lambda item: (-item[2]["total_utility"], item[0]))
    evaluation = Evaluation(person_id=person.id, person_name=person.name, model_version_id=version.id,
                            model_version=version.version, model_snapshot=model.model_dump(mode="json"),
                            state=body.state.model_dump(mode="json"), horizon_hours=body.horizon_hours)
    session.add(evaluation)
    session.flush()
    for rank, (action_id, snapshot, result) in enumerate(results, start=1):
        session.add(EvaluationResult(evaluation_id=evaluation.id, action_id=action_id,
                                    action_snapshot=snapshot, rank=rank, result=result))
    session.flush()
    return evaluation_payload(session, evaluation)


@router.get("/evaluations")
def list_evaluations(session: ReadSession):
    evaluations = session.scalars(select(Evaluation).order_by(Evaluation.created_at.desc(), Evaluation.id)).all()
    results = session.scalars(select(EvaluationResult).order_by(EvaluationResult.rank)).all()
    by_evaluation = {}
    for result in results:
        by_evaluation.setdefault(result.evaluation_id, []).append(result)
    payload = []
    for evaluation in evaluations:
        rows = by_evaluation.get(evaluation.id, [])
        top = rows[0] if rows else None
        payload.append({key: getattr(evaluation, key) for key in (
            "id", "person_id", "person_name", "model_version", "created_at", "horizon_hours", "engine_version"
        )} | {"action_count": len(rows), "top_action_title": top.action_snapshot["title"] if top else None,
              "top_total_utility": top.result["total_utility"] if top else None})
    return payload


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str, session: ReadSession):
    return evaluation_payload(session, require(session, Evaluation, evaluation_id))


@router.post("/evaluations/{evaluation_id}/reproduce")
def reproduce(evaluation_id: str, session: ReadSession):
    historical = require(session, Evaluation, evaluation_id)
    if historical.engine_version != ENGINE_VERSION:
        raise HTTPException(409, "This evaluation requires a different engine version; its saved trace remains available")
    model = PersonModel.model_validate(historical.model_snapshot)
    state = TransientState.model_validate(historical.state)
    rows = stored_results(session, evaluation_id)
    recomputed = []
    matches = True
    for row in rows:
        result = compute(evaluate, ActionInput.model_validate(row.action_snapshot), model, state, historical.horizon_hours)
        matches = matches and result == row.result
        recomputed.append({"action_id": row.action_id, "action_snapshot": row.action_snapshot,
                           "rank": row.rank, **result})
    return {"evaluation_id": evaluation_id, "matches": matches, "results": recomputed}
