"""Strict public computational contracts, independent of API and persistence."""
from datetime import date as Date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

from app.core.ontology import FEATURE_BY_KEY, FEATURE_KEYS

NonNegative = Annotated[FiniteFloat, Field(ge=0)]
Positive = Annotated[FiniteFloat, Field(gt=0)]
Unit = Annotated[FiniteFloat, Field(ge=0, le=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class AsymmetricSigned(StrictModel):
    family: Literal["asymmetric_signed"] = "asymmetric_signed"
    positive_sensitivity: NonNegative = 1
    negative_sensitivity: NonNegative = 1
    positive_curvature: Positive = 1
    negative_curvature: Positive = 1


class Cost(StrictModel):
    family: Literal["cost"] = "cost"
    cost_sensitivity: NonNegative = 1
    curvature: Positive = 1


class OrderPreference(StrictModel):
    family: Literal["order_preference"] = "order_preference"
    preference_sensitivity: Annotated[FiniteFloat, Field(ge=-64, le=64)] = 0


class Reward(StrictModel):
    family: Literal["reward"] = "reward"
    reward_sensitivity: NonNegative = 1
    curvature: Positive = 1


class RewardOverload(StrictModel):
    family: Literal["reward_overload"] = "reward_overload"
    reward_sensitivity: NonNegative
    overload_sensitivity: NonNegative


Response = Annotated[AsymmetricSigned | Cost | OrderPreference | Reward | RewardOverload, Field(discriminator="family")]


class TransientParameters(StrictModel):
    low_mental_energy_cognitive_multiplier: Annotated[FiniteFloat, Field(ge=0, le=64)] = 1
    low_physical_energy_physical_multiplier: Annotated[FiniteFloat, Field(ge=0, le=64)] = 1
    stress_overload_multiplier: NonNegative = .25
    stress_negative_multiplier: NonNegative = .25


class AftereffectParameters(StrictModel):
    sensitivity: NonNegative
    half_life_hours: Positive


class ResourceParameters(StrictModel):
    # Shared utility scale; money amounts use one caller-declared currency.
    time_value: NonNegative = 0
    money_value: NonNegative = 0


NEED_KEYS = ("physical_activity", "mental_stimulation", "social_interaction",
             "close_connection", "goal_progression")


class NeedParameters(StrictModel):
    lower: Annotated[FiniteFloat, Field(gt=0, lt=1)] = .6
    upper: Annotated[FiniteFloat, Field(gt=0, lt=1)] = .8
    sensitivity: Annotated[FiniteFloat, Field(ge=0, le=64)] = 1

    @model_validator(mode="after")
    def valid_interval(self):
        if self.lower > self.upper:
            raise ValueError("need lower must not exceed upper")
        return self


class HomeostaticParameters(StrictModel):
    needs: dict[str, NeedParameters] = Field(default_factory=lambda: {key: NeedParameters() for key in NEED_KEYS})
    mental_effort_weight: Unit = .4

    @field_validator("needs")
    @classmethod
    def valid_needs(cls, value):
        return exact_keys(value, NEED_KEYS, "homeostasis.needs")


AFTEREFFECT_DEFAULTS = {
    "accomplishment": (.50, 12), "pride_ego": (.35, 6), "relief": (.40, 4),
    "inspiration": (.30, 8), "guilt": (.45, 12), "regret": (.45, 12),
    "void": (.30, 8), "fatigue": (.40, 4),
}


def exact_keys(value, expected, label):
    missing, extra = set(expected) - set(value), set(value) - set(expected)
    if missing or extra:
        raise ValueError(f"{label} requires exactly the canonical keys; missing={sorted(missing)}, extra={sorted(extra)}")
    return value


class PersonModel(StrictModel):
    features: dict[str, Response]
    transient: TransientParameters
    aftereffects: dict[str, AftereffectParameters]
    resources: ResourceParameters
    homeostasis: HomeostaticParameters = Field(default_factory=HomeostaticParameters)

    @field_validator("features")
    @classmethod
    def valid_features(cls, value):
        exact_keys(value, FEATURE_KEYS, "model.features")
        for key, response in value.items():
            if response.family != FEATURE_BY_KEY[key]["response_family"]:
                raise ValueError(f"{key} must use {FEATURE_BY_KEY[key]['response_family']}")
        return value

    @field_validator("aftereffects")
    @classmethod
    def valid_aftereffects(cls, value):
        return exact_keys(value, AFTEREFFECT_DEFAULTS, "model.aftereffects")


class ActionInput(StrictModel):
    title: Annotated[str, Field(min_length=1, max_length=500)]
    duration_minutes: NonNegative
    net_money_cost: FiniteFloat
    features: dict[str, FiniteFloat]
    feature_notes: dict[str, str] | None = None
    feature_duration_minutes: dict[str, NonNegative] | None = None

    @field_validator("title")
    @classmethod
    def meaningful_title(cls, value):
        if not value.strip():
            raise ValueError("title must not be blank")
        return value.strip()

    @field_validator("features")
    @classmethod
    def valid_features(cls, value):
        exact_keys(value, FEATURE_KEYS, "action.features")
        for key, x in value.items():
            definition = FEATURE_BY_KEY[key]
            if not definition["minimum"] <= x <= definition["maximum"]:
                raise ValueError(f"{key} must be in [{definition['minimum']}, {definition['maximum']}]")
        return value

    @field_validator("feature_notes")
    @classmethod
    def valid_notes(cls, value):
        if value is not None and set(value) - set(FEATURE_KEYS):
            raise ValueError("feature_notes keys must be canonical feature keys")
        return value

    @model_validator(mode="after")
    def valid_exposure_durations(self):
        for key, minutes in (self.feature_duration_minutes or {}).items():
            if key not in FEATURE_BY_KEY or FEATURE_BY_KEY[key]["temporal_basis"] != "rate":
                raise ValueError("feature_duration_minutes keys must be ongoing feature keys")
            if minutes > self.duration_minutes:
                raise ValueError("feature exposure duration cannot exceed action duration")
        return self


class TransientState(StrictModel):
    mental_energy: Unit | None = None
    physical_energy: Unit | None = None
    acute_stress: Unit = 0
    need_satisfaction: dict[str, Unit] = Field(default_factory=dict)
    date: Date = Field(default_factory=Date.today)
    notes: str | None = None

    @field_validator("need_satisfaction")
    @classmethod
    def valid_need_state(cls, value):
        if set(value) - set(NEED_KEYS):
            raise ValueError("need_satisfaction keys must be canonical need keys")
        return value


def default_model() -> PersonModel:
    responses = {}
    for key in FEATURE_KEYS:
        family = FEATURE_BY_KEY[key]["response_family"]
        if family == "asymmetric_signed":
            responses[key] = AsymmetricSigned()
        elif family == "order_preference":
            responses[key] = OrderPreference()
        elif family == "cost":
            responses[key] = Cost()
        elif family == "reward":
            responses[key] = Reward()
        else:
            reward, overload = (.8, .6) if key == "stimulation_novelty" else (.6, .8)
            responses[key] = RewardOverload(reward_sensitivity=reward, overload_sensitivity=overload)
    return PersonModel(features=responses, transient=TransientParameters(), resources=ResourceParameters(),
                       aftereffects={k: AftereffectParameters(sensitivity=s, half_life_hours=h)
                                     for k, (s, h) in AFTEREFFECT_DEFAULTS.items()})
