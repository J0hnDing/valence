Build a complete local application from scratch called **Valence**.

Implement the full working application, not just scaffolding. Run tests, fix failures, and leave the repository ready to run.

## 1. Purpose

Valence is a deterministic, interpretable utility engine.

It does **not** understand natural-language actions and does **not** call any LLM.

A caller is responsible for:
1. understanding a real-world action;
2. considering any relevant external context;
3. converting the action into Valence's fixed 19-dimensional feature representation.

Valence receives:

```text
Action features x
+
Person Model θ
+
small transient state s
```

and calculates:

```text
utility = F(x, θ, s)
```

It should:
- calculate utility experienced during the action;
- calculate persistent post-action effects;
- integrate ongoing experience and aftereffects over time;
- count whole-action outcomes once;
- subtract time and money utility costs at the end;
- rank candidate actions by net total utility;
- expose the complete computation graph.

The same inputs must always produce exactly the same output.

Do not implement:
- LLM calls;
- Codex integration;
- natural-language action parsing;
- goals/preferences/relationships databases;
- parameter learning;
- feedback learning;
- uncertainty or probability estimates about outcomes;
- reinforcement learning.

---

# 2. Stack

Backend:
- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy or SQLModel
- SQLite
- pytest

Frontend:
- React
- TypeScript
- Vite
- React Flow
- Recharts or similar lightweight chart library
- Tailwind CSS or equivalent

Keep the utility engine as a pure Python module independent of FastAPI and persistence.

Suggested structure:

```text
valence/
  backend/
    app/
      core/
        ontology.py
        utility.py
        aftereffects.py
      api/
      db/
      schemas/
      main.py
    tests/

  frontend/
    src/
      pages/
      components/
      graph/
      api/
      types/
```

---

# 3. Core objects

## Person

A Person contains only the computational Person Model.

```text
id
name
description?
created_at
updated_at
```

No goals, preferences, relationships, interests, todos, or other personal-world data belong in Valence.

---

## Action

An action is already encoded by the caller.

```text
id
title
duration_minutes
net_money_cost
features
feature_notes?
feature_duration_minutes?
created_at
updated_at
```

`features` must contain all 19 feature values.

`feature_notes` is optional diagnostic/provenance text and never affects calculations.

`feature_duration_minutes` optionally maps ongoing feature keys to finite exposure minutes from zero through `duration_minutes`. Omitted keys use the full action duration. This permits a short episode of connection, authority or relief within a longer action. Unknown keys, one-time feature keys and exposures greater than the action duration are rejected. One-time outcomes cannot receive an exposure override.

Example:

```json
{
  "title": "Attend AI conference",
  "duration_minutes": 360,
  "net_money_cost": 0,
  "features": {
    "mental_effort": 0.35,
    "mental_rest": 0,
    "physical_effort": 0.15,
    "physical_pleasure": 0.1,
    "stimulation_novelty": 0.7,
    "learning_gain": 0.75,
    "curiosity_engagement": 0.65,
    "autonomy_control": 0.2,
    "competence_mastery": 0.1,
    "goal_progress": 0.6,
    "structure_planning": 0.7,
    "outcome_uncertainty": 0.4,
    "social_exposure": 0.9,
    "relatedness_intimacy": 0.05,
    "belonging_acceptance": 0.1,
    "status_recognition": 0.15,
    "influence_power": 0.05,
    "contribution_care": 0.0,
    "identity_value_alignment": 0.3
  }
}
```

---

# 4. Canonical 19-feature ontology

Define the ontology centrally in `ontology.py`. It is part of Valence's public API.

Every definition must contain its key, display name, domain, precise definition, anchors, inclusions, exclusions, distinctions, response family and temporal basis. Generate `FEATURES.md` from that source; it provides the detailed anchors and examples used by the Feature Reference page and external callers.

