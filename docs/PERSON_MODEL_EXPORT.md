# Person Model version export

In Person Model, select a saved version and choose **Export selected version**.
Valence downloads a UTF-8 JSON attachment with a version-specific `.valence.json`
filename. The file contains the selected persisted version, including full numeric
precision. Unsaved editor changes are excluded; save them as a new version first.

The fixed interchange contract is [person-model-export.schema.json](person-model-export.schema.json),
JSON Schema draft 2020-12. The envelope is `format: "valence.person-model"`,
`schema_version: 1`, and `model_contract_version: "7"`. Source metadata identifies
the person and exact saved version; `person_name` is the current person name at
export time. `model` contains all feature responses, transient parameters,
aftereffects, resources, and homeostatic need ranges and weights.

Every field and canonical feature, aftereffect, and need key is required. Unknown
properties, incorrect response families, strings or booleans used as numbers,
non-finite numbers, and out-of-bound values are rejected. Consumers must also
reject duplicate JSON object keys and enforce the cross-field rule
`0 < lower <= upper < 1` for each homeostatic need. JSON Schema expresses the
individual bounds; the comparison between lower and upper requires an additional
semantic check. Consumers must validate before making any changes and copy the
supplied values without defaults, coercion, inference, or rounding.
Integer numeric values must be exactly representable in IEEE-754 double precision;
export rejects stored integers that would change when read as a JavaScript number.
Source model version numbers are limited to the safe integer range.
Model numbers preserve the stored IEEE-754 double-precision value. Integral
floating-point values are written as their exact decimal integer value rather
than a rounded scientific literal; fractional values use roundtrip JSON notation,
and signed zero is preserved. This changes notation without changing the stored
numeric value.

`GET /api/persons/{person_id}/model-versions/{version_id}/export` returns
`application/json` with an attachment filename. An unknown, deleted, or wrong-owner
version returns 404. A legacy, incomplete, or incompatible saved version returns
422 with instructions to review its current parameters and save a new version;
export never runs the legacy compatibility converter. Export does not mutate the
stored model. This file contains model parameters and preferred current-state
ranges, not a daily current-state measurement.
