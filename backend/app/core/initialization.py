"""Friendly, versioned Likert elicitation of editable utility-model estimates.

Item style and forward/reverse scoring draw on the public IPIP item pool:
https://ipip.ori.org/newNEOKey.htm
https://ipip.ori.org/newScoringInstructions.htm
These are original everyday statements, not an IPIP scale or validated scores.

Scoring contract (all choices are integers 1..5): z = (answer - 3) / 2.
SIGNALS below explicitly name every item weight; a negative weight reverse-keys
the item. Signal score = sum(weight*z for answered items) / (sum(abs(weight)
for ALL items in that signal) + 2). The two neutral pseudo-observations and
fixed denominator shrink sparse evidence instead of exaggerating one answer.
Domain signals combine related statements for summaries and later feelings.
Asymmetric response branches use their own direct evidence; one conservatively
shrunk direct statement is preferable to assuming likes and harms are symmetric.
PARAMETER_SIGNALS combines
signals using an ordinary weighted mean, with all declared weights in its
denominator. A skipped signal therefore contributes zero, not extra certainty.

Nonnegative sensitivities and state modifiers = default*(1 + .75*score),
bounded to [.25*default, 1.75*default]. Half-lives = default*2**(2*score),
bounded to [.25*default, 4*default]. Signed preference = .8*score,
bounded to [-.8, .8]. Positive structure preference favors planned activity;
positive uncertainty preference favors uncertain outcomes. They are independent.
All response curvatures remain defaults: agreement cannot identify a curve.
These conservative ranges and item-to-utility associations are engineering
heuristics, not empirically calibrated utility magnitudes or duration estimates.
"""
from app.schemas import PersonModel, default_model

VERSION = "5"
OPTIONS = [{"label": label, "value": i} for i, label in enumerate((
    "Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree", "Strongly agree"), 1)]

