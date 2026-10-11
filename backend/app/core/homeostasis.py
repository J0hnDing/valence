"""Bounded, deterministic need values and effort adjustments; no state mutation."""
import math

from app.core.ontology import FEATURE_BY_KEY
from app.schemas.models import NEED_KEYS


def clip(value, lower=0.0, upper=1.0):
    return min(upper, max(lower, value))


def energy_modifier(energy, alpha):
    return 1.0 if energy is None else clip(1 + alpha * (.7 - energy), .5, 2.0)


def need_pressure(satisfaction, lower, upper):
    deprivation = max(0.0, (lower - satisfaction) / lower)
    overload = max(0.0, (satisfaction - upper) / (1 - upper))
    return deprivation ** 2 - overload ** 2


def evaluate_needs(model, state, experienced_features, graph):
    normalized, normalized_ids = {}, {}
    for key in ("physical_effort", "mental_effort", "learning_gain", "social_exposure",
                "relatedness_intimacy", "goal_progress"):
        x = experienced_features[key]
        definition = FEATURE_BY_KEY[key]
        scale = definition["maximum"] if x >= 0 else -definition["minimum"]
        normalized[key] = x / scale
        source = f"experienced:{key}" if definition["temporal_basis"] == "rate" else f"feature:{key}"
        normalized_ids[key] = graph.add(f"normalized:{key}", f"Normalized {definition['display_name']}", "signal",
                                       normalized[key], "Normalized feature intensity after zero-exposure filtering.",
                                       {"experienced_feature": x}, {"range_scale": scale}, "experienced_feature / range_scale", [source])
    w = model.homeostasis.mental_effort_weight
    weight_id = graph.add("need_mapping:mental_effort_weight", "Mental stimulation effort weight", "parameter", w,
                          "Learning weight is the complement of effort weight; sum is one.")
    mappings = {
        "physical_activity": (normalized["physical_effort"], "physical_effort", [normalized_ids["physical_effort"]]),
        "mental_stimulation": (w * normalized["mental_effort"] + (1 - w) * normalized["learning_gain"],
                               "w * mental_effort + (1 - w) * learning_gain",
                               [normalized_ids["mental_effort"], normalized_ids["learning_gain"], weight_id]),
        "social_interaction": (normalized["social_exposure"], "social_exposure", [normalized_ids["social_exposure"]]),
        "close_connection": (normalized["relatedness_intimacy"], "relatedness_intimacy", [normalized_ids["relatedness_intimacy"]]),
        "goal_progression": (normalized["goal_progress"], "goal_progress", [normalized_ids["goal_progress"]]),
    }
    traces, contribution_ids = [], []
    for key in NEED_KEYS:
        params = model.homeostasis.needs[key]
        parameters = params.model_dump()
        feature_value, feature_formula, sources = mappings[key]
        feature_id = graph.add(f"need:{key}:feature_value", f"{key}: action feature value", "need_feature", feature_value,
                               "Caller-encoded action features used for utility scoring once per action.",
                               normalized, {"mental_effort_weight": w} if key == "mental_stimulation" else {}, feature_formula, sources)
        parameter_ids = {name: graph.add(f"need:{key}:parameter:{name}", f"{key}: {name}", "parameter", value,
                                        "Personalized need-scoring parameter, independent of intrinsic preferences.")
                         for name, value in parameters.items()}
        current = state.need_satisfaction.get(key)
        current_id = graph.add(f"state:need:{key}", f"{key}: current satisfaction", "state", current,
                               "Caller-provided current satisfaction; missing satisfaction disables this need.")
        deprivation = overload = None
        pressure = 0.0
        pressure_sources = [current_id, parameter_ids["lower"], parameter_ids["upper"]]
        if current is not None:
            deprivation = max(0.0, (params.lower - current) / params.lower)
            overload = max(0.0, (current - params.upper) / (1 - params.upper))
            d_id = graph.add(f"need:{key}:deprivation", f"{key}: current deprivation", "need_value", deprivation,
                             "Normalized deprivation in the supplied current state.", {"current": current}, {"lower": params.lower},
                             "max(0, (lower - current) / lower)", [current_id, parameter_ids["lower"]])
            e_id = graph.add(f"need:{key}:overload", f"{key}: current overload", "need_value", overload,
                             "Normalized overload in the supplied current state.", {"current": current}, {"upper": params.upper},
                             "max(0, (current - upper) / (1 - upper))", [current_id, parameter_ids["upper"]])
            pressure = need_pressure(current, params.lower, params.upper)
            pressure_sources = [d_id, e_id]
        pressure_id = graph.add(f"need:{key}:pressure", f"{key}: current need pressure", "need_pressure", pressure,
                                "Positive under deprivation, negative under overload, zero within the optimum or when unknown.",
                                {"deprivation": deprivation, "overload": overload},
                                formula="deprivation^2 - overload^2" if current is not None else "0 (current satisfaction unavailable)",
                                sources=pressure_sources)
        utility = params.sensitivity * pressure * feature_value
        formula = "sensitivity * pressure * feature_value"
        contribution_ids.append(graph.add(f"need:{key}:utility", f"{key}: need utility", "need_utility", utility,
                                          "Current need pressure adjusts action utility once; no state change is estimated.",
                                          {"pressure": pressure, "feature_value": feature_value}, {"sensitivity": params.sensitivity}, formula,
                                          [pressure_id, feature_id, parameter_ids["sensitivity"]]))
        traces.append({"need_key": key, "available": current is not None, "current_satisfaction": current,
                       "feature_value": feature_value, "parameters": parameters, "deprivation": deprivation,
                       "overload": overload, "pressure": pressure, "utility_contribution": utility, "formula": formula})
    total = math.fsum(trace["utility_contribution"] for trace in traces)
    graph.add("needs_utility", "Needs utility", "aggregation", total, "Sum of independent bounded need contributions.",
              {t["need_key"]: t["utility_contribution"] for t in traces}, formula="sum(need_utility_i)", sources=contribution_ids)
    return total, traces


