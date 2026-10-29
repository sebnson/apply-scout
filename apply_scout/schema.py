"""Shared dictionary contracts; no third-party schema runtime is required."""

MATCHES = ("높음", "보통", "낮음", "판단 보류")
DEADLINES = ("dated", "rolling", "unspecified", "unknown")
IMPORTANCES = ("required", "preferred", "responsibility", "unknown")
ASSESSMENTS = ("met", "partial", "unmet", "unknown")
SOURCE_STATUSES = ("checked", "blocked", "failed")


def enum(values):
    return {"type": "string", "enum": list(values)}


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


STRING = {"type": "string", "minLength": 1}
STRINGS = {"type": "array", "items": STRING}
REQUIREMENT = obj({"requirement": STRING, "evidence": STRING, "assessment": STRING, "source_url": STRING})
JOB = obj({
    "company": STRING, "role": STRING, "url": STRING, "checked_at": STRING,
    "deadline_kind": enum(DEADLINES),
    "deadline": {"type": ["string", "null"]}, "deadline_note": STRING,
    "closed": {"type": "boolean"},
    "match": enum(MATCHES),
    "summary": STRING, "requirements": {"type": "array", "items": REQUIREMENT},
    "gaps": STRINGS, "actions": STRINGS,
})
V1_SCHEMA = obj({
    "searched_at": STRING,
    "jobs": {"type": "array", "items": JOB},
    "sources": {"type": "array", "items": obj({
        "url": STRING, "status": enum(SOURCE_STATUSES), "note": STRING,
    })},
})

V2_REQUIREMENT = obj({
    "requirement": STRING,
    "importance": enum(IMPORTANCES),
    "assessment": enum(ASSESSMENTS),
    "job_evidence": obj({"source_url": STRING, "detail": STRING}),
    "profile_evidence": {"type": "array", "items": obj({
        "file": STRING, "section": STRING, "detail": STRING,
    })},
    "rationale": STRING,
})
V2_JOB = obj({**JOB["properties"],
    "requirements": {"type": "array", "items": V2_REQUIREMENT},
    "official_source_urls": STRINGS,
})
V2_SCHEMA = obj({
    "schema_version": enum(("2",)),
    "run": obj({"agent": STRING, "instruction_hash": STRING, "input_files": STRINGS}),
    "searched_at": STRING,
    "jobs": {"type": "array", "items": V2_JOB},
    "sources": V1_SCHEMA["properties"]["sources"],
})

# Switch provider output only when the v2 reader and renderer are available.
SCHEMA = V1_SCHEMA


def validate_structure(value, schema=V2_SCHEMA, path="$"):
    """Validate only the JSON Schema keywords used by our closed contracts.

    This is not a general JSON Schema implementation. Cross-field and evidence
    rules belong to the consistency validator.
    """
    types = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
    allowed = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    if not any(type(value) is types[kind] for kind in allowed):
        raise ValueError(f"{path}: expected {' or '.join(allowed)}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: choose one of {schema['enum']}")
    if isinstance(value, str) and schema.get("minLength") and not value.strip():
        raise ValueError(f"{path}: provide a non-empty string")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError(f"{path}.{key}: required field is missing")
        for key, item in value.items():
            if key not in schema["properties"]:
                if schema.get("additionalProperties") is False:
                    raise ValueError(f"{path}.{key}: remove unsupported field")
            else:
                validate_structure(item, schema["properties"][key], f"{path}.{key}")
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_structure(item, schema["items"], f"{path}[{index}]")
    return value
