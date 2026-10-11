# Valence

Valence is a local deterministic utility engine: **Q = F(x, θ, s)**. A caller supplies an already encoded action vector `x`, a Person Model `θ` initialized from defaults, an exact saved copy, or questionnaire answers, and transient state `s`. Valence integrates ongoing experience, counts whole-action outcomes once, adds eight decaying aftereffects, evaluates five dynamic needs and energy-dependent effort costs, subtracts time and money utility costs, ranks candidates by net total utility, and exposes every calculation through structured traces and a computation graph.

Valence does not understand natural-language actions. Callers must interpret actions and external context and provide all 19 feature values. Titles and notes never affect a score. There are no LLM calls, Codex integration, embeddings, personality shortcuts, personal-world databases, learning, or estimates of outcome likelihood.

The current formula and acceptance contract is documented in [docs/SPECIFICATION.md](docs/SPECIFICATION.md).

## Setup (Windows PowerShell)

Requirements: Python 3.12+, Node.js 22.12+ (22.x) or 24.x, and npm. This checkout was verified with Python 3.12 and Node.js 24.18. From the repository root:

```powershell
Set-Location 'C:\Users\John\Projects\Valence'
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.lock.txt
npm --prefix frontend ci
```

Optional, idempotent demonstration data:

```powershell
Set-Location 'C:\Users\John\Projects\Valence\backend'
& ..\.venv\Scripts\python.exe -m app.seed
Set-Location ..
```

The seed creates a clearly labelled DEMO Person and manually encoded study, tennis, conference and personal-project actions. These encodings are examples, not universally correct representations. The backend lock file records the verified dependency versions; requirements.txt and pyproject.toml record the supported dependency ranges. npm uses the checked-in package-lock.json.

## Run

Start these commands in two terminals:

```powershell
& 'C:\Users\John\Projects\Valence\scripts\start-backend.ps1'
```

```powershell
& 'C:\Users\John\Projects\Valence\scripts\start-frontend.ps1'
```