Features describe what the action offers or causes. Person Model parameters describe how the person values those inputs. A desire for recognition or authority belongs in response parameters; recognition received or authority exercised belongs in the action vector. Specific possible resource gains or losses belong in their relevant outcome/resource fields, rather than being compressed into an uncertainty intensity.

| Key | Domain | Response family | Temporal basis |
| --- | --- | --- | --- |
| `mental_effort` | [0,1] | `cost` | `rate` |
| `mental_rest` | [0,1] | `reward` | `rate` |
| `physical_effort` | [0,1] | `cost` | `rate` |
| `physical_pleasure` | [0,1] | `reward` | `rate` |
| `stimulation_novelty` | [0,1] | `reward_overload` | `rate` |
| `learning_gain` | [0,1] | `reward` | `one_time` |
| `curiosity_engagement` | [0,1] | `reward` | `rate` |
| `autonomy_control` | [-1,1] | `asymmetric_signed` | `rate` |
| `competence_mastery` | [-1,1] | `asymmetric_signed` | `rate` |
| `goal_progress` | [-1,1] | `asymmetric_signed` | `one_time` |
| `structure_planning` | [0,1] | `order_preference` | `rate` |
| `outcome_uncertainty` | [0,1] | `order_preference` | `rate` |
| `social_exposure` | [0,1] | `reward_overload` | `rate` |
| `relatedness_intimacy` | [-1,1] | `asymmetric_signed` | `rate` |
| `belonging_acceptance` | [-1,1] | `asymmetric_signed` | `rate` |
| `status_recognition` | [-1,1] | `asymmetric_signed` | `one_time` |
| `influence_power` | [-1,1] | `asymmetric_signed` | `rate` |
| `contribution_care` | [-1,1] | `asymmetric_signed` | `one_time` |
| `identity_value_alignment` | [-1,1] | `asymmetric_signed` | `rate` |

## 1. mental_effort

Concentration, working-memory load and other mental demands during the activity. Keep relief independent; enjoyable inquiry can also require effort.

## 2. mental_rest

Mental rest and relief: release from mental demands, quiet and recovery during the activity. Excludes general enjoyment of thinking, learning, connection or achievement.

## 3. physical_effort

Bodily exertion, strain and discomfort during the activity. Do not subtract enjoyable sensations from exertion.

## 4. physical_pleasure

Pleasurable bodily sensations, comfort and enjoyable movement during the activity. Can coexist with physical effort; excludes general satisfaction or social enjoyment.

## 5. stimulation_novelty

Novelty, excitement, sensory stimulation and environmental intensity. Excludes outcome uncertainty itself.

## 6. learning_gain

Actual meaningful knowledge or understanding expected to be gained across the whole action. Excludes inquiry that produces no knowledge gain.

## 7. curiosity_engagement

Engagement in inquiry, exploration and investigating interesting questions, whether or not useful knowledge is gained. Excludes mental rest and generic pleasure.

## 8. autonomy_control

Experienced freedom to choose, change or refuse the activity versus coercion or constraint. A self-chosen detailed plan can be highly autonomous; lasting gains in future freedom are not required.

## 9. competence_mastery

Experienced capability, mastery and successful challenge versus salient failure or inability to perform. Excludes knowledge gained and whole-action goal progress.

## 10. goal_progress

Net whole-action progress or setback on relevant goals. The caller incorporates goal importance; do not encode the pleasure of progress itself.

## 11. structure_planning

Amount of defined plan, rules or sequence followed during the activity. Zero is freely improvised; one is tightly prescribed. Describes organization independently of autonomy and outcome uncertainty.

## 12. outcome_uncertainty

How uncertain the relevant consequences are given what the person knows. Zero is predictable consequences; one is widely varying possible consequences. This does not encode harmfulness, stakes or outcome probabilities.

## 13. social_exposure

Quantity and intensity of interpersonal interaction. Encode exposure, not whether the person likes socializing.

