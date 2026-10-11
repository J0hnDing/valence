import json
import math

import pytest
from pydantic import ValidationError

from app.core.aftereffects import decay, decay_integral_factor, integrate_decay, noisy_or, triggers
from app.core.ontology import FEATURE_KEYS, ONTOLOGY, render_markdown
from app.core.utility import evaluate, model_preview, response
from app.schemas.models import ActionInput, PersonModel, TransientState, default_model


def action(duration=60, **features):
    return ActionInput(title="Encoded action", duration_minutes=duration, net_money_cost=0,
                       features={key: features.get(key, 0) for key in FEATURE_KEYS})


def contributions(result):
    return {trace["feature_key"]: trace["response_value"] for trace in result["feature_traces"]}


@pytest.mark.parametrize("x,expected", [(0, 0), (.5, .5), (-.5, -1.5)])
def test_asymmetric_branches_have_independent_sensitivity_and_curvature(x, expected):
    assert response("asymmetric_signed", x, {"positive_sensitivity": 2, "negative_sensitivity": 3,
                                            "positive_curvature": 2, "negative_curvature": 1}) == expected


@pytest.mark.parametrize("family,x,params,expected", [
    ("cost", .5, {"cost_sensitivity": 3, "curvature": 2}, -.75),
    ("reward", .5, {"reward_sensitivity": 3, "curvature": 2}, .75),
    ("reward_overload", .5, {"reward_sensitivity": 2, "overload_sensitivity": 3}, .25),
])
def test_other_response_families(family, x, params, expected):
    assert response(family, x, params) == expected


def test_default_model_is_complete_and_new_instances_are_independent():
    first, second = default_model(), default_model()
    assert len(first.features) == 19
    assert len(first.aftereffects) == 8
    assert first.features["stimulation_novelty"].reward_sensitivity == .8
    assert first.features["social_exposure"].overload_sensitivity == .8
    first.features["goal_progress"].positive_sensitivity = 3
    assert second.features["goal_progress"].positive_sensitivity == 1


@pytest.mark.parametrize("mental,physical,cognitive,body", [(0, 0, -1.5, -1.5), (.5, .5, -1.25, -1.25), (1, 1, -1, -1), (0, 1, -1.5, -1)])
def test_energy_modifiers_are_separate(mental, physical, cognitive, body):
    result = evaluate(action(mental_effort=1, physical_effort=1), default_model(),
                      TransientState(mental_energy=mental, physical_energy=physical))
    rates = contributions(result)
    assert rates["mental_effort"] == cognitive
    assert rates["physical_effort"] == body


def test_stress_modifies_only_overload_and_negative_signed_sensitivity():
    result = evaluate(action(competence_mastery=-.4, goal_progress=.4, stimulation_novelty=1, social_exposure=1,
                             mental_effort=1, learning_gain=1), default_model(), TransientState(acute_stress=1))
    rates = contributions(result)
    assert rates["competence_mastery"] == -.5
    assert rates["goal_progress"] == .4
    assert rates["stimulation_novelty"] == pytest.approx(.8 - .6 * 1.25)
    assert rates["social_exposure"] == pytest.approx(.6 - .8 * 1.25)
    assert rates["mental_effort"] == -1.25
    assert rates["learning_gain"] == 1


@pytest.mark.parametrize("name,features,expected", [
    ("accomplishment", {"goal_progress": .8, "competence_mastery": .4, "structure_planning": .5}, 1 - (1 - .55 * .8) * (1 - .25 * .4) * (1 - .2 * .5)),
    ("pride_ego", {"status_recognition": .6, "competence_mastery": .4, "goal_progress": .8}, 1 - (1 - .5 * .6) * (1 - .25 * .4) * (1 - .25 * .8)),
    ("relief", {"structure_planning": .5, "autonomy_control": .8}, 1 - (1 - .80 * .5) * (1 - .20 * .8)),
    ("inspiration", {"learning_gain": .6, "stimulation_novelty": .8, "identity_value_alignment": .5}, 1 - (1 - .225 * .6) * (1 - .25 * .8) * (1 - .3 * .5)),
    ("guilt", {"identity_value_alignment": -.5, "contribution_care": -.6, "goal_progress": -.8}, 1 - (1 - .4 * .5) * (1 - .3 * .6) * (1 - .2 * .8)),
    ("regret", {"goal_progress": -.8, "identity_value_alignment": -.6, "autonomy_control": -.4}, 1 - (1 - .3 * .8) * (1 - .2 * .6) * (1 - .15 * .4)),
    ("void", {"goal_progress": .8, "structure_planning": .4}, .32),
    ("fatigue", {"mental_effort": .6, "physical_effort": .2}, .4 * (1 - math.exp(-1))),
])
def test_each_aftereffect_trigger_from_independent_explicit_formula(name, features, expected):
    assert triggers(action(**features).features, 2)[name] == pytest.approx(expected)


