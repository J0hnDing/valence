"""Reusable deterministic utility engine and complete numeric computation graph."""
import math
from typing import TYPE_CHECKING

from app.core.aftereffects import (SIGNS, TRIGGER_SPECS, decay, decay_integral_factor,
                                  finite, integrate_decay, neg, pos, triggers)
from app.core.ontology import FEATURE_BY_KEY, FEATURE_KEYS
from app.core.homeostasis import energy_modifier, rest_energy_modifier, evaluate_energy, evaluate_needs

if TYPE_CHECKING:
    from app.schemas.models import ActionInput, PersonModel, TransientState

FORMULAS = {
    "asymmetric_signed": "x >= 0: positive_sensitivity * x^positive_curvature; x < 0: -negative_sensitivity * (-x)^negative_curvature",
    "cost": "-cost_sensitivity * x^curvature",
    "order_preference": "preference_sensitivity * x",
    "reward": "reward_sensitivity * x^curvature",
    "reward_overload": "reward_sensitivity * x - overload_sensitivity * x^2",
}
INTEGRAL_FORMULA = "A * half_life_hours / ln(2) * (1 - 2^(-horizon_hours / half_life_hours))"


def validate_horizon(value):
    try:
        horizon = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("horizon_hours must be finite and nonnegative") from None
    if not math.isfinite(horizon) or horizon < 0:
        raise ValueError("horizon_hours must be finite and nonnegative")
    return horizon


def validated_inputs(model, state, action=None):
    # Validate a fresh representation: nested dictionaries can be mutated after
    # Pydantic construction without triggering validate_assignment.
    from app.schemas.models import ActionInput, PersonModel, TransientState
    def validate(schema, value):
        return schema.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)
    model = validate(PersonModel, model)
    state = validate(TransientState, state)
    return model, state, validate(ActionInput, action) if action is not None else None


def effective_parameters(key, parameters, model, state, include_energy=True):
    effective = parameters.model_dump(exclude={"family"})
    if key == "mental_effort" and parameters.family == "cost" and include_energy:
        effective["cost_sensitivity"] *= energy_modifier(state.mental_energy, model.transient.low_mental_energy_cognitive_multiplier)
    elif key == "physical_effort" and parameters.family == "cost" and include_energy:
        effective["cost_sensitivity"] *= energy_modifier(state.physical_energy, model.transient.low_physical_energy_physical_multiplier)
    elif key == "mental_rest" and parameters.family == "reward" and include_energy:
        effective["reward_sensitivity"] *= rest_energy_modifier(state.mental_energy, model.transient.low_mental_energy_cognitive_multiplier)
    elif parameters.family == "reward_overload":
        effective["overload_sensitivity"] *= 1 + model.transient.stress_overload_multiplier * state.acute_stress
    elif parameters.family == "asymmetric_signed":
        effective["negative_sensitivity"] *= 1 + model.transient.stress_negative_multiplier * state.acute_stress
    for value in effective.values():
        finite(value, "Effective response parameter")
    return effective


def response(family, x, parameters):
    if family == "asymmetric_signed":
        result = (parameters["positive_sensitivity"] * x ** parameters["positive_curvature"] if x >= 0
                  else -parameters["negative_sensitivity"] * (-x) ** parameters["negative_curvature"])
    elif family == "cost":
        result = -parameters["cost_sensitivity"] * x ** parameters["curvature"]
    elif family == "order_preference":
        result = parameters["preference_sensitivity"] * x
    elif family == "reward":
        result = parameters["reward_sensitivity"] * x ** parameters["curvature"]
    elif family == "reward_overload":
        result = parameters["reward_sensitivity"] * x - parameters["overload_sensitivity"] * x * x
    else:
        raise ValueError("Unknown response family")
    return finite(result, "Feature response")


class Graph:
    def __init__(self):
        self.nodes = []
        self.edges = []

    def add(self, identifier, label, kind, value, definition, inputs=None, parameters=None, formula="value", sources=(), note=None):
        node = {"id": identifier, "label": label, "kind": kind, "value": finite(value, label) if value is not None else None,
                "definition": definition, "inputs": inputs or {}, "parameters": parameters or {}, "formula": formula}
        if note is not None:
            node["note"] = note
        self.nodes.append(node)
        self.edges.extend({"source": source, "target": identifier} for source in sources)
        return identifier

    def dump(self):
        return {"nodes": self.nodes, "edges": self.edges}