## 14. relatedness_intimacy

Warmth, meaningful closeness and connection experienced during the activity versus conflict and disconnection. Existing closeness counts even if the relationship does not improve.

## 15. belonging_acceptance

Experienced membership, inclusion and acceptance versus rejection or exclusion. Existing group membership counts without newly earning acceptance.

## 16. status_recognition

Discrete admiration, respect, acknowledgement or humiliation provided by the event. Displaying existing status can count when it elicits recognition; permanent reputation gains are not required. Excludes authority over decisions.

## 17. influence_power

Exercising authority, having a meaningful say and shaping external decisions versus being overruled or unable to influence them. Existing authority counts; prestige alone and freedom over one's own actions are separate.

## 18. contribution_care

Whole-action effects on helping, protecting, caring for, benefiting or harming others. Encode actual welfare effects rather than self-image or enjoyment of helping.

## 19. identity_value_alignment

Expressing or violating specific personal principles during the activity. Name the relevant principle in provenance notes; exclude broad desired self-image, ego and generic preference fit.

For nonnegative intensity features, zero means absence, approximately 0.5 means a meaningful moderate intensity, and one means an extreme intensity. Structure and uncertainty use their specific low/high anchors above. Signed features use zero for no meaningful positive or negative experience/effect, with negative and positive endpoints describing strong adverse and beneficial inputs. Do not encode the person's enjoyment into these input values.

Ongoing experience is scored only for its relevant exposure. A brief rejection or exercise of authority can have a shorter exposure than the full action. A discrete recognition event and actual learning, goal progress and contribution are counted once. Lasting changes in relationships, autonomy or power are not interchangeable with their experienced expression during an activity.

---

# 5. Person Model

The Person Model describes how this specific person responds to the 19 action features. It also contains `resources: {time_value, money_value}`: finite nonnegative utility/hour and utility/currency-unit coefficients. Both default to zero; questionnaire initialization does not estimate them. Use one consistent caller-declared currency; no conversion is performed.

Do not create broad personality variables such as:

```text
introversion
ambition
ego
laziness
work_ethic
```

Those should emerge from the response parameters.

Current Person Models use five response-function families: `asymmetric_signed`, `cost`, `order_preference`, `reward`, and `reward_overload`. The retired `signed_effort` family is accepted only through explicit legacy compatibility conversion.

---

## asymmetric_signed

Used by:

```text
autonomy_control
competence_mastery
goal_progress
relatedness_intimacy
belonging_acceptance
status_recognition
influence_power
contribution_care
identity_value_alignment
```

Fields:

```text
positive_sensitivity >= 0
negative_sensitivity >= 0
positive_curvature > 0
negative_curvature > 0
```

Function:

For `x >= 0`:

```text
f(x) =
positive_sensitivity *
x ^ positive_curvature
```

For `x < 0`:

```text
f(x) =
-negative_sensitivity *
(-x) ^ negative_curvature
```

---

## cost

Used by `mental_effort` and `physical_effort`.

Fields:

```text
cost_sensitivity >= 0
curvature > 0
```

Function:

```text
f(x) = -cost_sensitivity * x ^ curvature
```

Low mental or physical energy changes only the corresponding effort cost. Rest and physical pleasure have separate reward parameters and can coexist with effort.

---

## order_preference

Used independently by `structure_planning` and `outcome_uncertainty`. Each input is in `[0,1]`, and each has its own signed preference parameter.

Fields:

```text
preference_sensitivity in [-64, 64]
```

Function:

```text
f(x) = preference_sensitivity * x
```

A positive parameter rewards more of that input; a negative parameter assigns it a cost; zero expresses no modeled preference. Enjoying structure does not imply disliking uncertainty. The two preferences are estimated and edited independently.

---

---

## reward

Used by:

```text
mental_rest
physical_pleasure
learning_gain
curiosity_engagement
```

Fields:

```text
reward_sensitivity >= 0
curvature > 0
```

Function:

```text
f(x) =
reward_sensitivity *
x ^ curvature
```

---

## reward_overload

Used by:

```text
stimulation_novelty
social_exposure
```

Fields:

```text
reward_sensitivity >= 0
overload_sensitivity >= 0
```

Function:

```text
f(x) =
reward_sensitivity * x
-
overload_sensitivity * x²
```

Derived preferred exposure:

```text
preferred_exposure =
reward_sensitivity /
(2 * overload_sensitivity)
```

when `overload_sensitivity > 0`.

Clamp the displayed preferred exposure to `[0,1]`.

---

# 6. Default Person Model

Defaults are engineering placeholders, not scientifically calibrated values.

For every `asymmetric_signed` feature:

```text
positive_sensitivity = 1
negative_sensitivity = 1
positive_curvature = 1
negative_curvature = 1
```

Mental and physical effort:

```text
cost_sensitivity = 1
curvature = 1
```

Structure and outcome uncertainty (independent parameters):

```text
preference_sensitivity = 0
```

Rest, physical pleasure, learning gain and curiosity:

```text
reward_sensitivity = 1
curvature = 1
```

Stimulation:

```text
reward_sensitivity = 0.8
overload_sensitivity = 0.6
```

Social exposure:

```text
reward_sensitivity = 0.6
overload_sensitivity = 0.8
```

---

# 7. Transient state

Keep transient state separate from the persistent Person Model.

Support exactly:

```text
mental_energy: [0,1] or null/omitted
physical_energy: [0,1] or null/omitted
acute_stress: [0,1]
need_satisfaction: partial object of the five canonical needs, values in [0,1]
date
notes?
```

Defaults:

```text
mental_energy = null
physical_energy = null
acute_stress = 0
need_satisfaction = {}
```

Person Model global parameters:

```text
low_mental_energy_cognitive_multiplier in [0,64] (mental alpha)
low_physical_energy_physical_multiplier in [0,64] (physical alpha)
stress_overload_multiplier >= 0
stress_negative_multiplier >= 0
```

Defaults:

```text
1
1
0.25
0.25
```

Effective cognitive cost:

```text
base_cost * clip(1 + low_mental_energy_cognitive_multiplier * (0.7 - mental_energy), 0.5, 2)
```

Effective physical cost:

```text
base_cost * clip(1 + low_physical_energy_physical_multiplier * (0.7 - physical_energy), 0.5, 2)
```

Effective overload sensitivity for:
- social exposure;
- stimulation/novelty:

```text
base_overload *
(
  1 +
  stress_overload_multiplier *
  acute_stress
)
```

Effective negative sensitivity for asymmetric features:

```text
base_negative_sensitivity *
(
  1 +
  stress_negative_multiplier *
  acute_stress
)
```

Unknown energy uses modifier 1. Record the difference from original integrated effort cost as `energy_utility`, keeping feature traces as base contributions. Do not modify rest, pleasure, need-scoring inputs or aftereffects with energy.

Engine v7 scores five dynamic needs from the supplied current state: physical activity, mental stimulation, social interaction, close connection, and goal progression. Store optimal bounds and sensitivity in `PersonModel.homeostasis`; store the caller-provided partial current satisfaction values in transient state. Missing satisfaction disables that need. Current pressure is squared normalized deprivation minus squared normalized overload. Each need contributes `sensitivity * current_pressure * associated_action_feature_value` once per action, ignoring ongoing inputs at zero exposure. The action-feature scoring inputs do not estimate satisfaction impacts. Impacts, satisfaction rates, recovery, accumulation and derivation of new state are the caller's responsibility. No predicted satisfaction or before/after value is calculated or returned. Manual daily-state saving and evaluation snapshots remain supported; evaluation never applies state changes. See [HOMEOSTASIS.md](HOMEOSTASIS.md) for final schemas, bounds, equations, defaults and ownership.