def test_noisy_or_clamps_operands_and_signed_trigger_branches_ignore_opposite_sign():
    assert noisy_or([(10, 2), (-1, 1)]) == 1
    positive = triggers(action(goal_progress=1, identity_value_alignment=1, contribution_care=1).features, 1)
    negative = triggers(action(goal_progress=-1, structure_planning=0, competence_mastery=-1).features, 1)
    assert positive["guilt"] == 0
    assert negative["accomplishment"] == 0
    assert negative["void"] == 0


def test_decay_half_life_and_integral_match_analytic_expectation():
    assert decay(3, 12, 12) == pytest.approx(1.5)
    assert decay(-3, 12, 24) == pytest.approx(-.75)
    assert integrate_decay(3, 12, 12) == pytest.approx(3 * 12 / math.log(2) * .5)
    assert integrate_decay(-3, 12, 12) == pytest.approx(-3 * 12 / math.log(2) * .5)
    assert integrate_decay(3, 12, 0) == 0


def test_integration_is_stable_for_extreme_positive_half_lives_and_small_horizons():
    assert integrate_decay(2, 1e308, 168) == pytest.approx(336)
    assert integrate_decay(2, 1e308, 1e-100) == pytest.approx(2e-100, abs=0)
    assert decay_integral_factor(5e-324, 168) == pytest.approx(5e-324 / math.log(2), abs=0)
    assert decay_integral_factor(4, 1e308) == pytest.approx(4 / math.log(2))


def test_fatigue_duration_factor_retains_tiny_nonzero_durations():
    duration = 1e-20
    value = triggers(action(mental_effort=1, physical_effort=1).features, duration)["fatigue"]
    assert value == pytest.approx(duration / 2, rel=1e-15, abs=0)


def test_duration_integrates_rates_and_total_contains_all_signed_effects():
    model, state = default_model(), TransientState(mental_energy=1, physical_energy=1)
    result = evaluate(action(duration=120, goal_progress=.8, structure_planning=.5, mental_effort=.4), model, state, 12)
    assert result["during_rate"] == pytest.approx(-.4)
    assert result["one_time_utility"] == pytest.approx(.8)
    assert result["during_utility"] == pytest.approx(2 * -.4)
    expected_after = sum(trace["sign"] * trace["sensitivity"] * trace["trigger"] * trace["half_life_hours"] / math.log(2)
                         * (1 - 2 ** (-12 / trace["half_life_hours"])) for trace in result["aftereffect_traces"])
    assert result["aftereffect_utility"] == pytest.approx(expected_after)
    assert result["total_utility"] == pytest.approx(result["during_utility"] + .8 + expected_after)
    assert result["utility_per_action_hour"] == pytest.approx(result["total_utility"] / 2)
    assert {t["name"]: t["sign"] for t in result["aftereffect_traces"]} == {
        "accomplishment": 1, "pride_ego": 1, "relief": 1, "inspiration": 1,
        "guilt": -1, "regret": -1, "void": -1, "fatigue": -1}


def test_zero_duration_retains_nonfatigue_aftereffects_and_has_no_ratio():
    result = evaluate(action(duration=0, goal_progress=1, mental_effort=1), default_model(), TransientState())
    assert result["during_utility"] == 0
    assert result["utility_per_action_hour"] is None
    assert result["total_utility"] > 0
    assert next(t for t in result["aftereffect_traces"] if t["name"] == "fatigue")["trigger"] == 0


def test_zero_horizon_and_neutral_features():
    result = evaluate(action(), default_model(), TransientState())
    assert result["total_utility"] == 0
    result = evaluate(action(goal_progress=1), default_model(), TransientState(), 0)
    assert result["aftereffect_utility"] == 0
    assert result["total_utility"] == 1


def test_notes_title_date_do_not_change_calculations_and_inputs_are_not_mutated():
    model, state, original = default_model(), TransientState(date="2026-10-06"), action(goal_progress=.7)
    before = json.dumps([model.model_dump(), original.model_dump(), state.model_dump(mode="json")], sort_keys=True)
    first = evaluate(original, model, state)
    assert first == evaluate(original, model, state)
    changed = original.model_copy(update={"title": "Different", "feature_notes": {"goal_progress": "Caller provenance"}})
    second = evaluate(changed, model, state.model_copy(update={"notes": "Different", "date": state.date.replace(day=7)}))
    for key in ("during_rate", "during_utility", "aftereffect_utility", "total_utility", "feature_traces", "aftereffect_traces"):
        assert first[key] == second[key]
    assert before == json.dumps([model.model_dump(), original.model_dump(), state.model_dump(mode="json")], sort_keys=True)
    assert next(n for n in second["graph"]["nodes"] if n["id"] == "feature:goal_progress")["note"] == "Caller provenance"


