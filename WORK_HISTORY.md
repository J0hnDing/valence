## 2026-10-06 22:54 — Implement complete deterministic Valence application

- Category: feature
- Area: full stack

### Summary

Implemented full Valence: pure Python deterministic 17-feature engine and all8 aftereffects, complete backend traces/248-node graphs, strict validation, SQLAlchemy SQLite immutable model versions and evaluation snapshots, FastAPI CRUD/history/reproduction/ontology/previews, six analytical React pages, editable78 model parameters,25 backend-sampled curves, optional DEMO seed, FEATURES.md, README, dependency locks and PowerShell startup scripts. Validation:108 backend tests and11 frontend tests pass; TypeScript and production build pass; live browser and single-server static/API smoke pass; npm audit0 vulnerabilities.

### Limitations

Experimental uncalibrated ontology and arbitrary utility units; manually specified models; no learning, uncertainty, opportunity cost or remote multi-user authentication, as specified. One upstream Starlette/httpx test deprecation warning.

## 2026-10-06 23:41 — Unify Person management and model version selection

- Category: feature
- Area: Person Model UI and API

### Summary

Unified person creation, selection, and metadata editing in Person Model. Added saved-version browsing with exact parameters and backend curves; editing any snapshot saves a new immutable latest version. Removed creation from Compare and made evaluations use the explicitly selected saved version. Added metadata and owned-version API routes, historical snapshot protections, README guidance, and regression coverage. Validated 117 backend tests, 14 frontend tests, TypeScript, production build, and live switching across existing v1/v2/v3 models with 25 curves and no browser errors.

### Limitations

none

## 2026-10-07 00:14 — Delete a person from Person Model

- Category: feature
- Area: Person lifecycle

### Summary

Added Delete person beside Edit person with explicit in-page confirmation, cancellation, busy controls, and honest error handling. Soft-deleted persons disappear from Person Model and Compare and cannot be used for person/model/state/new-evaluation operations; immutable saved evaluations remain readable and reproducible. Added an additive SQLite startup upgrade, selection fallback and last-person creation state, README documentation, and API/UI regression tests. Validated 120 backend tests and 17 frontend tests, type checking, production build, and live confirmation cancellation. Restored the demo person after an unexpected native-dialog deletion during verification; final UI uses explicit in-page confirmation.

### Limitations

Person deletion retains stored records for immutable history and does not purge the database.

## 2026-10-07 00:24 — Initialize people from defaults, exact model copies, or a comparative scenario quiz

- Category: feature
- Area: Person initialization

### Summary

Implemented three atomic person creation methods: defaults, exact saved source-version copy, and a backend-owned concrete comparative scenario quiz. Added 26 sections covering all 78 model parameters with quick choices, optional answers, bounded deterministic fits, explicit retained-default paths and mismatch warnings. Added answer/parameter review, navigation and in-memory draft preservation across pages. Existing metadata editing and immutable versions remain intact. Documented API, fitting assumptions and workflow. Validation: 147 backend tests and 28 frontend tests pass; TypeScript check and production build pass; live UI verified quiz start, quick choices, draft navigation and fit review; restarted backend and verified current endpoints.

### Limitations

Quiz parameters are editable self-report estimates within the existing fixed response families, not empirically calibrated measurements. Creation drafts survive page navigation only; refresh/close discards drafts, and raw answers are not persisted after creation.

## 2026-10-08 23:17 — Replace calibration quiz with an approachable personality-style questionnaire

- Category: bugfix
- Area: Person initialization

### Summary

Replaced the numeric calibration quiz with45 interleaved everyday statements, concrete examples and five agreement choices. Added automatic advance, Back/Skip, remaining progress, draft preservation, plain-language insights and optional answer/parameter review. Backend version3 strictly validates integer choices and maps weighted forward/reverse evidence into multiple parameters with independent positive/negative branches and conservative missing-data handling. Preserved default/exact-copy creation and atomic version1 initialization. Documented IPIP-inspired item style and heuristic limits; fixed slider/native validation for valid fractional encodings. Validation:174 backend tests,30 frontend tests, production build and live questionnaire/preview checks passed.

### Limitations

Custom scoring produces conservative editable starting estimates, not empirically validated personality or utility measurements; response curvatures retain defaults.

## 2026-10-08 23:45 — Limit numeric UI values to three decimal places

- Category: bugfix
- Area: Frontend numeric formatting

### Summary

Rounded all numeric displays to at most three decimal places, including model inputs and quiz summaries, charts, traces, nested graph values, stored-model previews, durations, horizons, and reference values. Numeric controls use 0.001 steps and round edited values; calculations and existing saved snapshots retain full precision. Added regression coverage for signed rounding, zero, input and slider edits, nested snapshots, and comparison/evaluation displays. All 34 frontend tests and the production build pass.

### Limitations

none

## 2026-10-09 01:01 — Resource utility costs and one-time outcomes

- Category: feature
- Area: Utility engine, Person Model, actions, evaluation traces

### Summary

Added editable time and money utility coefficients and required signed whole-action net money cost. Evaluation subtracts both resource costs at the end; utility per action-hour includes money cost and excludes time cost. Nine outcome features including goal progress are counted once, while ongoing experience remains duration-scaled. Added full cost and temporal traces/UI, zero-cost compatibility views and additive SQLite migration, immutable v1/v2 history preservation, and engine v3 reproduction. Updated caller documentation and generated reference. Validation: 202 backend tests, 38 frontend tests (serial with 20-second test timeout), TypeScript check, production build, and live UI/engine v3 checks passed.