---

# 8. Ongoing and one-time utility

The canonical ontology declares `temporal_basis` for every feature.

One-time outcomes: `learning_gain`, `goal_progress`, `status_recognition`, `contribution_care`. Their responses are utility units for the whole action, counted once even at zero duration. Encode the entire outcome without dividing by duration.

All remaining features are ongoing experiences (`rate`); their responses are utility units/hour. For each ongoing feature, `E_i` is its optional exposure override divided by 60, or the action duration `D = duration_minutes / 60` when omitted.

```text
during_utility = Σ (ongoing_response_i * E_i)
one_time_utility = Σ one_time_response_i
during_rate = during_utility / D if D > 0 else 0
```

`during_rate` is the duration-weighted diagnostic average, not an additional contribution. With no overrides, it equals the sum of ongoing responses. Expose each response, temporal basis, exposure minutes/hours and actual integrated or one-time contribution. One-time traces have null exposure values. Duration is not normalized to a unit interval.

---

# 9. Post-action effects

Implement exactly:

```text
accomplishment
pride_ego
relief
inspiration
guilt
regret
void
fatigue
```

These are derived effects, not action features. Before deriving triggers, use zero for ongoing feature inputs whose exposure is zero. One-time inputs remain active even for zero-duration actions. Positive exposure retains the encoded input intensity; fatigue additionally uses each effort feature's actual exposure duration.

Define:

```text
pos(x) = max(x, 0)
neg(x) = max(-x, 0)
```

Define:

```text
noisy_or((w1,s1), ..., (wn,sn))
=
1 - Π(
    1 - clamp(wi * si, 0, 1)
)
```

Triggers:

## accomplishment

```text
noisy_or(
  (0.55, pos(goal_progress)),
  (0.25, pos(competence_mastery)),
  (0.20, structure_planning)
)
```

## pride_ego

```text
noisy_or(
  (0.50, pos(status_recognition)),
  (0.25, pos(competence_mastery)),
  (0.25, pos(goal_progress))
)
```

## relief

```text
noisy_or(
  (0.80, structure_planning),
  (0.20, pos(autonomy_control))
)
```

## inspiration

```text
noisy_or(
  (0.225, learning_gain),
  (0.225, curiosity_engagement),
  (0.25, stimulation_novelty),
  (0.30, pos(identity_value_alignment))
)
```

## guilt

```text
noisy_or(
  (0.40, neg(identity_value_alignment)),
  (0.30, neg(contribution_care)),
  (0.20, neg(goal_progress))
)
```

## regret

```text
noisy_or(
  (0.30, neg(goal_progress)),
  (0.20, neg(identity_value_alignment)),
  (0.15, neg(autonomy_control))
)
```

## void

```text
pos(goal_progress) *
structure_planning
```

## fatigue

Only mental and physical effort generate fatigue. Their actual exposure durations are used; rest and physical pleasure do not add fatigue.

```text
trigger = 0.5 * mental_effort * (1 - exp(-mental_effort_exposure_hours / 2))
        + 0.5 * physical_effort * (1 - exp(-physical_effort_exposure_hours / 2))
```

Each effort exposure defaults to the action duration. The trigger remains in `[0,1]`.

---

# 10. Aftereffect Person Model

Each aftereffect has:

```text
sensitivity >= 0
half_life_hours > 0
```

Signs:

Positive:

```text
accomplishment
pride_ego
relief
inspiration
```

Negative:

```text
guilt
regret
void
fatigue
```

Initial amplitude:

```text
A =
sign *
sensitivity *
trigger
```

Decay:

```text
effect(t) =
A *
2 ^ (-t / half_life_hours)
```

Default integration horizon:

```text
168 hours
```

Integrated utility:

```text
U =
A *
half_life_hours / ln(2) *
(
  1 -
  2 ^
  (
    -horizon_hours /
    half_life_hours
  )
)
```

