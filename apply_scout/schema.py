"""Shared structured research contract for both providers."""


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


STRING = {"type": "string"}
STRINGS = {"type": "array", "items": STRING}
REQUIREMENT = obj({"requirement": STRING, "evidence": STRING, "assessment": STRING, "source_url": STRING})
JOB = obj({
    "company": STRING, "role": STRING, "url": STRING, "checked_at": STRING,
    "deadline_kind": {"type": "string", "enum": ["dated", "rolling", "unspecified", "unknown"]},
    "deadline": {"type": ["string", "null"]}, "deadline_note": STRING,
    "closed": {"type": "boolean"},
    "match": {"type": "string", "enum": ["높음", "보통", "낮음", "판단 보류"]},
    "summary": STRING, "requirements": {"type": "array", "items": REQUIREMENT},
    "gaps": STRINGS, "actions": STRINGS,
})
SCHEMA = obj({
    "searched_at": STRING,
    "jobs": {"type": "array", "items": JOB},
    "sources": {"type": "array", "items": obj({
        "url": STRING, "status": {"type": "string", "enum": ["checked", "blocked", "failed"]}, "note": STRING,
    })},
})