def test_complete_graph_is_closed_unique_and_traces_match_numeric_nodes():
    result = evaluate(action(goal_progress=.7, structure_planning=.3, mental_effort=.8), default_model(), TransientState())
    nodes = {node["id"]: node for node in result["graph"]["nodes"]}
    assert len(nodes) == len(result["graph"]["nodes"])
    assert all(edge["source"] in nodes and edge["target"] in nodes for edge in result["graph"]["edges"])
    for node in nodes.values():
        assert math.isfinite(node["value"])
        assert isinstance(node["inputs"], dict)
        assert isinstance(node["parameters"], dict)
        assert node["definition"] and node["formula"]
    for trace in result["feature_traces"]:
        assert nodes[f"response:{trace['feature_key']}"]["value"] == trace["response_value"]
    for trace in result["aftereffect_traces"]:
        assert nodes[f"trigger:{trace['name']}"]["value"] == trace["trigger"]
        assert nodes[f"integral:{trace['name']}"]["value"] == trace["integrated_utility"]
    assert nodes["total_utility"]["value"] == result["total_utility"]
    assert "operands" in nodes["trigger:accomplishment"]["inputs"]


@pytest.mark.parametrize("definition", ONTOLOGY, ids=lambda item: item["key"])
def test_every_ontology_domain_is_enforced(definition):
    key, low, high = definition["key"], definition["minimum"], definition["maximum"]
    action(**{key: low})
    action(**{key: high})
    for invalid in (low - .001, high + .001, math.nan, math.inf, -math.inf):
        with pytest.raises(ValidationError):
            action(**{key: invalid})


def test_missing_and_extra_vector_keys_notes_and_negative_duration_rejected():
    values = action().model_dump()
    del values["features"]["goal_progress"]
    with pytest.raises(ValidationError):
        ActionInput.model_validate(values)
    values = action().model_dump()
    values["features"]["unknown"] = 0
    with pytest.raises(ValidationError):
        ActionInput.model_validate(values)
    with pytest.raises(ValidationError):
        action(duration=-1)
    with pytest.raises(ValidationError):
        ActionInput(**{**action().model_dump(), "feature_notes": {"unknown": "text"}})
    with pytest.raises(ValidationError):
        ActionInput(**{**action().model_dump(), "title": "   "})


@pytest.mark.parametrize("feature,parameter,invalid", [
    ("goal_progress", "positive_sensitivity", -1), ("goal_progress", "negative_sensitivity", -1),
    ("goal_progress", "positive_curvature", 0), ("goal_progress", "negative_curvature", -1),
    ("mental_effort", "cost_sensitivity", -1), ("physical_effort", "curvature", 0),
    ("learning_gain", "reward_sensitivity", math.inf), ("learning_gain", "curvature", math.nan),
    ("social_exposure", "overload_sensitivity", -1), ("stimulation_novelty", "reward_sensitivity", math.nan),
])
def test_invalid_response_parameters(feature, parameter, invalid):
    values = default_model().model_dump()
    values["features"][feature][parameter] = invalid
    with pytest.raises(ValidationError):
        PersonModel.model_validate(values)


def test_exact_model_structure_and_response_families_enforced():
    for change in ("missing_feature", "extra_feature", "wrong_family", "missing_effect", "extra_effect", "extra_parameter"):
        values = default_model().model_dump()
        if change == "missing_feature":
            del values["features"]["goal_progress"]
        elif change == "extra_feature":
            values["features"]["unknown"] = values["features"]["goal_progress"]
        elif change == "wrong_family":
            values["features"]["goal_progress"] = {"family": "reward", "reward_sensitivity": 1, "curvature": 1}
        elif change == "missing_effect":
            del values["aftereffects"]["void"]
        elif change == "extra_effect":
            values["aftereffects"]["unknown"] = {"sensitivity": 1, "half_life_hours": 1}
        else:
            values["features"]["goal_progress"]["ambition"] = 1
        with pytest.raises(ValidationError):
            PersonModel.model_validate(values)