Default aftereffect parameters:

```text
accomplishment:
  sensitivity = 0.50
  half_life_hours = 12

pride_ego:
  sensitivity = 0.35
  half_life_hours = 6

relief:
  sensitivity = 0.40
  half_life_hours = 4

inspiration:
  sensitivity = 0.30
  half_life_hours = 8

guilt:
  sensitivity = 0.45
  half_life_hours = 12

regret:
  sensitivity = 0.45
  half_life_hours = 12

void:
  sensitivity = 0.30
  half_life_hours = 8

fatigue:
  sensitivity = 0.40
  half_life_hours = 4
```

---

# 11. Total action utility

For action `a`:

```text
base_gross = during_utility + one_time_utility + aftereffect_utility
gross_utility = base_gross + needs_utility + energy_utility
time_cost = resources.time_value * duration_hours
money_cost = resources.money_value * net_money_cost
resource_cost = time_cost + money_cost
base_utility = base_gross - resource_cost
total_utility = base_utility + needs_utility + energy_utility
utility_per_action_hour = (gross_utility - money_cost) / duration_hours
```

Also expose:

```text
during_rate
during_utility
one_time_utility
aftereffect_utility
gross_utility
time_cost
money_cost
resource_cost
base_utility
needs_utility
energy_utility
need_traces
energy_traces
total_utility
utility_per_action_hour
```

Rank actions by:

```text
total_utility DESC
```

Every new or updated action must provide finite signed `net_money_cost`: positive spending, negative income, explicit zero for no money effect. Money is a whole-action amount deducted once. Avoid counting the same financial return in goal progress. Time value represents expected utility from an alternative use of the time.

Utility/hour includes money cost but excludes time cost, and is null for zero duration. Zero-duration actions retain one-time outcomes and money cost; ongoing utility and time cost are zero. All resource products, aggregates and ratios must stay finite.

Do not rank by utility/hour.

Do not normalize the score to `0–10`.

Negative scores are valid.

Do not output probability.

---

# 12. Computation trace

Every evaluation must produce a complete structured trace.

For each action feature:

```text
feature_key
raw_value
response_family
effective_parameters
formula
temporal_basis
response_value
exposure_minutes          # null for one-time outcomes
exposure_hours            # null for one-time outcomes
utility_rate_contribution  # null for one-time outcomes
utility_contribution       # integrated or one-time utility
```

For every aftereffect:

```text
name
trigger
sensitivity
half_life_hours
sign
initial_amplitude
integrated_utility
formula
```

The frontend must consume backend traces.

Do not reproduce calculations independently in React.

---

# 13. Persistence

Use SQLite.

Persist:

```text
persons
person_model_versions
daily_states
actions
evaluations
evaluation_results
```

Person Model edits should create new versions.

Legacy 15-, 16- and 17-feature records are converted to the current 19-feature schema in a read-only compatibility view. The retired preference alignment is omitted. Positive old mental/physical demand maps to effort, negative physical demand maps to physical pleasure, and negative general mental pleasure is not treated as mental rest: rest defaults to zero. Old learning/curiosity maps to learning gain while curiosity engagement defaults to zero. Positive old combined order/uncertainty maps to structure; its negative side maps to uncertainty. Older closure/order and security/tranquility inputs first use their existing combined compatibility mapping. These conversions are conservative and lossy: a single signed legacy value cannot recover simultaneous effort and pleasure, separate curiosity from learning, or distinguish autonomy, structure and uncertainty. Show a compatibility warning and let the caller review the current encoding.

Saving an edited action stores the current shape. Legacy model versions remain immutable; compatibility copies carry forward effort and physical-pleasure response parameters, while new mental-rest and curiosity responses use engineering defaults. Structure and uncertainty preferences derive from the old combined directional preference and retain the same documented limitations. Earlier models receive zero resource coefficients in the read-only compatibility view. Existing SQLite action tables receive an additive non-null `net_money_cost` column defaulting to zero and the persistence needed for optional feature exposures.

