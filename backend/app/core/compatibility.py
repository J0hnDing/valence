"""Read-only conservative projections of earlier contracts; never rewrite history.

Net demand cannot recover simultaneous experiences. General mental pleasure is
not evidence of rest. Combined order cannot recover two independent dimensions.
"""
from copy import deepcopy


def _clamp(value, minimum, maximum):
    return min(maximum, max(minimum, value))


def normalize_model(saved):
    """Project saved parameters for editing/copying, preserving stored JSON."""
    model = deepcopy(saved)
    if not isinstance(model, dict):
        return model, False
    converted = "resources" not in model
    if converted:
        model["resources"] = {"time_value": 0, "money_value": 0}
    features = model.get("features")
    if not isinstance(features, dict):
        return model, converted
    if "preference_alignment" in features:
        del features["preference_alignment"]
        converted = True
    if "closure_order" in features and "security_tranquility" in features:
        old = [features.pop(key) for key in ("closure_order", "security_tranquility")]
        intensity = .5
        preference = sum(item.get("positive_sensitivity", 1) * intensity ** item.get("positive_curvature", 1)
                         + item.get("negative_sensitivity", 1) * intensity ** item.get("negative_curvature", 1)
                         for item in old)
        features["order_uncertainty"] = {"family": "order_preference", "preference_sensitivity": _clamp(preference, -64, 64)}
        converted = True
    for old_key, effort_key, pleasure_key in (("cognitive_demand", "mental_effort", "mental_rest"),
                                              ("physical_demand", "physical_effort", "physical_pleasure")):
        if old_key not in features:
            continue
        old = features.pop(old_key)
        features[effort_key] = {"family": "cost", "cost_sensitivity": old.get("effort_sensitivity", old.get("cost_sensitivity", 1)),
                                "curvature": old.get("effort_curvature", old.get("curvature", 1))}
        features[pleasure_key] = {"family": "reward", "reward_sensitivity": old.get("pleasure_sensitivity", 1) if old_key == "physical_demand" else 1,
                                  "curvature": old.get("pleasure_curvature", 1) if old_key == "physical_demand" else 1}
        converted = True
    if "learning_curiosity" in features:
        features["learning_gain"] = features.pop("learning_curiosity")
        features["curiosity_engagement"] = {"family": "reward", "reward_sensitivity": 1, "curvature": 1}
        converted = True
    if "order_uncertainty" in features:
        preference = features.pop("order_uncertainty").get("preference_sensitivity", 0)
        features["structure_planning"] = {"family": "order_preference", "preference_sensitivity": preference}
        features["outcome_uncertainty"] = {"family": "order_preference", "preference_sensitivity": -preference}
        converted = True
    return model, converted


def normalize_action(saved):
    """Project earlier net encodings; independent inputs require review."""
    action = deepcopy(saved)
    if not isinstance(action, dict):
        return action, False
    converted = "net_money_cost" not in action
    if converted:
        action["net_money_cost"] = 0
    features = action.get("features")
    if not isinstance(features, dict):
        return action, converted
    notes = action.get("feature_notes")
    if "preference_alignment" in features:
        del features["preference_alignment"]
        converted = True
    if isinstance(notes, dict) and "preference_alignment" in notes:
        del notes["preference_alignment"]
        converted = True
    if "closure_order" in features and "security_tranquility" in features:
        closure, security = features.pop("closure_order"), features.pop("security_tranquility")
        features["order_uncertainty"] = _clamp((closure + security) / 2, -1, 1)
        if isinstance(notes, dict):
            parts = [notes.get("order_uncertainty")]
            for key, label in (("closure_order", "closure/order"), ("security_tranquility", "security/tranquility")):
                note = notes.pop(key, None)
                if note:
                    parts.append(f"Earlier {label} note: {note}")
            if any(parts):
                notes["order_uncertainty"] = "; ".join(part for part in parts if part)
        converted = True
    for old_key, effort_key, pleasure_key in (("cognitive_demand", "mental_effort", "mental_rest"),
                                              ("physical_demand", "physical_effort", "physical_pleasure")):
        if old_key not in features:
            continue
        value = features.pop(old_key)
        features[effort_key] = max(0, value)
        features[pleasure_key] = max(0, -value) if old_key == "physical_demand" else 0
        if isinstance(notes, dict):
            note = notes.pop(old_key, None)
            if note:
                notes[effort_key] = f"Earlier net demand note: {note}"
                prefix = ("Earlier general mental pleasure does not identify mental rest; review this input. " if old_key == "cognitive_demand"
                          else "Earlier net demand cannot identify simultaneous effort and pleasure. ")
                notes[pleasure_key] = prefix + note
        converted = True
    if "learning_curiosity" in features:
        features["learning_gain"] = features.pop("learning_curiosity")
        features["curiosity_engagement"] = 0
        if isinstance(notes, dict):
            note = notes.pop("learning_curiosity", None)
            if note:
                notes["learning_gain"] = f"Earlier combined learning/curiosity note; review knowledge actually gained: {note}"
        converted = True
    if "order_uncertainty" in features:
        value = features.pop("order_uncertainty")
        features["structure_planning"] = max(0, value)
        features["outcome_uncertainty"] = max(0, -value)
        if isinstance(notes, dict):
            note = notes.pop("order_uncertainty", None)
            if note:
                for key in ("structure_planning", "outcome_uncertainty"):
                    notes[key] = f"Earlier combined order/uncertainty note; review the independent input: {note}"
        converted = True
    return action, converted