def evaluate_energy(model, state, feature_traces, graph):
    traces, sources = [], []
    for key, state_key, parameter_key in (
        ("mental_effort", "mental_energy", "low_mental_energy_cognitive_multiplier"),
        ("physical_effort", "physical_energy", "low_physical_energy_physical_multiplier"),
    ):
        energy = getattr(state, state_key)
        alpha = getattr(model.transient, parameter_key)
        modifier = energy_modifier(energy, alpha)
        base = next(t["utility_contribution"] for t in feature_traces if t["feature_key"] == key)
        adjusted = base * modifier
        utility = base * (modifier - 1)
        factor_id = graph.add(f"modifier:{key}", f"{key}: energy factor", "modifier", modifier,
                              "Bounded positive effort-cost modifier; unavailable energy gives one.", {"energy": energy}, {"alpha": alpha},
                              "1 if energy is unavailable else clip(1 + alpha * (0.7 - energy), 0.5, 2)",
                              [f"state:{state_key}", f"global:{parameter_key}"])
        adjusted_id = graph.add(f"energy:{key}:adjusted", f"{key}: adjusted cost", "energy_cost", adjusted,
                                "Actual effort contribution adjusted by energy without reversing polarity.",
                                {"base_contribution": base, "modifier": modifier}, formula="base_contribution * modifier",
                                sources=[f"contribution:{key}", factor_id])
        formula = "base_contribution * (modifier - 1)"
        sources.append(graph.add(f"energy:{key}:utility", f"{key}: energy adjustment", "energy_utility", utility,
                                 "Difference from base effort cost; avoids counting the cost twice.",
                                 {"base_contribution": base, "adjusted_contribution": adjusted, "modifier": modifier}, formula=formula,
                                 sources=[f"contribution:{key}", factor_id, adjusted_id]))
        traces.append({"feature_key": key, "energy": energy, "alpha": alpha, "modifier": modifier,
                       "base_contribution": base, "adjusted_contribution": adjusted, "utility_contribution": utility, "formula": formula})
    total = math.fsum(t["utility_contribution"] for t in traces)
    graph.add("energy_utility", "Energy adjustment", "aggregation", total, "Sum of physical and mental effort cost differences.",
              {t["feature_key"]: t["utility_contribution"] for t in traces}, formula="sum(energy_adjustment_i)", sources=sources)
    return total, traces
