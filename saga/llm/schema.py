ANALYZER_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": ["issues", "summary"],
}

PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "weights": {"type": "array", "items": {"type": "number"}},
        "summary": {"type": "string"},
    },
    "required": ["weights", "summary"],
}

IMPLEMENTER_SCHEMA = {
    "type": "object",
    "properties": {
        "scoring_code": {"type": "string"},
        "version": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["scoring_code", "version", "summary"],
}