@pytest.mark.parametrize("field,value", [("sensitivity", -1), ("sensitivity", math.nan), ("half_life_hours", 0), ("half_life_hours", -1), ("half_life_hours", math.inf)])
def test_invalid_aftereffect_parameters(field, value):
    values = default_model().model_dump()
    values["aftereffects"]["guilt"][field] = value
    with pytest.raises(ValidationError):
        PersonModel.model_validate(values)


@pytest.mark.parametrize("value", [-.1, 1.1, math.inf, math.nan])
@pytest.mark.parametrize("field", ["mental_energy", "physical_energy", "acute_stress"])
def test_state_domains(field, value):
    with pytest.raises(ValidationError):
        TransientState(**{field: value})


def test_transient_multipliers_must_be_finite_nonnegative_and_extra_state_forbidden():
    for parameter in default_model().transient.model_dump():
        for invalid in (-1, math.nan, math.inf):
            values = default_model().model_dump()
            values["transient"][parameter] = invalid
            with pytest.raises(ValidationError):
                PersonModel.model_validate(values)
    with pytest.raises(ValidationError):
        TransientState(energy=1)


@pytest.mark.parametrize("invalid", [-1, math.nan, math.inf, "bad", None])
def test_horizon_validation(invalid):
    with pytest.raises(ValueError):
        evaluate(action(), default_model(), TransientState(), invalid)


def test_overflow_is_reported_instead_of_emitting_nonfinite_json():
    model = default_model()
    model.features["competence_mastery"].positive_sensitivity = 1e308
    with pytest.raises(ValueError, match="double-precision"):
        evaluate(action(duration=600, competence_mastery=1), model, TransientState())


def test_backend_preview_samples_effective_response_and_unit_trigger_decay():
    model = default_model()
    preview = model_preview(model, TransientState(acute_stress=1), 12)
    assert set(preview["features"]) == set(FEATURE_KEYS)
    assert len(preview["features"]["goal_progress"]["points"]) == 101
    assert preview["features"]["goal_progress"]["points"][0] == {"x": -1, "y": -1.25}
    assert preview["features"]["stimulation_novelty"]["preferred_exposure"] == pytest.approx(.8 / (2 * .6 * 1.25))
    assert preview["aftereffects"]["guilt"]["points"][0]["y"] == -.45
    assert preview["aftereffects"]["guilt"]["points"][-1]["y"] == pytest.approx(-.225)
    model.features["social_exposure"].overload_sensitivity = 0
    assert model_preview(model, TransientState())["features"]["social_exposure"]["preferred_exposure"] is None
    model.features["social_exposure"].overload_sensitivity = .1
    assert model_preview(model, TransientState())["features"]["social_exposure"]["preferred_exposure"] == 1


def test_public_boundary_revalidates_mutated_nested_inputs():
    encoded = action()
    encoded.features["goal_progress"] = math.nan
    with pytest.raises(ValidationError):
        evaluate(encoded, default_model(), TransientState())
    model = default_model()
    del model.features["goal_progress"]
    with pytest.raises(ValidationError):
        model_preview(model, TransientState())


def test_input_key_insertion_order_does_not_change_evaluation():
    original = action(goal_progress=.7, mental_effort=.3)
    reversed_values = original.model_dump()
    reversed_values["features"] = dict(reversed(list(reversed_values["features"].items())))
    reversed_model = default_model().model_dump()
    reversed_model["features"] = dict(reversed(list(reversed_model["features"].items())))
    reversed_model["aftereffects"] = dict(reversed(list(reversed_model["aftereffects"].items())))
    assert evaluate(original, default_model(), TransientState()) == evaluate(reversed_values, reversed_model, TransientState())


def test_preview_keeps_very_large_horizon_finite():
    result = model_preview(default_model(), TransientState(), 1e308)
    assert all(math.isfinite(point[axis]) for trace in result["aftereffects"].values()
               for point in trace["points"] for axis in ("x", "y"))


def test_ontology_document_is_generated_from_public_contract():
    from pathlib import Path
    assert Path(__file__).resolve().parents[2].joinpath("FEATURES.md").read_text(encoding="utf-8") == render_markdown()
    assert all(item["definition"] and item["anchors"] and item["belongs"] and item["excludes"]
               and item["distinction"] and item["examples"] for item in ONTOLOGY)


def test_library_engine_imports_without_web_framework_or_persistence():
    import subprocess
    import sys
    from pathlib import Path
    result = subprocess.run([sys.executable, "-c", "from app.core.utility import evaluate; from app.schemas import default_model; import sys; assert 'fastapi' not in sys.modules; assert 'sqlalchemy' not in sys.modules; assert len(default_model().features) == 19"],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
