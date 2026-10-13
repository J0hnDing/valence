"""Exact saved-version interchange. No compatibility conversion or defaults."""

from copy import deepcopy
import json
import math

from app.core.ontology import FEATURE_BY_KEY
from app.schemas.models import AFTEREFFECT_DEFAULTS, NEED_KEYS, PersonModel

FORMAT = "valence.person-model"
SCHEMA_VERSION = 1
MODEL_CONTRACT_VERSION = "7"


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def export_schema():
    """Publish the required-field variant of the computational contract."""
    schema = deepcopy(PersonModel.model_json_schema())

    def explicit(node):
        if isinstance(node, dict):
            node.pop("default", None)
            node.pop("title", None)
            if "properties" in node:
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            for value in node.values():
                explicit(value)
        elif isinstance(node, list):
            for value in node:
                explicit(value)

    explicit(schema)
    definitions = schema.pop("$defs")
    families = {"asymmetric_signed": "AsymmetricSigned", "cost": "Cost",
                "order_preference": "OrderPreference", "reward": "Reward",
                "reward_overload": "RewardOverload"}
    schema["properties"]["features"] = _object({
        key: {"$ref": f"#/$defs/{families[feature['response_family']]}"}
        for key, feature in FEATURE_BY_KEY.items()
    })
    schema["properties"]["aftereffects"] = _object({
        key: {"$ref": "#/$defs/AftereffectParameters"} for key in AFTEREFFECT_DEFAULTS
    })
    definitions["HomeostaticParameters"]["properties"]["needs"] = _object({
        key: {"$ref": "#/$defs/NeedParameters"} for key in NEED_KEYS
    })
    string = {"type": "string", "minLength": 1}
    result = _object({
        "format": {"const": FORMAT, "type": "string"},
        "schema_version": {"const": SCHEMA_VERSION, "type": "integer"},
        "model_contract_version": {"const": MODEL_CONTRACT_VERSION, "type": "string"},
        "source": _object({
            "person_id": string,
            "person_name": {**string, "maxLength": 200},
            "model_version_id": string,
            "model_version": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
            "model_created_at": string,
        }),
        "model": schema,
    })
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Valence Person Model export v1",
            "description": "UTF-8 .valence.json saved-version snapshot. Every field is required; no defaults or conversion. Additionally, each homeostasis need must satisfy lower <= upper, and integer numeric values must be exactly representable as IEEE-754 double precision.",
            **result, "$defs": definitions}


EXPORT_SCHEMA = export_schema()


def _serialize_exact(value, indent=0):
    """Write integral doubles as their exact integer value, avoiding exponent rounding."""
    if isinstance(value, dict):
        padding = " " * indent
        entries = [f'{padding}  {json.dumps(key, ensure_ascii=False)}: {_serialize_exact(child, indent + 2)}'
                   for key, child in value.items()]
        return "{\n" + ",\n".join(entries) + f"\n{padding}" + "}"
    if type(value) is float and value.is_integer() and value != 0:
        return str(int(value))
    # Keep signed zero and the standard shortest roundtrip for fractional doubles.
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _validate(value, schema, path):
    if "$ref" in schema:
        schema = EXPORT_SCHEMA["$defs"][schema["$ref"].rsplit("/", 1)[1]]
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be an object")
        properties = schema["properties"]
        if set(value) != set(properties):
            raise ValueError(f"{path} requires exactly {', '.join(properties)}")
        for key, child in properties.items():
            _validate(value[key], child, f"{path}.{key}")
    elif kind in ("number", "integer"):
        if type(value) not in (int, float) or (kind == "integer" and type(value) is not int):
            raise ValueError(f"{path} must be a {kind}")
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        if type(value) is int and int(float(value)) != value:
            raise ValueError(f"{path} cannot be represented exactly at double precision")
        for bound, invalid in (("minimum", lambda n: value < n),
                               ("maximum", lambda n: value > n),
                               ("exclusiveMinimum", lambda n: value <= n),
                               ("exclusiveMaximum", lambda n: value >= n)):
            if bound in schema and invalid(schema[bound]):
                raise ValueError(f"{path} violates {bound} {schema[bound]}")
    elif kind == "string":
        if not isinstance(value, str):
            raise ValueError(f"{path} must be a string")
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", math.inf):
            raise ValueError(f"{path} has invalid length")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path} must equal {schema['const']!r}")


def export_person_model(person, version):
    payload = {
        "format": FORMAT, "schema_version": SCHEMA_VERSION,
        "model_contract_version": MODEL_CONTRACT_VERSION,
        "source": {"person_id": person.id, "person_name": person.name,
                   "model_version_id": version.id, "model_version": version.version,
                   "model_created_at": version.created_at},
        "model": version.model,
    }
    _validate(payload, EXPORT_SCHEMA, "export")
    # The computational validator owns cross-field constraints such as lower <= upper.
    # Discard its result: only the unmodified persisted dictionary is serialized.
    PersonModel.model_validate(version.model, strict=True)
    return _serialize_exact(payload).encode("utf-8")
