# Dynamic needs and current state (engine v7)

Valence evaluates actions using only the caller-provided current state. It does not
estimate action impacts on satisfaction, satisfaction rates, or a new state. Callers
own impacts, rates, accumulation, recovery, and event processing, and supply the
resulting current state for each evaluation. Manual daily-state saving and immutable
evaluation snapshots remain available; evaluation never changes supplied or saved state.

## Contracts and defaults

`PersonModel.homeostasis` contains `needs` with exactly five keys:
`physical_activity`, `mental_stimulation`, `social_interaction`,
`close_connection`, and `goal_progression`. Each has `lower = 0.6`,
`upper = 0.8`, and `sensitivity = 1`.
Require finite `0 < lower <= upper < 1` and sensitivity in `[0,64]`.
Satisfaction rates are not part of the current model contract. A sensitivity of 1 uses the same reference utility unit as a default
unit one-time reward; it is an engineering starting value, independent of intrinsic
feature parameters. The cap is a configurable range, not empirical calibration.

`homeostasis.mental_effort_weight = 0.4` is configurable in `[0,1]`;
the learning weight is its complement (default 0.6). These combine action features
for utility scoring; they do not estimate satisfaction changes.

`TransientState.need_satisfaction` is a partial object with those five keys and
values in `[0,1]`. Missing keys disable that need's contribution; they do not
assume a midpoint. `mental_energy` and `physical_energy` are optional/null or
finite values in `[0,1]`. Missing/null energy means modifier 1. Acute stress,
date, and notes retain their existing meanings.

## Action scoring inputs

| Need | Normalized action-feature value |
| --- | --- |
| Physical activity | physical_effort |
| Mental stimulation | w * mental_effort + (1-w) * learning_gain |
| Social interaction | social_exposure |
| Close connection | relatedness_intimacy |
| Goal progression | goal_progress |

Normalize nonnegative features by their documented maximum into `[0,1]` and
signed features by the corresponding positive/negative range into `[-1,1]`.
Current canonical ranges already use these units. An ongoing feature with zero
exposure supplies zero scoring input. A positive exposure supplies the feature's intensity
once, independently of its duration. One-time learning and goal outcomes count at
zero action duration too. Do not add features or use semantic interpretation.

For each available need, evaluate pressure at the supplied current satisfaction `s`:

```text
D(s) = max(0, (lower - s) / lower)
E(s) = max(0, (s - upper) / (1 - upper))
pressure(s) = D(s)^2 - E(s)^2
need utility = sensitivity * pressure(s) * action_feature_value
```

Pressure lies in `[-1,1]`. Deprivation gives positive pressure, the optimum interval
(including both endpoints) gives zero, and overload gives negative pressure. A
positive relevant feature therefore gains utility under deprivation and loses it
under overload. Signed features use the same rule with their supplied sign. This
scores the action in its current context; it makes no claim about how the action
will change satisfaction. For example, a positive feature of 1 with sensitivity 1
contributes 1 at satisfaction 0, zero at 0.7, and -1 at satisfaction 1.

Each contribution is bounded in magnitude by its sensitivity; their sum is bounded
by the sum of sensitivities. Unknown needs contribute zero, with unavailable
current satisfaction, deprivation, and overload explicitly reported as null and
pressure reported as zero. Current traces expose only current satisfaction,
normalized action-feature value, parameters, deprivation, overload, pressure,
utility contribution, and the scoring formula. They contain no impacts, rates,
before/after values, or predicted state.

## Energy and accounting

The existing transient keys `low_mental_energy_cognitive_multiplier` and
`low_physical_energy_physical_multiplier` now represent alpha for mental and
physical energy respectively. New models default to 1, with range `[0,64]`.
Saved alpha values are retained where in range; earlier larger values are capped
on read-only projection and flagged for review. Original snapshots are preserved.
Stress parameters and formulas are unchanged.

```text
m(e) = clip(1 + alpha * (0.7 - e), 0.5, 2)
energy utility = sum((m(e) - 1) * original effort contribution)
```

Original effort contributions include their actual exposure hours. The positive
modifier cannot reverse cost polarity. Energy produces no need reward and does
not modify rest, pleasure, need-scoring inputs, or aftereffects.

```text
base gross = ongoing + one-time + aftereffects (existing formulas, no energy)
base utility = base gross - time cost - money cost
gross utility = base gross + needs utility + energy utility
total utility = base utility + needs utility + energy utility
utility/action-hour = (gross utility - money cost) / duration hours
```

The hourly diagnostic still excludes time cost and is undefined at zero duration.
Feature traces describe base contributions, with separate need and energy traces
and complete graph dependencies. With unknown needs and unknown energy (or
energy 0.7), the new layer contributes zero. This reproduces the intrinsic engine
without energy modifications. Stored v1-v6 results stay readable under their
recorded contracts and are not recomputed as v7. Engine v6 prediction traces remain
historical data only. Read-only projections of v6 models discard obsolete
satisfaction rates for current editing and scoring while preserving their original
stored JSON. Current requests reject obsolete rate fields.

## Responsibility and future scope

State evolution belongs to callers, including action impacts, satisfaction rates,
time-based accumulation, recovery, event-driven updates, and relationship-specific
state. These are not deferred features to implement inside Valence. Hunger/sleep
scoring dimensions and learned/calibrated scoring parameters remain outside this
implementation and would require separately agreed contracts. The initialization
quiz does not infer homeostatic sensitivities, intervals, or scoring weights.