Historical v1-v6 snapshots and traces remain unchanged with their original semantics. Reproduction requires the original engine version; engine v7 reproduces only v7 snapshots. New evaluations of converted older inputs use v7 semantics and may differ from saved historical totals. Read-only model projections add default homeostatic parameters and retain saved energy strengths up to the new bound of 64; larger legacy values are capped and flagged for review. Obsolete v6 satisfaction rates are stripped only from the read-only model projection; original v6 models and prediction traces remain historical data. Current model requests reject rates. Saved states with numeric energy remain explicit inputs; missing need satisfaction is neutral. Changing current actions, exposure overrides, state or model coefficients must not affect saved evaluations. Atlas schema synchronization is deferred while the Valence schema is being refined.

Every evaluation must reference:
- exact Person Model version;
- exact action values;
- transient state;
- horizon;
- timestamp.

Historical evaluations retain their exact original results and remain reproducible with the matching original engine version.

---

# 14. API

Implement approximately:

```text
GET    /api/health

GET    /api/persons
POST   /api/persons
GET    /api/persons/{id}

GET    /api/persons/{id}/model
PUT    /api/persons/{id}/model

GET    /api/daily-state
PUT    /api/daily-state

GET    /api/actions
POST   /api/actions
GET    /api/actions/{id}
PUT    /api/actions/{id}
DELETE /api/actions/{id}

POST   /api/evaluations
GET    /api/evaluations
GET    /api/evaluations/{id}

GET    /api/ontology
```

`GET /api/ontology` should expose the canonical feature specification.

---

# 15. Frontend

Implement these pages.

## Compare

Select:
- Person;
- transient state;
- candidate actions.

Run evaluation.

Show ranking:

```text
1. Work on project      +6.82
2. Play tennis          +5.19
3. Attend conference    +2.44
```

Also show:
- ongoing utility;
- one-time utility;
- aftereffect utility;
- time and money utility costs;
- duration;
- utility/action-hour excluding time cost.

---

## Actions

Allow creating/editing an action by entering:
- title;
- duration;
- required net money cost, including explicit zero;
- all 19 feature values;
- optional notes;
- optional exposure minutes for ongoing features.

Provide compact sliders and numeric inputs.

Show each feature's definition and anchors.

Validate ranges immediately.

---

## Person Model

Allow editing every Person Model parameter.

For each feature show:
- definition;
- function;
- parameter controls;
- response curve.

For `reward_overload`, show derived preferred exposure.

Also expose:
- time value and money value resource coefficients;
- transient response parameters;
- aftereffect sensitivities;
- aftereffect half-lives;
- decay curves.

---

## Evaluation Detail

Use React Flow to display the real computation graph.

Example:

```text
Caller features + person responses + state
    ongoing responses -> response * feature exposure -> sum ongoing utility
    one-time responses --------------------------> one-time utility
    aftereffect triggers -> decay integration ---> aftereffect utility

ongoing + one-time + aftereffects -> gross utility
    gross - (time value * hours + money value * net money cost) -> total
    (gross - money value * net money cost) / hours -> utility/action-hour
```

Every node should expose its numeric value.

Clicking a node opens an inspector with:
- definition;
- inputs;
- parameters;
- formula;
- output;
- optional caller-supplied feature note.

No LLM-generated explanation.

---

## Feature Reference

Create a dedicated page based on the canonical ontology.

For all 19 features show:
- exact definition;
- range;
- anchors;
- what belongs in it;
- what does NOT belong in it;
- distinctions from similar features;
- example values.

This documentation must be good enough that another LLM or external caller can reliably populate the vector.

Also provide the same information in:

```text
FEATURES.md
```

---

## History

Show historical evaluations and allow reopening their computation graph.

---

