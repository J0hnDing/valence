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