def evaluate(action: "ActionInput", model: "PersonModel", state: "TransientState", horizon_hours=168) -> dict:
    model, state, action = validated_inputs(model, state, action)
    horizon = validate_horizon(horizon_hours)
    duration = action.duration_minutes / 60.0
    graph = Graph()
    graph.add("duration_minutes", "Duration (minutes)", "input", action.duration_minutes, "Caller-supplied action duration in minutes.")
    graph.add("duration_hours", "Duration (hours)", "duration", duration, "Action duration in hours.",
              {"duration_minutes": action.duration_minutes}, formula="duration_minutes / 60", sources=["duration_minutes"])
    graph.add("horizon_hours", "Aftereffect horizon (hours)", "input", horizon, "Integration time measured from the end of the action.")
    for name in ("mental_energy", "physical_energy", "acute_stress"):
        graph.add(f"state:{name}", name.replace("_", " "), "state", getattr(state, name), "Transient state input in [0,1].")
    for name, value in model.transient.model_dump().items():
        graph.add(f"global:{name}", name.replace("_", " "), "parameter", value, "Person Model transient response multiplier.")
    feature_traces, response_ids, outcome_ids = [], [], []
    exposures = {}
    for key in FEATURE_KEYS:
        definition = FEATURE_BY_KEY[key]
        x, params = action.features[key], model.features[key]
        effective = effective_parameters(key, params, model, state, include_energy=False)
        raw_id = graph.add(f"feature:{key}", definition["display_name"], "feature_input", x, definition["definition"],
                           note=(action.feature_notes or {}).get(key))
        param_ids = {}
        for name, value in params.model_dump(exclude={"family"}).items():
            param_ids[name] = graph.add(f"parameter:{key}:{name}", f"{definition['display_name']}: {name}", "parameter", value,
                                       "Base Person Model response parameter.")
        modified = None
        if params.family == "reward_overload":
            modified = ("overload_sensitivity", "stress_overload_multiplier", "acute_stress", state.acute_stress, "acute_stress")
        elif params.family == "asymmetric_signed":
            modified = ("negative_sensitivity", "stress_negative_multiplier", "acute_stress", state.acute_stress, "acute_stress")
        if modified:
            parameter_name, multiplier_name, state_name, signal, signal_formula = modified
            multiplier = getattr(model.transient, multiplier_name)
            factor = finite(1 + multiplier * signal, "State modifier")
            factor_id = graph.add(f"modifier:{key}", f"{definition['display_name']}: state factor", "modifier", factor,
                                  "Transient state changes response sensitivity, never the encoded feature.",
                                  {state_name: getattr(state, state_name)}, {multiplier_name: multiplier},
                                  f"1 + {multiplier_name} * ({signal_formula})",
                                  [f"state:{state_name}", f"global:{multiplier_name}"])
            base_value = getattr(params, parameter_name)
            effective_id = graph.add(f"effective:{key}:{parameter_name}", f"Effective {parameter_name}", "effective_parameter",
                                     effective[parameter_name], "Base sensitivity multiplied by transient state factor.",
                                     {"base": base_value, "state_factor": factor}, formula="base * state_factor",
                                     sources=[param_ids[parameter_name], factor_id])
            param_ids[parameter_name] = effective_id
        value = response(params.family, x, effective)
        basis = definition["temporal_basis"]
        exposure_minutes = (action.feature_duration_minutes or {}).get(key, action.duration_minutes) if basis == "rate" else None
        exposure_hours = exposure_minutes / 60 if exposure_minutes is not None else None
        if exposure_hours is not None:
            exposures[key] = exposure_hours
        contribution = finite(value * exposure_hours, "Integrated feature utility") if basis == "rate" else value
        feature_traces.append({"feature_key": key, "raw_value": x, "response_family": params.family,
                               "effective_parameters": effective, "formula": FORMULAS[params.family],
                               "temporal_basis": basis, "response_value": value,
                               "exposure_duration_minutes": exposure_minutes, "exposure_duration_hours": exposure_hours,
                               "utility_rate_contribution": value if basis == "rate" else None,
                               "utility_contribution": contribution})
        response_id = graph.add(f"response:{key}", f"{definition['display_name']} response", "feature_response", value,
                                "Utility rate in units/hour." if basis == "rate" else "One-time outcome utility, counted once per action.",
                                {"x": x}, effective, FORMULAS[params.family], [raw_id, *param_ids.values()],
                                (action.feature_notes or {}).get(key))
        if basis == "rate":
            overridden = key in (action.feature_duration_minutes or {})
            exposure_minutes_id = graph.add(f"exposure_minutes:{key}", f"{definition['display_name']} exposure minutes", "input" if overridden else "duration", exposure_minutes,
                                           "Caller-supplied exposure override." if overridden else "Default exposure equals the action duration.",
                                           formula="value" if overridden else "duration_minutes", sources=[] if overridden else ["duration_minutes"])
            exposure_id = graph.add(f"exposure:{key}", f"{definition['display_name']} exposure", "duration", exposure_hours,
                                    "Actual feature exposure hours; omitted overrides use the action duration.",
                                    {"exposure_minutes": exposure_minutes}, formula="exposure_minutes / 60", sources=[exposure_minutes_id])
            contribution_id = graph.add(f"contribution:{key}", f"{definition['display_name']} integrated utility", "integral", contribution,
                      "Ongoing feature utility integrated over its actual exposure.",
                      {"response": value, "exposure_hours": exposure_hours}, formula="response * exposure_hours",
                      sources=[response_id, exposure_id])
            response_ids.append(contribution_id)
        else:
            outcome_ids.append(response_id)
    try:
        during = finite(math.fsum(trace["utility_contribution"] for trace in feature_traces if trace["temporal_basis"] == "rate"), "During utility")
        during_rate = finite(during / duration, "During rate") if duration > 0 else 0
        one_time = finite(math.fsum(trace["response_value"] for trace in feature_traces if trace["temporal_basis"] == "one_time"), "One-time utility")
    except OverflowError:
        raise ValueError("Feature aggregation exceeds finite double-precision arithmetic") from None
    graph.add("during_rate", "During rate", "aggregation", during_rate, "Average ongoing utility per action hour, accounting for actual exposures; zero at zero duration.",
              {"during_utility": during, "duration_hours": duration}, formula="during_utility / duration_hours if duration_hours > 0 else 0", sources=["during_utility", "duration_hours"])
    graph.add("one_time_utility", "One-time utility", "aggregation", one_time, "Sum of one-time outcome responses; independent of duration.",
              {t["feature_key"]: t["response_value"] for t in feature_traces if t["temporal_basis"] == "one_time"}, formula="sum(one_time_response_i)", sources=outcome_ids)
    graph.add("during_utility", "During utility", "aggregation", during, "Sum of utility integrated over each ongoing feature's actual exposure.",
              {t["feature_key"]: t["utility_contribution"] for t in feature_traces if t["temporal_basis"] == "rate"}, formula="sum(rate_response_i * exposure_hours_i)", sources=response_ids)

    trigger_features = dict(action.features)
    for key, exposure in exposures.items():
        trigger_features[key] = action.features[key] if exposure > 0 else 0
        graph.add(f"experienced:{key}", f"Experienced {FEATURE_BY_KEY[key]['display_name']}", "trigger_signal", trigger_features[key],
                  "Ongoing input contributes to aftereffect triggers only if its exposure is positive.",
                  {"x": action.features[key], "exposure_hours": exposure}, formula="x if exposure_hours > 0 else 0",
                  sources=[f"feature:{key}", f"exposure:{key}"])
    signal_ids = {}
    def signal_node(key, branch):
        source_id = f"experienced:{key}" if key in exposures else f"feature:{key}"
        if branch == "raw":
            return source_id, trigger_features[key]
        value = (pos if branch == "pos" else neg)(trigger_features[key])
        identifier = f"signal:{branch}:{key}"
        if identifier not in signal_ids:
            graph.add(identifier, f"{branch}({key})", "signal", value, "Positive or negative magnitude from the encoded action feature.",
                      {"x": trigger_features[key]}, formula="max(x, 0)" if branch == "pos" else "max(-x, 0)", sources=[source_id])
            signal_ids[identifier] = value
        return identifier, value

    trigger_values = triggers(trigger_features, duration, exposures)
    aftereffect_traces, integral_ids = [], []
    for name, sign in SIGNS.items():
        trigger_id = f"trigger:{name}"
        if name in TRIGGER_SPECS:
            complements, complement_ids, operands = [], [], []
            for index, (weight, key, branch) in enumerate(TRIGGER_SPECS[name]):
                signal_id, signal = signal_node(key, branch)
                weighted = min(1.0, max(0.0, weight * signal))
                operand_id = graph.add(f"operand:{name}:{index}", f"{name}: {weight:g} × {branch}({key})", "trigger_operand", weighted,
                                       "Clamped weighted noisy-or input (deterministic intensity, not a probability).",
                                       {"signal": signal}, {"weight": weight}, "clamp(weight * signal, 0, 1)", [signal_id])
                complement = 1 - weighted
                complement_ids.append(graph.add(f"complement:{name}:{index}", f"{name}: complement {index + 1}", "trigger_operand", complement,
                                                 "Complement of a clamped noisy-or operand.", {"weighted_signal": weighted}, formula="1 - weighted_signal", sources=[operand_id]))
                complements.append(complement)
                operands.append({"feature_key": key, "branch": branch, "weight": weight, "signal": signal, "weighted_clamped": weighted})
            product = math.prod(complements)
            product_id = graph.add(f"product:{name}", f"{name}: complement product", "trigger_product", product, "Product of noisy-or operand complements.",
                                   {str(i): c for i, c in enumerate(complements)}, formula="product(1 - clamp(weight_i * signal_i, 0, 1))", sources=complement_ids)
            trigger_formula = "1 - product(1 - clamp(weight_i * signal_i, 0, 1))"
            graph.add(trigger_id, f"{name} trigger", "trigger", trigger_values[name], "Derived deterministic aftereffect intensity.",
                      {"complement_product": product, "operands": operands}, formula=trigger_formula, sources=[product_id])
        elif name == "void":
            g_id, g = signal_node("goal_progress", "pos")
            c_id, c = signal_node("structure_planning", "raw")
            trigger_formula = "pos(goal_progress) * structure_planning"
            graph.add(trigger_id, "Void trigger", "trigger", trigger_values[name], "Joint positive goal progress and order/structure; sensitivity determines negative post-action utility.",
                      {"pos_goal_progress": g, "structure_planning": c}, formula=trigger_formula, sources=[g_id, c_id])
        else:
            component_ids, components = [], {}
            for key in ("mental_effort", "physical_effort"):
                factor = -math.expm1(-exposures[key] / 2)
                factor_id = graph.add(f"fatigue:duration_factor:{key}", f"Fatigue {key} duration factor", "trigger_operand", factor,
                                      "Saturating actual effort exposure (two-hour time constant).",
                                      {"exposure_hours": exposures[key]}, {"time_constant_hours": 2}, "1 - exp(-exposure_hours / 2)", [f"exposure:{key}"])
                component = .5 * trigger_features[key] * factor
                component_ids.append(graph.add(f"fatigue:component:{key}", f"Fatigue {key} component", "trigger_operand", component,
                                               "Equal-weight effort intensity times its actual exposure factor.",
                                               {"effort": trigger_features[key], "duration_factor": factor}, {"weight": .5},
                                               "weight * effort * duration_factor", [f"experienced:{key}", factor_id]))
                components[key] = component
            trigger_formula = "sum(0.5 * effort_i * (1 - exp(-exposure_hours_i / 2)))"
            graph.add(trigger_id, "Fatigue trigger", "trigger", trigger_values[name], "Demand trigger using actual mental and physical effort exposures.",
                      components, formula=trigger_formula, sources=component_ids)
        params = model.aftereffects[name]
        sensitivity_id = graph.add(f"aftereffect_parameter:{name}:sensitivity", f"{name} sensitivity", "parameter", params.sensitivity, "Person Model aftereffect amplitude sensitivity.")
        half_life_id = graph.add(f"aftereffect_parameter:{name}:half_life_hours", f"{name} half-life", "parameter", params.half_life_hours, "Hours until the aftereffect rate halves.")
        amplitude = finite(sign * params.sensitivity * trigger_values[name], "Initial amplitude")
        amplitude_id = graph.add(f"amplitude:{name}", f"{name} initial amplitude", "amplitude", amplitude, "Signed post-action utility rate at t=0, in utility units/hour.",
                                 {"trigger": trigger_values[name]}, {"sign": sign, "sensitivity": params.sensitivity}, "sign * sensitivity * trigger", [trigger_id, sensitivity_id])
        factor = decay_integral_factor(params.half_life_hours, horizon)
        decay_id = graph.add(f"decay_factor:{name}", f"{name} decay integral factor", "decay", factor, "Integral of a unit-amplitude decay from action end to the selected horizon, in hours.",
                            {"horizon_hours": horizon}, {"half_life_hours": params.half_life_hours}, "half_life_hours / ln(2) * (1 - 2^(-horizon_hours / half_life_hours))", [half_life_id, "horizon_hours"])
        integrated = integrate_decay(amplitude, params.half_life_hours, horizon)
        integral_ids.append(graph.add(f"integral:{name}", f"{name} integrated utility", "integral", integrated, "Signed aftereffect utility integrated from action end to horizon.",
                                      {"initial_amplitude": amplitude, "decay_integral_factor": factor}, formula="initial_amplitude * decay_integral_factor", sources=[amplitude_id, decay_id]))
        aftereffect_traces.append({"name": name, "trigger": trigger_values[name], "sensitivity": params.sensitivity,
                                  "half_life_hours": params.half_life_hours, "sign": sign, "initial_amplitude": amplitude,
                                  "integrated_utility": integrated, "formula": INTEGRAL_FORMULA,
                                  "trigger_formula": trigger_formula, "decay_formula": "A * 2^(-t / half_life_hours)"})
    try:
        aftereffect = finite(math.fsum(t["integrated_utility"] for t in aftereffect_traces), "Aftereffect utility")
    except OverflowError:
        raise ValueError("Aftereffect utility exceeds finite double-precision arithmetic") from None
    graph.add("aftereffect_utility", "Aftereffect utility", "aggregation", aftereffect, "Sum of integrated utility from all eight post-action effects.",
              {t["name"]: t["integrated_utility"] for t in aftereffect_traces}, formula="sum(integrated_aftereffect_utility_i)", sources=integral_ids)
    needs_utility, need_traces = evaluate_needs(model, state, trigger_features, graph)
    energy_utility, energy_traces = evaluate_energy(model, state, feature_traces, graph)
    try:
        base_gross = finite(math.fsum([during, one_time, aftereffect]), "Base gross utility")
        gross = finite(math.fsum([base_gross, needs_utility, energy_utility]), "Gross utility")
    except OverflowError:
        raise ValueError("Gross utility exceeds finite double-precision arithmetic") from None
    graph.add("gross_utility", "Gross utility", "aggregation", gross, "Utility before resource costs.",
              {"during_utility": during, "one_time_utility": one_time, "aftereffect_utility": aftereffect,
               "needs_utility": needs_utility, "energy_utility": energy_utility},
              formula="during_utility + one_time_utility + aftereffect_utility + needs_utility + energy_utility",
              sources=["during_utility", "one_time_utility", "aftereffect_utility", "needs_utility", "energy_utility"])
    for name, value in model.resources.model_dump().items():
        graph.add(f"resource_parameter:{name}", name.replace("_", " "), "parameter", value,
                  "Utility per hour of time." if name == "time_value" else "Utility per currency unit; all money uses one consistent caller-declared currency.")
    graph.add("net_money_cost", "Net money cost", "input", action.net_money_cost,
              "Whole-action spending minus income in currency units; negative values are income.")
    time_cost = finite(model.resources.time_value * duration, "Time cost")
    money_cost = finite(model.resources.money_value * action.net_money_cost, "Money cost")
    resource_cost = finite(time_cost + money_cost, "Resource cost")
    graph.add("time_cost", "Time utility cost", "resource_cost", time_cost, "Time opportunity cost across the action duration.",
              {"duration_hours": duration}, {"time_value": model.resources.time_value}, "time_value * duration_hours",
              ["duration_hours", "resource_parameter:time_value"])
    graph.add("money_cost", "Money utility cost", "resource_cost", money_cost, "Money utility cost counted once; income yields a negative cost.",
              {"net_money_cost": action.net_money_cost}, {"money_value": model.resources.money_value}, "money_value * net_money_cost",
              ["net_money_cost", "resource_parameter:money_value"])
    graph.add("resource_cost", "Resource utility cost", "aggregation", resource_cost, "Sum of time and money utility costs.",
              {"time_cost": time_cost, "money_cost": money_cost}, formula="time_cost + money_cost", sources=["time_cost", "money_cost"])
    base_utility = finite(base_gross - resource_cost, "Base utility")
    graph.add("base_utility", "Base utility", "aggregation", base_utility,
              "Existing intrinsic and aftereffect utility less resources; excludes energy and dynamic needs.",
              {"during_utility": during, "one_time_utility": one_time, "aftereffect_utility": aftereffect, "resource_cost": resource_cost},
              formula="during_utility + one_time_utility + aftereffect_utility - resource_cost",
              sources=["during_utility", "one_time_utility", "aftereffect_utility", "resource_cost"])
    total = finite(math.fsum([base_utility, needs_utility, energy_utility]), "Total utility")
    graph.add("total_utility", "Total utility", "total", total, "Ranking score after subtracting time and money utility costs.",
              {"base_utility": base_utility, "needs_utility": needs_utility, "energy_utility": energy_utility},
              formula="base_utility + needs_utility + energy_utility", sources=["base_utility", "needs_utility", "energy_utility"])
    before_time_cost = finite(gross - money_cost, "Utility excluding time cost")
    graph.add("utility_excluding_time_cost", "Utility excluding time cost", "aggregation", before_time_cost,
              "Gross utility less money cost; excludes time opportunity cost for the hourly diagnostic.",
              {"gross_utility": gross, "money_cost": money_cost}, formula="gross_utility - money_cost", sources=["gross_utility", "money_cost"])
    per_hour = finite(before_time_cost / duration, "Utility per action hour") if duration > 0 else None
    if per_hour is not None:
        graph.add("utility_per_action_hour", "Utility / action hour", "ratio", per_hour, "Diagnostic ratio including money cost and excluding time cost; ranking uses net total utility.",
                  {"utility_excluding_time_cost": before_time_cost, "duration_hours": duration}, formula="utility_excluding_time_cost / duration_hours", sources=["utility_excluding_time_cost", "duration_hours"])
    return {"during_rate": during_rate, "during_utility": during, "one_time_utility": one_time, "aftereffect_utility": aftereffect,
            "gross_utility": gross, "time_cost": time_cost, "money_cost": money_cost, "resource_cost": resource_cost,
            "total_utility": total, "utility_per_action_hour": per_hour,
            "base_utility": base_utility, "needs_utility": needs_utility, "energy_utility": energy_utility,
            "need_traces": need_traces, "energy_traces": energy_traces,
            "feature_traces": feature_traces, "aftereffect_traces": aftereffect_traces, "graph": graph.dump()}