# Interleaved rather than blocked by a named personality dimension. Examples
# illustrate the statement; respondents need not have experienced that event.
ITEMS = [
    ("explore_ideas", "You enjoy exploring questions even when you gain no new knowledge.", "Investigating why a gadget behaves oddly feels engaging, even if you find no answer."),
    ("try_new_experiences", "You enjoy trying unfamiliar experiences.", "You try a new local activity whose format and likely outcome are clear."),
    ("plan_ahead", "You enjoy following a clear plan that you chose and can change.", "You organize your errands and enjoy the structure while remaining free to rearrange them."),
    ("enjoy_conversation", "You enjoy ordinary conversation with other people.", "You feel pleased after chatting with a few people over lunch."),
    ("enjoy_mental_rest", "You find relief in resting your mind and setting mental demands aside.", "A quiet break without decisions or problems to solve feels restorative."),
    ("enjoy_movement", "You enjoy the feeling of moving your body.", "The movement itself feels good during a walk or a stretch."),
    ("choose_your_way", "You like being free to choose, change, or refuse what you do.", "You appreciate being able to change a detailed plan you chose for a household task."),
    ("help_someone", "You feel good when you make someone else's day easier.", "You help a neighbor carry something and feel glad you did."),
    ("value_progress", "You find small steps toward an important goal rewarding.", "Finishing one part of a project you care about improves your day."),
    ("value_closeness", "You find warm, personal time with someone close to you rewarding.", "You appreciate an unhurried conversation with a trusted friend."),
    ("enjoy_recognition", "You enjoy being admired, respected, or acknowledged by others.", "You feel good when others recognize your contribution, even if your lasting reputation does not change."),
    ("enjoy_influence", "You enjoy exercising authority or having a real say in group decisions.", "You enjoy directing a meeting using authority you already have."),
    ("express_values", "You feel good when you express a specific personal principle through your actions.", "You keep a promise because honesty is an important principle for you."),
    ("crowds_drain", "You find busy groups tiring even when the people are friendly.", "After a crowded gathering, you want a quiet break."),
    ("feelings_linger", "Unpleasant feelings tend to stay with you after the event is over.", "A frustrating exchange keeps bothering you later that evening."),
    ("prefer_certainty", "You prefer knowing what will happen, even when uncertain outcomes would be equally harmless.", "With equally pleasant options, you prefer knowing the result in advance rather than getting a surprise."),
    ("enjoy_uncertain_outcomes", "You enjoy not knowing exactly what will happen when the possible outcomes are acceptable.", "An activity's outcome remains a surprise even though its steps are fully planned."),
    ("concentration_costly", "Sustained concentration feels demanding to you.", "An hour of careful planning feels like hard mental work."),
    ("exertion_costly", "Sustained physical exertion feels demanding to you.", "Carrying several heavy bags feels like hard bodily work."),
    ("exclusion_hurts", "Being left out bothers you.", "You feel hurt when a group makes plans without including you."),
    ("tired_thinking", "Mental work feels much harder when you are tired.", "A planning task feels more taxing after a poor night's sleep."),
    ("tired_movement", "Physical effort feels much harder when you are tired.", "The same stairs feel more demanding when your body is worn out."),
    ("stress_crowds", "Busy surroundings feel more overwhelming when you are stressed.", "A crowded shop feels harder to handle on an already stressful day."),
    ("stress_setbacks", "Setbacks upset you more when you are already stressed.", "A small problem with your plans feels worse during a tense day."),
    ("prefer_familiar", "You usually prefer familiar activities to new experiences.", "You choose a familiar place for an outing rather than trying a new one."),
    ("learning_satisfies", "You find gaining new knowledge or understanding rewarding.", "You feel satisfied after understanding a new idea, even if learning it was not engaging."),
    ("improvise_plan", "You enjoy freely improvising instead of following a detailed plan.", "You choose the order of familiar errands as you go, with predictable outcomes and full freedom."),
    ("enjoy_group", "You feel good when a group makes you feel welcome.", "You feel pleased when a group includes you in its plans."),
    ("failure_stings", "It bothers you when you cannot do something as well as you hoped.", "An unsuccessful attempt at a skill you care about feels discouraging."),
    ("setback_stings", "Losing progress toward an important goal is upsetting to you.", "You feel disappointed when work on a valued project has to be redone."),
    ("conflict_hurts", "Conflict with someone close to you affects you strongly.", "An argument with a trusted friend makes the day feel worse."),
    ("criticism_stings", "Criticism from people whose opinion matters to you stings.", "You feel bad after your contribution is dismissed in front of others."),
    ("imposition_bothers", "You feel frustrated when someone takes away your choice.", "Someone insists on a method without letting you choose how to approach the task."),
    ("harm_bothers", "You feel troubled when your actions make life harder for someone else.", "You feel bad after accidentally creating an avoidable problem for a neighbor."),
    ("values_conflict", "Acting against an important personal principle bothers you.", "You feel uncomfortable after choosing something that conflicts with your values."),
    ("no_say_bothers", "You feel frustrated when you have no say in a shared decision.", "A group decides something important without letting you contribute."),
    ("recover_quickly", "You usually move on from unpleasant feelings quickly.", "A frustrating exchange stops bothering you soon after it ends."),
    ("good_feelings_linger", "Good feelings from a meaningful success stay with you.", "Finishing something important still feels good later that day."),
    ("good_feelings_fade", "Your good feelings usually fade soon after a positive event.", "The pleasure of a successful task quickly gives way to an ordinary mood."),
    ("completion_empty", "You sometimes feel empty after finishing something important.", "After a major project ends, you miss having it to work toward."),
    ("completion_settles", "Finishing a pending task leaves you feeling settled.", "Once a lingering obligation is handled, you feel at ease."),
    ("energy_recovers", "Your energy usually returns quickly after demanding activity.", "After a tiring task and a short break, you feel ready to do more."),
    ("fatigue_lingers", "You tend to stay tired after demanding activity.", "A difficult session of work leaves you drained well afterward."),
    ("improve_skill", "You feel satisfied when you get better at a skill.", "You feel good after learning to use a cooking technique more confidently."),
]
QUESTION_BY_ID = {identifier: {"id": identifier, "prompt": prompt, "example": example}
                  for identifier, prompt, example in ITEMS}

