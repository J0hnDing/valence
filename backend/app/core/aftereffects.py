"""Deterministic aftereffect trigger and stable exponential-decay primitives."""
import math

LN2 = math.log(2.0)
SIGNS = {"accomplishment": 1, "pride_ego": 1, "relief": 1, "inspiration": 1,
         "guilt": -1, "regret": -1, "void": -1, "fatigue": -1}
TRIGGER_SPECS = {
    "accomplishment": [(0.55, "goal_progress", "pos"), (.25, "competence_mastery", "pos"), (.20, "structure_planning", "raw")],
    "pride_ego": [(.50, "status_recognition", "pos"), (.25, "competence_mastery", "pos"), (.25, "goal_progress", "pos")],
    "relief": [(.80, "structure_planning", "raw"), (.20, "autonomy_control", "pos")],
    "inspiration": [(.225, "learning_gain", "raw"), (.225, "curiosity_engagement", "raw"), (.25, "stimulation_novelty", "raw"), (.30, "identity_value_alignment", "pos")],
    "guilt": [(.40, "identity_value_alignment", "neg"), (.30, "contribution_care", "neg"), (.20, "goal_progress", "neg")],
    "regret": [(.30, "goal_progress", "neg"), (.20, "identity_value_alignment", "neg"), (.15, "autonomy_control", "neg")],
}


def finite(value: float, label="Computation") -> float:
    if not math.isfinite(value):
        raise ValueError(f"{label} exceeds finite double-precision arithmetic")
    return value


def pos(value):
    return max(value, 0.0)


def neg(value):
    return max(-value, 0.0)


def noisy_or(operands):
    return 1.0 - math.prod(1.0 - min(1.0, max(0.0, w * s)) for w, s in operands)


def triggers(features, duration_hours, exposure_hours=None):
    branch = {"pos": pos, "neg": neg, "raw": lambda x: x}
    result = {name: noisy_or((w, branch[b](features[k])) for w, k, b in spec)
              for name, spec in TRIGGER_SPECS.items()}
    result["void"] = pos(features["goal_progress"]) * features["structure_planning"]
    exposures = exposure_hours or {}
    result["fatigue"] = sum(.5 * features[key] * -math.expm1(-exposures.get(key, duration_hours) / 2)
                            for key in ("mental_effort", "physical_effort"))
    return result


def decay(amplitude, half_life_hours, elapsed_hours):
    return finite(amplitude * math.exp(-LN2 * elapsed_hours / half_life_hours), "Decay")


def decay_integral_factor(half_life_hours, horizon_hours):
    """Integral of unit amplitude, stable for tiny horizons and huge half-lives."""
    if horizon_hours == 0:
        return 0.0
    z = LN2 * horizon_hours / half_life_hours
    if math.isinf(z):
        return half_life_hours / LN2
    if z == 0:  # Underflow: the effect is constant at double precision.
        return horizon_hours
    return finite(horizon_hours * (-math.expm1(-z) / z), "Decay integral factor")


def integrate_decay(amplitude, half_life_hours, horizon_hours):
    return finite(amplitude * decay_integral_factor(half_life_hours, horizon_hours), "Integrated aftereffect")