def model_preview(model: "PersonModel", state: "TransientState", horizon=168) -> dict:
    model, state, _ = validated_inputs(model, state)
    horizon = validate_horizon(horizon)
    features, aftereffects = {}, {}
    for key in FEATURE_KEYS:
        minimum = FEATURE_BY_KEY[key]["minimum"]
        params = model.features[key]
        effective = effective_parameters(key, params, model, state)
        points = []
        for index in range(101):
            x = minimum + (1 - minimum) * index / 100
            points.append({"x": x, "y": response(params.family, x, effective)})
        preferred = None
        if params.family == "reward_overload" and effective["overload_sensitivity"] > 0:
            preferred = min(1.0, (effective["reward_sensitivity"] / effective["overload_sensitivity"]) / 2)
        features[key] = {"points": points, "preferred_exposure": preferred,
                         "effective_parameters": effective, "formula": FORMULAS[params.family]}
    for name, sign in SIGNS.items():
        params = model.aftereffects[name]
        aftereffects[name] = {"points": [{"x": horizon * (index / 100), "y": decay(sign * params.sensitivity, params.half_life_hours, horizon * (index / 100))} for index in range(101)],
                              "formula": "sign * sensitivity * 2^(-t / half_life_hours)", "trigger": 1,
                              "definition": "Unit-trigger decay; an evaluated action scales this curve by its derived trigger."}
    return {"features": features, "aftereffects": aftereffects}