# 16. UI design

Valence should look like an analytical instrument, not a consumer productivity app.

Use:
- dark neutral interface;
- compact controls;
- clear numeric hierarchy;
- visible formulas;
- response curves;
- computation graphs.

Avoid:
- chat UI;
- excessive cards;
- marketing layout;
- unnecessary animation;
- gradients everywhere.

---

# 17. Validation

Reject:
- missing features;
- feature values outside their domains;
- NaN;
- infinity;
- negative cost/reward/overload/asymmetric sensitivities; signed structure and uncertainty preferences are allowed;
- non-positive curvature where prohibited;
- non-positive half-lives;
- negative duration;
- unknown or one-time exposure keys;
- negative, nonfinite or greater-than-action exposure durations.

Use double precision.

Round only for display.

Zero-duration actions are allowed but have zero during-action utility.

---

# 18. Tests

Write substantial backend tests covering:

1. all five response families;
2. positive and negative asymmetric branches;
3. transient mental-energy modifier;
4. transient physical-energy modifier;
5. acute-stress modifiers;
6. all eight aftereffect triggers;
7. aftereffect decay integration;
8. action-duration and per-feature exposure integration;
9. total utility;
10. ranking;
11. ontology range validation;
12. model versioning;
13. historical evaluation reproducibility.

Add API tests for critical endpoints.

Frontend should at least test:
- action feature entry;
- Person Model editing;
- comparison results;
- graph trace rendering.

---

# 19. Demo data

Seed an optional clearly labelled DEMO Person.

Also include example actions such as:

```text
Study ML for 2 hours
Play tennis for 90 minutes
Attend AI conference for 6 hours
Work on a personal project for 3 hours
```

Their feature vectors may be manually defined for demonstration.

Do not imply they are universally correct encodings.

---

# 20. README

Document:

- what Valence is;
- architecture;
- `Q = F(x, θ, s)`;
- distinction between action features and Person Model;
- all 19 features;
- person response functions;
- aftereffects;
- API;
- setup;
- startup commands;
- tests;
- current limitations.

Explicitly mention:

- Valence does not understand natural-language actions;
- callers must provide the 19-dimensional action representation;
- Person Model parameters are manually specified;
- there is no learning yet;
- there are no uncertainty or probability estimates for outcomes;
- the ontology is experimental;
- utility units are arbitrary but internally consistent;
- time opportunity cost is caller-specified through the time-value coefficient; Valence does not estimate alternative activities.

---

# 21. Critical architectural constraints

Do NOT:

- call an LLM;
- depend on Codex;
- store Atlas-style personal data;
- infer feature values from text;
- add personality-trait shortcuts;
- add probabilistic outputs;
- implement learning;
- use embeddings;
- replace the formulas with a neural network;
- calculate utility in frontend code;
- hide intermediate computations.

Valence should be a reusable deterministic engine.

Its conceptual API is:

```text
evaluate(
    action_features,
    duration,
    person_model,
    transient_state
)
→
utility_trace
```

The core engine should be usable directly as a Python library without FastAPI.

---

# 22. Acceptance criteria

The implementation is complete when:

- I can create a Person.
- I can manually edit every Person Model parameter.
- I can inspect every response curve.
- I can enter transient state.
- I can create an action by entering all 19 feature values.
- Every feature is range validated.
- I can compare multiple actions.
- Valence deterministically ranks them.
- I can inspect every feature contribution.
- I can inspect every aftereffect.
- I can inspect the full computation graph.
- I can reopen historical evaluations.
- `/api/ontology` exposes the canonical feature schema.
- `FEATURES.md` clearly tells external callers how to populate every feature.
- backend tests pass;
- frontend build/typecheck passes.

Work autonomously. Implement the application, test it, fix issues, and finish the README.

At the end, report only:
- what was implemented;
- important implementation choices;
- test/build results;
- exact commands to run Valence locally.