SIGNALS = {
    "learning": {"learning_satisfies": 1},
    "curiosity": {"explore_ideas": 1},
    "novelty": {"try_new_experiences": 1, "prefer_familiar": -1},
    "structure": {"plan_ahead": 1, "improvise_plan": -1},
    "uncertainty": {"enjoy_uncertain_outcomes": 1, "prefer_certainty": -1},
    "social_reward": {"enjoy_conversation": 1},
    "overload": {"crowds_drain": 1, "stress_crowds": .5},
    "mental_rest": {"enjoy_mental_rest": 1},
    "physical_pleasure": {"enjoy_movement": 1},
    "mental_cost": {"concentration_costly": 1, "tired_thinking": .3},
    "physical_cost": {"exertion_costly": 1, "tired_movement": .3},
    "autonomy": {"choose_your_way": 1, "imposition_bothers": 1},
    "competence": {"improve_skill": 1, "failure_stings": 1},
    "goals": {"value_progress": 1, "setback_stings": 1},
    "closeness": {"value_closeness": 1, "conflict_hurts": 1},
    "belonging": {"enjoy_group": 1, "exclusion_hurts": 1},
    "recognition": {"enjoy_recognition": 1, "criticism_stings": 1},
    "influence": {"enjoy_influence": 1, "no_say_bothers": 1},
    "care": {"help_someone": 1, "harm_bothers": 1},
    "values": {"express_values": 1, "values_conflict": 1},
    # The second, weaker item provides general cost/reactivity evidence, rather
    # than claiming it directly measures a tired-versus-rested comparison.
    "tired_mental": {"tired_thinking": 1, "concentration_costly": .3},
    "tired_physical": {"tired_movement": 1, "exertion_costly": .3},
    "stressed_overload": {"stress_crowds": 1, "crowds_drain": .3},
    "stressed_negative": {"stress_setbacks": 1, "setback_stings": .3, "exclusion_hurts": .3},
    "negative_persistence": {"feelings_linger": 1, "recover_quickly": -1},
    "positive_persistence": {"good_feelings_linger": 1, "good_feelings_fade": -1},
    "void": {"completion_empty": 1, "completion_settles": -.5},
    "relief": {"completion_settles": 1, "plan_ahead": .5},
    "fatigue_persistence": {"fatigue_lingers": 1, "energy_recovers": -1},
}

# Direct branch evidence is intentionally separate from paired domain summaries.
# Enjoying recognition says little about the harm of criticism, for example.
BRANCH_ITEMS = {
    "autonomy_control": ("choose_your_way", "imposition_bothers"),
    "competence_mastery": ("improve_skill", "failure_stings"),
    "goal_progress": ("value_progress", "setback_stings"),
    "relatedness_intimacy": ("value_closeness", "conflict_hurts"),
    "belonging_acceptance": ("enjoy_group", "exclusion_hurts"),
    "status_recognition": ("enjoy_recognition", "criticism_stings"),
    "influence_power": ("enjoy_influence", "no_say_bothers"),
    "contribution_care": ("help_someone", "harm_bothers"),
    "identity_value_alignment": ("express_values", "values_conflict"),
}
for _feature, (_positive, _negative) in BRANCH_ITEMS.items():
    SIGNALS[f"{_feature}_positive"] = {_positive: 1}
    SIGNALS[f"{_feature}_negative"] = {_negative: 1}


