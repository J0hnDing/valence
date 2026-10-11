"""Explicit, idempotent examples: python -m app.seed. Never called on startup."""

from sqlalchemy import select

from app.core.ontology import ONTOLOGY
from app.db import Database
from app.db.models import Action, Person, PersonModelVersion
from app.schemas import ActionInput, default_model

DEMO_NAME = "DEMO — engineering placeholders"


def examples():
    definitions = [
        ("Study ML for 2 hours", 120, {
            "mental_effort": 0.75, "physical_effort": 0.05,
            "stimulation_novelty": 0.3, "learning_gain": 0.9, "autonomy_control": 0.5,
            "competence_mastery": 0.25, "goal_progress": 0.5, "identity_value_alignment": 0.3,
        }),
        ("Play tennis for 90 minutes", 90, {
            "mental_effort": 0.25, "physical_pleasure": 0.2,
            "stimulation_novelty": 0.5, "autonomy_control": 0.5, "competence_mastery": 0.3,
            "social_exposure": 0.4, "relatedness_intimacy": 0.2, "structure_planning": 0.1,
        }),
        ("Attend AI conference for 6 hours", 360, {
            "mental_effort": 0.35, "physical_effort": 0.15,
            "stimulation_novelty": 0.7, "learning_gain": 0.75, "autonomy_control": 0.2,
            "competence_mastery": 0.1, "goal_progress": 0.6, "social_exposure": 0.9,
            "relatedness_intimacy": 0.05, "belonging_acceptance": 0.1, "status_recognition": 0.15,
            "influence_power": 0.05, "identity_value_alignment": 0.3, "outcome_uncertainty": 0.05,
        }),
        ("Work on a personal project for 3 hours", 180, {
            "mental_effort": 0.6, "physical_effort": 0.05,
            "stimulation_novelty": 0.3, "learning_gain": 0.5, "autonomy_control": 0.8,
            "competence_mastery": 0.5, "goal_progress": 0.7, "structure_planning": 0.25,
            "identity_value_alignment": 0.5,
        }),
    ]
    for title, duration, values in definitions:
        features = {entry["key"]: 0.0 for entry in ONTOLOGY}
        features.update(values)
        yield ActionInput(title=title, duration_minutes=duration, net_money_cost=0, features=features,
                          feature_notes={key: "DEMO: manually assigned illustrative encoding; not universal." for key in features})


def seed(database_url: str | None = None):
    database = Database(database_url)
    created_person = False
    created_actions = 0
    try:
        with database.sessions() as session, session.begin():
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            person = session.scalars(select(Person).where(Person.name == DEMO_NAME)).first()
            if person is None:
                person = Person(name=DEMO_NAME, description="DEMO only. Parameters are engineering placeholders; actions are illustrative caller encodings.")
                session.add(person)
                session.flush()
                session.add(PersonModelVersion(person_id=person.id, version=1,
                                               model=default_model().model_dump(mode="json")))
                created_person = True
            for action in examples():
                if session.scalars(select(Action.id).where(Action.title == action.title)).first() is None:
                    session.add(Action(**action.model_dump(mode="json")))
                    created_actions += 1
        return {"created_demo_person": created_person, "created_actions": created_actions}
    finally:
        database.dispose()


if __name__ == "__main__":
    print(seed())