Open [Valence](http://127.0.0.1:5173). [API documentation](http://127.0.0.1:8010/docs) is on the backend. Stop each server with Ctrl+C. STARTUP.md provides the same launch commands for Projector. The Vite server proxies `/api` to `127.0.0.1:8010`.

For a production build, run `npm --prefix frontend run build` and start the backend without `--reload`. If the built frontend exists, the backend serves it at `http://127.0.0.1:8010`.

## Interface

- **Compare:** select a Person and a saved model version, edit transient state, select candidate actions and a horizon, then run an evaluation. Rankings show net total, ongoing, one-time and aftereffect utility, time and money costs, duration and utility/action-hour excluding time cost. Daily state can be saved separately. The Person Model tab manages people and parameters.
- **Actions:** create, edit and delete manually encoded vectors, with sliders, numeric inputs, immediate validation, definitions, anchors and per-feature provenance notes, a required signed net money cost (explicit zero for no monetary effect), and optional exposure minutes for ongoing features.
- **Person Model:** create/select a Person and edit their name and description. Use the model version selector to inspect any saved version's parameters and backend-sampled response/decay curves. Edit every response parameter, the time and money resource values, the four transient modifiers, and all aftereffect sensitivities and half-lives. Saving parameters from any version creates a new immutable latest version and selects it; previous versions remain available. Editing name/description does not create a model version. Compare uses the selected saved version, which stays selected across page navigation; changing people initially selects their latest version. Unsaved parameter edits do not affect comparisons.
- **Evaluation Detail:** select an evaluated action and inspect its contributions and React Flow computation graph. Click a node for definition, inputs, parameters, formula, output and optional note.
- **Feature Reference:** canonical definitions, domains, anchors, inclusions, exclusions, distinctions and example values.
- **History:** reopen the original snapshots and computation graphs of historical evaluations.

## Initializing a person

In **Person Model → Create person**, choose Default, Copy a saved version, or Personality quiz. Each method saves the initial model atomically as version 1. Copy accepts any immutable version of an active source person, including an older version; subsequent edits are independent. It copies model parameters only.

Selecting Personality quiz starts one questionnaire of 44 short everyday statements, each with a concrete example and five choices from Strongly disagree to Strongly agree. Questions are interleaved without named sections. Choosing an answer advances automatically; Back restores earlier choices and Skip leaves an answer unknown. A remaining-question count and progress bar show progress. Review offers a plain-language summary and optional answer and parameter inspection before creation. An unfinished creation draft survives app-page navigation in memory; refreshing or closing the app discards it. Cancelling or completing creation clears the draft. Only the resulting model is persisted, not the answers.

The item style and forward/reverse scoring draw on the public-domain [IPIP item pool](https://ipip.ori.org/newNEOKey.htm) and [scoring instructions](https://ipip.ori.org/newScoringInstructions.htm). The statements and their Valence mappings are original adaptations, not a validated IPIP scale or personality-type test. They estimate everyday preferences, effort, state dependence, and lingering feelings; they do not directly measure utility magnitudes or encode activities.

The backend centers choices with `(answer − 3) / 2`, reverses appropriate statements, and combines documented weights. A question can inform multiple related parameters. Positive and negative feature sensitivities use independent evidence, mental rest/relief and physical pleasure are distinct from effort costs, and structure and outcome uncertainty have independent preference evidence. Every signal uses a fixed denominator including two neutral pseudo-observations, keeping sparse evidence conservative. Nonnegative parameters move around their engineering defaults; structure and outcome-uncertainty preferences can each be positive or negative; persistence answers adjust aftereffect half-lives. Skipped answers add no evidence and unsupported parameters retain defaults. A neutral choice is an observed answer, not a skip. All response curvatures stay at defaults because agreement statements cannot identify response shapes. Exact item weights, parameter mappings, ranges, and assumptions are in `backend/app/core/initialization.py`.

Preview and creation use the same backend scoring function. Quiz parameters are editable self-report estimates, not scientifically calibrated measurements or a validated psychological assessment. Inspect curves and comparison results after creation and refine parameters as experience warrants.

## Architecture and persistence

`backend/app/core` is a pure Python engine independent of FastAPI and SQLite. `backend/app/schemas` validates inputs; `backend/app/api` exposes FastAPI; `backend/app/db` uses SQLAlchemy/SQLite. `frontend` is React/TypeScript/Vite with React Flow and Recharts. The frontend consumes backend traces, graph values and sampled curves rather than calculating utility itself.

SQLite stores `persons`, `person_model_versions`, `daily_states`, `actions`, `evaluations` and `evaluation_results`. Evaluations retain exact immutable model versions, model and action snapshots, transient state, horizon, timestamp and complete results. Editing/deleting current actions, editing models or changing daily states preserves historical evaluations. Ranking ties use a stable action-ID order. Calculations use double precision and canonical feature order. All numeric displays (including charts, traces, and snapshot previews) are rounded to at most three decimal places; numeric controls use 0.001 steps and round edits to the same precision. Existing saved values retain their full precision.

Legacy 15-, 16- and 17-feature records are exposed through a 19-feature compatibility view without changing immutable stored model versions. Positive old mental/physical demand maps to effort; negative physical demand maps to physical pleasure. Negative general mental pleasure cannot establish mental rest, so rest defaults to zero. Old learning/curiosity maps to learning gain with curiosity engagement defaulting to zero. The positive side of old combined order/uncertainty maps to structure and its negative side to uncertainty. Older closure/order and security/tranquility values first use their existing combined mapping. Preference alignment remains retired. These are conservative, lossy conversions with a warning: callers should review converted encodings, particularly simultaneous effort/pleasure and independent structure/uncertainty. Saving an edited action writes the current shape. Legacy model copies carry forward effort and physical-pleasure response parameters; new rest and curiosity responses use engineering defaults. Earlier resource coefficients default to zero in the compatibility view. SQLite schema updates are additive, including zero money cost for old actions and storage for feature exposures.

Engine v1-v6 evaluation snapshots and traces keep their original results. Reproduction requires the matching original engine version; engine v7 reproduces v7 snapshots. New evaluations of older saved inputs use current definitions, temporal bases, exposures, resources and homeostatic formulas, so totals may differ from historical evaluations. Atlas synchronization is deferred while this schema is being refined.

The default database is `backend/data/valence.db`, independent of the launch directory. Override it using `VALENCE_DATABASE_URL`, such as `sqlite:///C:/path/valence.db`. Back up the database with the application stopped. Servers bind to loopback; this is a single-user local application.

## Canonical features

The public ontology lives in `backend/app/core/ontology.py`, is exposed by `/api/ontology`, and is documented in [FEATURES.md](FEATURES.md). Every vector contains exactly these keys:

| Feature | Domain | Response family | Temporal basis |
| --- | --- | --- | --- |
| mental_effort | [0,1] | cost | rate |
| mental_rest | [0,1] | reward | rate |
| physical_effort | [0,1] | cost | rate |
| physical_pleasure | [0,1] | reward | rate |
| stimulation_novelty | [0,1] | reward_overload | rate |
| learning_gain | [0,1] | reward | one_time |
| curiosity_engagement | [0,1] | reward | rate |
| autonomy_control | [-1,1] | asymmetric_signed | rate |
| competence_mastery | [-1,1] | asymmetric_signed | rate |
| goal_progress | [-1,1] | asymmetric_signed | one_time |
| structure_planning | [0,1] | order_preference | rate |
| outcome_uncertainty | [0,1] | order_preference | rate |
| social_exposure | [0,1] | reward_overload | rate |
| relatedness_intimacy | [-1,1] | asymmetric_signed | rate |
| belonging_acceptance | [-1,1] | asymmetric_signed | rate |
| status_recognition | [-1,1] | asymmetric_signed | one_time |
| influence_power | [-1,1] | asymmetric_signed | rate |
| contribution_care | [-1,1] | asymmetric_signed | one_time |
| identity_value_alignment | [-1,1] | asymmetric_signed | rate |

Features describe what an action offers or causes; Person Model parameters describe how the person values it. Effort can coexist with bodily pleasure or mental relief. Mental rest means release from demands and recovery, not general enjoyment of thinking. Actual learning gains and curiosity engagement are separate. Structure describes the plan or rules, autonomy describes freedom to choose/change/refuse, and uncertainty describes unpredictable consequences; these can vary independently. Outcome uncertainty does not encode the harmfulness or likelihood of possible outcomes.

Closeness and belonging describe experienced connection and membership, without requiring an improvement in relationships. Recognition describes discrete admiration, respect or humiliation; influence describes exercising authority and shaping decisions, without requiring a permanent increase in power. Value alignment concerns specific personal principles, rather than broad self-image or generic preference fit. The caller incorporates relevant goal importance into `goal_progress`; Valence stores no goal records. See [FEATURES.md](FEATURES.md) for exact definitions, anchors and distinctions.

## Response functions

Each feature has a canonical temporal basis. Ongoing responses are utility units/hour; one-time responses are utility units for the whole action. Asymmetric signed features use `positive_sensitivity × x^positive_curvature` for `x ≥ 0`, or `-negative_sensitivity × (-x)^negative_curvature` otherwise. Effort cost uses `-cost_sensitivity × x^curvature`. Structure and uncertainty independently use `preference_sensitivity × x`: a positive parameter rewards that input and a negative parameter assigns it a cost. Reward uses `reward_sensitivity × x^curvature`. Reward/overload uses `reward_sensitivity × x - overload_sensitivity × x²`. Displayed preferred exposure is `reward_sensitivity / (2 × overload_sensitivity)`, clamped to `[0,1]`, when overload is positive.

Signed, cost and reward defaults set each sensitivity and curvature to 1. Structure and uncertainty preferences default to 0. Stimulation reward/overload defaults are 0.8/0.6, and social defaults are 0.6/0.8. Defaults are engineering placeholders, not scientifically calibrated values.

Transient state supports optional mental and physical energy `[0,1]` (missing/null means unknown), acute stress `[0,1]` (default 0), a partial `need_satisfaction` object, date and optional notes. Mental/physical effort costs use `clip(1 + alpha × (0.7 - energy), 0.5, 2)`; unknown energy gives modifier 1. The existing `low_mental_energy_cognitive_multiplier` and `low_physical_energy_physical_multiplier` fields now represent alpha, default 1 and bounded to `[0,64]`. Energy adjustments are reported separately as the difference from base effort contributions. Rest, physical pleasure and aftereffects are unaffected by energy. Overload and negative sensitivity still multiply by `1 + multiplier × acute_stress`, with defaults 0.25/0.25.

Five needs (physical activity, mental stimulation, social interaction, close connection and goal progression) adjust action utility using only the supplied current satisfaction and existing action features. Person Model exposes optimal intervals and sensitivities, defaulting to `[0.6,0.8]` and 1 utility unit. Each available need contributes `sensitivity * (D(current)^2 - E(current)^2) * associated_action_feature_value`, where `D` and `E` are normalized deprivation and overload. Missing satisfaction disables that need. Need contributions count once per action, independently of positive duration; ongoing features with zero exposure are ignored. Valence receives current state and never estimates satisfaction impacts, rates, or a new state. The caller owns state derivation and supplies updated current state. Manual state saving remains available; evaluations never update it. See [the complete schemas, scoring inputs and equations](docs/HOMEOSTASIS.md).

Optional `feature_duration_minutes` maps ongoing feature keys to their actual exposure minutes, from zero through the action duration; omitted keys use the full duration. A brief experience therefore need not be scored for an entire event. One-time features cannot have an override. With `D = duration_minutes / 60` and each ongoing exposure `E_i` in hours: `during_utility = Σ(response_i × E_i)`; `one_time_utility = Σ one_time_response`; `during_rate = during_utility / D` when `D > 0`, otherwise zero. Without overrides, the diagnostic rate is the sum of ongoing responses.

One-time outcomes are `learning_gain`, `goal_progress`, `status_recognition` and `contribution_care`. Encode each for the whole action without dividing by duration. All other features are ongoing experiences. Feature traces expose actual exposure minutes/hours and integrated contributions; one-time exposure fields are null.

## Resource / return

The Person Model includes `resources: {time_value, money_value}`. Both are finite nonnegative coefficients on the same utility scale as feature responses: `time_value` is the expected value of an alternative use of time in utility/hour, and `money_value` is utility per currency unit. Both default to zero and remain at zero after questionnaire initialization because the quiz does not calibrate them. Set them explicitly in Person Model. Use one consistent caller-declared currency; Valence does not convert currencies.

Every new or updated action requires finite signed `net_money_cost`: positive spending, negative income, or explicit zero. This is the whole-action net amount, not an hourly amount. Avoid counting the same financial return again in goal progress. Resource costs are deducted at the end:

```text
base_gross = during_utility + one_time_utility + aftereffect_utility
gross_utility = base_gross + needs_utility + energy_utility
time_cost = time_value * D
money_cost = money_value * net_money_cost
resource_cost = time_cost + money_cost
base_utility = base_gross - resource_cost
total_utility = base_utility + needs_utility + energy_utility
utility_per_action_hour = (gross_utility - money_cost) / D
```

Utility/action-hour includes money cost and excludes time opportunity cost. Ranking uses net total utility. Money cost is counted once regardless of duration; negative money cost represents income.

## Aftereffects

Accomplishment, pride_ego, relief and inspiration are positive. Guilt, regret, void and fatigue are negative. They are derived effects, not action features. The first six triggers use `noisy_or = 1 - Π(1 - clamp(weight × signal, 0, 1))`, where signals are specified positive/negative parts of features. This is deterministic saturation arithmetic, not a probability estimate. Void uses positive goal progress times structure. Accomplishment and relief also use structure, while uncertainty does not imply guilt. Inspiration splits its learning/curiosity signal equally between actual learning gain and curiosity engagement. Ongoing inputs with zero exposure do not trigger aftereffects. Fatigue sums half-weighted mental and physical effort, each multiplied by `1 - exp(-E_i / 2)` using its own exposure hours; rest and pleasure do not add fatigue.

| Effect | Default sensitivity | Default half-life (hours) |
| --- | ---: | ---: |
| accomplishment | 0.50 | 12 |
| pride_ego | 0.35 | 6 |
| relief | 0.40 | 4 |
| inspiration | 0.30 | 8 |
| guilt | 0.45 | 12 |
| regret | 0.45 | 12 |
| void | 0.30 | 8 |
| fatigue | 0.40 | 4 |

With trigger `T`, sensitivity `S`, sign `σ` and half-life `L`: `A = σ × S × T`, `effect(t) = A × 2^(-t/L)`, and `U = A × L / ln(2) × (1 - 2^(-H/L))`. The default post-action horizon `H` is 168 hours. Each effect starts when the action ends. The backend trace exposes all trigger operands, weights, formulas, amplitudes and integrals.

`total_utility = during_utility + one_time_utility + aftereffect_utility - resource_cost`. Rank by total utility descending, never by utility/hour. Negative scores are valid and are not normalized. Utility/action-hour divides gross utility minus money cost by duration and is `null` for zero duration. Zero-duration actions have zero during utility; their non-fatigue aftereffects still follow the specified triggers.

## API and Python library

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /api/health | Health check |
| GET, POST | /api/persons | List/create Persons |
| GET | /api/person-initialization-quiz | Versioned flat statements, examples and five agreement choices |
| POST | /api/person-initialization-quiz/preview | Score `{version, answers}` without writes; return model, insights, answer counts, warnings and defaulted parameter paths |
| GET, PUT, DELETE | /api/persons/{id} | Read/edit Person metadata or delete from active use |
| GET, PUT | /api/persons/{id}/model | Latest version/save new model version |
| GET | /api/persons/{id}/model-versions | All immutable model versions, newest first |
| GET | /api/persons/{id}/model-versions/{version_id} | Read an exact model version belonging to this Person |
| GET, PUT | /api/daily-state | Read by person_id/date; save `{person_id, state}` |
| GET, POST | /api/actions | List/create actions |
| GET, PUT, DELETE | /api/actions/{id} | Read/replace/delete action |
| POST | /api/evaluations | Evaluate `{person_id, model_version_id, action_ids, state, horizon_hours}` |
| GET | /api/evaluations | Historical summaries |
| GET | /api/evaluations/{id} | Full snapshot and traces |
| POST | /api/evaluations/{id}/reproduce | Recompute original snapshots and report exact trace equality |
| GET | /api/ontology | Canonical feature specification |
| POST | /api/model-preview | Backend curves for `{model, state, horizon_hours}` |

Model shape: `{features: {key: {family, ...parameters}}, transient: {...multipliers}, aftereffects: {name: {sensitivity, half_life_hours}}, resources: {time_value, money_value}, homeostasis: {needs: {need_key: {lower, upper, sensitivity}}, mental_effort_weight}}`. State adds `need_satisfaction: {need_key: satisfaction}` (partial) and nullable energy. Action shape: `{title, duration_minutes, net_money_cost, features: {all_19_keys}, feature_notes: {key: "optional provenance"}, feature_duration_minutes: {ongoing_key: minutes}}`. Every evaluation supplies its state explicitly. The UI supplies the selected `model_version_id`; API callers may omit it or send null to use the latest version. Versions belonging to other people are rejected. Refer to `/docs` for complete schemas.

Person creation takes `{name, description?, initialization?}`. Omit initialization or use `{method: "default"}` for defaults. Copy uses `{method: "copy", person_id, model_version_id}`. Quiz uses `{method: "quiz", version: "5", answers: {question_id: integer | null}}`; get IDs from the quiz schema. Choices must be integers from 1 to 5; null or omitted answers are unknown. Unknown IDs, unsupported versions (including the old numeric calibration quiz), booleans, strings, floats, and out-of-range answers are rejected before any person is saved. Metadata updates still accept only name and description.

From the `backend` directory, use the engine without a web server:

```python
from app.core.utility import evaluate
from app.schemas.models import ActionInput, TransientState, default_model
from app.core.ontology import ONTOLOGY

action = ActionInput(
    title="Manually encoded example",
    duration_minutes=60,
    net_money_cost=0,
    features={feature["key"]: 0.0 for feature in ONTOLOGY},
)
trace = evaluate(action, default_model(), TransientState(), horizon_hours=168)
print(trace["total_utility"])
```

Missing/unknown keys, out-of-domain features, NaN/infinity, negative nonnegative-family sensitivities/duration/horizon, and non-positive curvatures/half-lives are rejected. Signed structure/uncertainty preference sensitivities are allowed. Exposure overrides reject one-time or unknown keys and minutes outside the action duration. Computations that overflow finite double precision are rejected rather than persisted. The engine uses numerically stable exponential integration for long half-lives.

Person Model includes a confirmed **Delete person** control beside **Edit person**. Deletion removes the person from Person Model and Compare; deleting the selected person selects the next remaining person, or opens creation if none remain. Person deletion is a soft delete: stored records and versions are retained for immutable history, but all person, model-version, daily-state, and new-evaluation operations for that person return 404. Saved evaluations remain readable and reproducible. Existing SQLite databases receive an additive nullable `persons.deleted_at` column on startup.

## Tests and build

From the repository root:

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests -q
npm --prefix frontend test -- --run
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Backend tests cover response functions, signed branches, state modifiers, all triggers, decay integration, duration, totals, ranking, validation, critical endpoints, questionnaire scoring and asymmetric evidence, atomic creation, copy ownership and isolation, model version selection, metadata editing and historical reproduction. Frontend tests cover feature entry, all creation methods, quiz navigation/review/defaults/errors/draft preservation, person editing, older-version inspection and saving, explicit comparison versions, stale responses, model editing, comparison results and graph traces.

## Limitations

The ontology is experimental. Parameters are manually specified or elicited through the initialization quiz and remain uncalibrated; the quiz does not estimate dynamic need parameters. There is no learning or estimate of outcome likelihood. Utility units are arbitrary but internally consistent. Time opportunity cost is caller-specified through the time-value coefficient; Valence does not estimate alternative activities. Feature/state values stay constant over each encoded exposure; a single feature cannot encode a changing intensity timeline. Aftereffects do not feed into future actions or daily state. Impacts, satisfaction rates, accumulation, recovery and derivation of new state belong to the caller. Each evaluation records its engine version; v1-v6 snapshots remain readable, and reproduction refuses incompatible engine versions. Earlier models receive need defaults on read-only projection, preserving saved response/stress parameters and energy alpha values within bounds; obsolete v6 satisfaction rates are removed only in the compatibility view, and no historical JSON is rewritten. Future formula changes require an explicit migration policy. Hunger/sleep scoring dimensions and parameter learning remain outside this implementation. State evolution is outside Valence's responsibility. Remote authentication and multi-user permissions are outside this local application's scope.