def _parameter_signals():
    result = {}
    for feature in BRANCH_ITEMS:
        for branch in ("positive", "negative"):
            result[f"features.{feature}.{branch}_sensitivity"] = {f"{feature}_{branch}": 1}
    for feature, kind in (("mental_effort", "mental"), ("physical_effort", "physical")):
        result[f"features.{feature}.cost_sensitivity"] = {f"{kind}_cost": 1}
    result.update({
        "features.mental_rest.reward_sensitivity": {"mental_rest": 1},
        "features.physical_pleasure.reward_sensitivity": {"physical_pleasure": 1},
        "features.learning_gain.reward_sensitivity": {"learning": 1},
        "features.curiosity_engagement.reward_sensitivity": {"curiosity": 1},
        "features.stimulation_novelty.reward_sensitivity": {"novelty": 1},
        "features.stimulation_novelty.overload_sensitivity": {"overload": 1},
        "features.social_exposure.reward_sensitivity": {"social_reward": 1},
        "features.social_exposure.overload_sensitivity": {"overload": 1},
        "features.structure_planning.preference_sensitivity": {"structure": 1},
        "features.outcome_uncertainty.preference_sensitivity": {"uncertainty": 1},
        "transient.low_mental_energy_cognitive_multiplier": {"tired_mental": 1},
        "transient.low_physical_energy_physical_multiplier": {"tired_physical": 1},
        "transient.stress_overload_multiplier": {"stressed_overload": 1},
        "transient.stress_negative_multiplier": {"stressed_negative": 1},
    })
    effects = {
        "accomplishment": {"goals": 1, "competence": .5, "positive_persistence": .5},
        "pride_ego": {"recognition": 1, "positive_persistence": .5},
        "relief": {"relief": 1},
        "inspiration": {"curiosity": 1, "novelty": .5, "positive_persistence": .5},
        "guilt": {"care": 1, "values": 1},
        "regret": {"goals": .5, "autonomy": .5},
        "void": {"void": 1},
        "fatigue": {"mental_cost": .5, "physical_cost": .5, "fatigue_persistence": .5},
    }
    for effect, signals in effects.items():
        result[f"aftereffects.{effect}.sensitivity"] = signals
        persistence = ("fatigue_persistence" if effect == "fatigue" else "positive_persistence"
                       if effect in ("accomplishment", "pride_ego", "relief", "inspiration") else "negative_persistence")
        result[f"aftereffects.{effect}.half_life_hours"] = {persistence: 1}
    return result


PARAMETER_SIGNALS = _parameter_signals()


def quiz_schema():
    return {"version": VERSION, "instructions": [
        "Answer for this person as they usually are in everyday life. Each example helps explain the statement.",
        "Choose what feels closest, or skip if you are unsure."],
        "options": [dict(option) for option in OPTIONS], "questions": [dict(item) for item in QUESTION_BY_ID.values()]}


def validate_answers(answers):
    for identifier, value in answers.items():
        if identifier not in QUESTION_BY_ID:
            raise ValueError(f"Unknown quiz answer: {identifier}")
        if value is None:
            continue
        # Exact integers reject booleans, strings, floats (including 3.0), NaN,
        # infinity and fractional values before transport can coerce them.
        if type(value) is not int or not 1 <= value <= 5:
            raise ValueError(f"{identifier} must be an integer choice from 1 to 5, or null")
    return answers


def _score(answers, weights):
    return sum(weight * ((answers[key] - 3) / 2) for key, weight in weights.items()
               if answers.get(key) is not None) / (sum(abs(w) for w in weights.values()) + 2)


INSIGHT_TEXT = {
    "learning": ("Gaining knowledge", "Gaining new knowledge and understanding seems rewarding to you.", "Gaining knowledge may carry a quieter emotional reward for you."),
    "curiosity": ("Exploring questions", "Exploring questions seems rewarding even without gaining knowledge.", "Exploration itself may carry a quieter emotional reward for you."),
    "novelty": ("New experiences", "You seem drawn to variety and trying unfamiliar experiences.", "You tend to prefer familiar experiences and routines."),
    "structure": ("Plans and improvisation", "Following a clear plan you chose seems rewarding to you.", "You tend to enjoy freely improvising instead of following a detailed plan."),
    "uncertainty": ("Uncertain outcomes", "Not knowing exactly what will happen can feel enjoyable to you.", "You tend to prefer knowing what will happen, even when alternatives are harmless."),
    "social_reward": ("Everyday company", "Ordinary conversation and group time tend to lift your mood.", "Group time may offer you less reward than quieter time."),
    "overload": ("Busy surroundings", "Busy social settings can feel draining, even when the people are friendly.", "Busy settings seem less likely to feel draining to you."),
    "mental_rest": ("Resting your mind", "Setting mental demands aside and resting your mind seems rewarding to you.", "Mental rest may carry a quieter emotional reward for you."),
    "physical_pleasure": ("Enjoying movement", "The feeling of movement itself can be rewarding for you.", "Movement may offer you less pleasure for its own sake."),
    "care": ("Helping others", "Making life better for someone else seems to matter strongly to you.", "Helping others may carry a quieter emotional weight for you."),
    "goals": ("Meaningful progress", "Progress toward goals you care about seems especially rewarding.", "Goal progress may have a gentler effect on your mood."),
    "positive_persistence": ("Lasting good feelings", "Good feelings from positive events tend to stay with you.", "Good feelings tend to fade soon after a positive event."),
    "negative_persistence": ("Recovering from feelings", "Unpleasant feelings tend to linger after an event ends.", "You tend to move on from unpleasant feelings fairly quickly."),
    "fatigue_persistence": ("Recovering energy", "Tiredness can linger after demanding activity.", "Your energy tends to return fairly quickly after demanding activity."),
    "autonomy": ("Having a choice", "Choosing your own approach seems to matter strongly to you.", "Having your own choice may carry a quieter emotional weight for you."),
    "closeness": ("Close relationships", "Warmth and conflict in close relationships seem to affect you strongly.", "Changes in closeness may have a gentler effect on your mood."),
}


