"""Stored input snapshots are intentionally independent of mutable actions."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app import ENGINE_VERSION


def new_id() -> str:
    return str(uuid4())


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "persons"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=timestamp)
    updated_at: Mapped[str] = mapped_column(String, default=timestamp)
    # Retain the row and version references solely for immutable history.
    deleted_at: Mapped[str | None] = mapped_column(String, nullable=True)


class PersonModelVersion(Base):
    __tablename__ = "person_model_versions"
    __table_args__ = (UniqueConstraint("person_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    model: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, default=timestamp)


class DailyState(Base):
    __tablename__ = "daily_states"
    __table_args__ = (UniqueConstraint("person_id", "date"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    date: Mapped[str] = mapped_column(String(10))
    state: Mapped[dict] = mapped_column(JSON)


class Action(Base):
    __tablename__ = "actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[float] = mapped_column(Float)
    net_money_cost: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    features: Mapped[dict] = mapped_column(JSON)
    feature_notes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feature_duration_minutes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=timestamp)
    updated_at: Mapped[str] = mapped_column(String, default=timestamp)


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    person_name: Mapped[str] = mapped_column(Text)
    model_version_id: Mapped[str] = mapped_column(ForeignKey("person_model_versions.id"))
    model_version: Mapped[int] = mapped_column(Integer)
    model_snapshot: Mapped[dict] = mapped_column(JSON)
    state: Mapped[dict] = mapped_column(JSON)
    horizon_hours: Mapped[float] = mapped_column(Float)
    engine_version: Mapped[str] = mapped_column(String, default=ENGINE_VERSION)
    created_at: Mapped[str] = mapped_column(String, default=timestamp, index=True)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (UniqueConstraint("evaluation_id", "action_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id"), index=True)
    # No FK: deleting or editing an action must preserve historical evaluation.
    action_id: Mapped[str] = mapped_column(String(36))
    action_snapshot: Mapped[dict] = mapped_column(JSON)
    rank: Mapped[int] = mapped_column(Integer)
    result: Mapped[dict] = mapped_column(JSON)