### Limitations

Existing models start with zero resource coefficients; users must set them to activate costs. All monetary values use one consistent caller-declared currency without conversion. Historical v1/v2 evaluations remain readable but require their original engine for reproduction. Default parallel frontend execution hit three existing 5-second App-flow timeouts; the full suite passed with serial execution and a 20-second timeout.

## 2026-10-10 19:40 — Remove preference alignment from Valence

- Category: refactor
- Area: Ontology, engine, initialization quiz, frontend, compatibility, documentation

### Summary

Removed preference alignment from the canonical action and Person Model contracts, direct utility and regret trigger, quiz questions and scoring, UI, fixtures, seeds, and documentation. Valence now requires 15 feature values and provides a 43-question quiz; engine and quiz versions are 4. Read-only compatibility omits retired values, notes, and parameters from saved inputs while preserving immutable model versions and historical evaluation snapshots/traces. Existing v3 evaluations remain readable and require their original engine for reproduction. Atlas was not changed. Validation: 204 backend tests and 38 frontend tests passed; TypeScript check and production build passed; live API confirmed 15 features, quiz v4 with 43 questions, and successful previews of both existing saved model versions.

### Limitations

Historical v1/v2/v3 evaluations require their original engine version for exact reproduction; their saved traces remain available. Atlas schema changes are deferred at the user request.

## 2026-10-10 20:28 — Revise experience features and separate effort, rest, structure, and uncertainty

- Category: feature
- Area: Schema, utility engine, initialization, frontend

### Summary

Implemented the approved Valence ontology revision with 19 independent features. Split mental/physical effort from mental rest/relief and bodily pleasure; mental rest explicitly excludes enjoyment of thinking. Split structure/planning from outcome uncertainty and knowledge gained from curiosity engagement. Refined autonomy, intimacy, belonging, recognition, exercising influence, and specific personal principles. Added bounded optional actual exposure durations for ongoing features, persisted action timing, exposure traces/graph nodes, and exposure-aware fatigue. Updated engine and quiz to version 5, with 44 quiz statements and independent parameter evidence. Updated schema, examples, UI, generated reference, README and specification. Conservative read-only views preserve older stored model versions and history; current requests use only the new shape. Validation: 222 backend tests passed; final graph/exposure follow-up checks passed (103 tests); 46 frontend tests passed; TypeScript and production build passed. Live API and browser verified 19 fields, quiz5, existing model previews, independent parameters and conversion notices. Atlas unchanged.

### Limitations

Earlier combined encodings cannot recover simultaneous effort/pleasure, mental rest, curiosity engagement or independent structure/uncertainty precisely; converted inputs and parameters require review. Historical v1-v4 evaluations retain their saved traces and require the original engine for exact reproduction. Atlas synchronization is deferred at user request.

## 2026-10-11 00:04 — Need!!!!

- Category: feature
- Area: 1

### Summary

Implemented approved dynamic needs and current-state homeostasis in engine v6. Added strict bounded per-person need parameters and partial satisfaction state, deterministic mappings from the existing 19 features, quadratic deprivation/overload values and once-per-action need contributions with zero-exposure filtering. Replaced legacy energy behavior with the bounded modifier, preserving stress behavior and separating base, needs and energy totals, traces and graph nodes. Manual daily-state saving remains; evaluation never evolves state. Added explicit Unknown/Provided state controls, editable need parameters, read-only legacy projections, immutable historical snapshots and complete documentation. Validation: 259 backend tests, 50 frontend tests, TypeScript/production build and desktop/mobile live UI checks passed.

### Limitations

Need parameters are uncalibrated engineering defaults. Hunger/sleep, accumulation, recovery, relationship-specific state, learned parameters and richer inference are deferred in TODO-003. Historical v1-v5 evaluations remain readable and require their original engine for reproduction.

## 2026-10-12 21:59 — Export personal model, and input in the eidolon atlas.

- Category: feature
- Area: ..

### Summary

Implemented exact selected Person Model version export as a fixed-schema UTF-8 .valence.json file and Atlas import. Atlas encrypts the full model/source snapshot, copies all five need lower/upper bounds exactly in one transaction, locks bound ranges, preserves spectra/dynamics/history, and validates without defaults, legacy conversion, coercion, or inference. Shared schema copies match. Valence backend and export/frontend checks passed; 78 focused Atlas checks, producer-consumer precision test, and isolated desktop/mobile browser import passed.

### Limitations

Whole-suite gates retain unrelated existing failures in Atlas motivation/End fixtures and one stale Valence Evaluation text assertion. Running Atlas requires a restart to load the new backend route if an existing process remains active.

## 2026-10-12 21:37 — Add everyday starter action library

- Category: feature
- Area: Action library and optional seed

### Summary

Added and populated 12 editable everyday actions: eating, sleeping, League of Legends, study, walks, movies, projects, exercise, reading, cooking, chores, and friends. Added an explicit repeatable --standard-actions seed that preserves existing exact-title actions and creates no demo person, with scenario provenance and README instructions. API/starter tests passed (35 initially, final 2 starter integration tests passed after test cleanup); git diff --check passed; live API confirmed all 12 actions.

### Limitations

Feature values and durations are manually assigned starter assumptions; money costs default to zero. Hunger/sleep needs and subsequent energy recovery remain outside the current scoring contract. Renamed actions do not suppress recreating their original starter title.