def _insights(answers, scores):
    candidates = []
    for order, (signal, (label, positive, negative)) in enumerate(INSIGHT_TEXT.items()):
        if any(answers.get(key) is not None for key in SIGNALS[signal]):
            score = scores[signal]
            description = positive if score > .08 else negative if score < -.08 else "Your answers suggest no strong lean in this area yet."
            candidates.append((-abs(score), order, {"label": label, "description": description}))
    candidates.sort(key=lambda item: item[:2])
    insights = [item[2] for item in candidates[:6]]
    answered = sum(value is not None for value in answers.values())
    fillers = [
        {"label": "A tentative start", "description": "A few more answers can make these starting estimates less dependent on defaults." if answered < 12 else "These tendencies are starting estimates based on everyday preferences, ready for you to review."},
        {"label": "What is still open", "description": f"You answered {answered} of {len(ITEMS)} statements. Skipped areas keep their starting defaults."},
        {"label": "Flexible estimates", "description": "The response shapes remain at their defaults because these statements cannot identify them."},
    ]
    for filler in fillers:
        if len(insights) >= 3:
            break
        insights.append(filler)
    return insights


def initialize_from_quiz(answers):
    validate_answers(answers)
    model = default_model().model_dump(mode="json")
    scores = {signal: _score(answers, weights) for signal, weights in SIGNALS.items()}
    defaulted = []
    for group, members in model.items():
        if group == "homeostasis":
            # This questionnaire supplies no evidence for dynamic need parameters.
            defaulted.append("homeostasis.mental_effort_weight")
            defaulted.extend(f"homeostasis.needs.{key}.{field}"
                             for key, parameters in members["needs"].items() for field in parameters)
            continue
        for key, parameters in members.items():
            fields = parameters if isinstance(parameters, dict) else {None: parameters}
            for field, baseline in fields.items():
                if field == "family":
                    continue
                path = f"{group}.{key}" + (f".{field}" if field is not None else "")
                signals = PARAMETER_SIGNALS.get(path)
                if signals is None or not any(answers.get(item) is not None for signal in signals for item in SIGNALS[signal]):
                    defaulted.append(path)
                    continue
                score = sum(weight * scores[signal] for signal, weight in signals.items()) / sum(signals.values())
                if field == "preference_sensitivity":
                    value = max(-.8, min(.8, .8 * score))
                elif field == "half_life_hours":
                    value = max(.25 * baseline, min(4 * baseline, baseline * 2**(2 * score)))
                else:
                    value = max(.25 * baseline, min(1.75 * baseline, baseline * (1 + .75 * score)))
                if field is None:
                    members[key] = value
                else:
                    parameters[field] = value
    answered = sum(value is not None for value in answers.values())
    warnings = ["These are conservative starting estimates, not calibrated utility ratings. Review them as you learn what fits you.",
                "Response curvatures remain at their defaults; agreement statements do not identify response shapes.",
                "Dynamic need parameters retain engineering defaults; this questionnaire does not calibrate them."]
    if answered < 12:
        warnings.append("With few answers, the estimates stay especially close to defaults.")
    return {"model": PersonModel.model_validate(model).model_dump(mode="json"), "warnings": warnings,
            "defaulted": defaulted, "answered": answered, "total": len(ITEMS), "insights": _insights(answers, scores)}
