import json
from typing import Any, Dict, List

from saga.llm import schema


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no-json")
    return raw[start : end + 1]


def _ensure_keys(data: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    for k in required:
        if k not in data:
            raise ValueError(f"missing:{k}")
    return data


def parse_analyzer_output(raw: str) -> Dict[str, Any]:
    data = json.loads(_extract_json(raw))
    return _ensure_keys(data, schema.ANALYZER_SCHEMA["required"])


def parse_planner_output(raw: str) -> Dict[str, Any]:
    data = json.loads(_extract_json(raw))
    return _ensure_keys(data, schema.PLANNER_SCHEMA["required"])


def parse_implementer_output(raw: str) -> Dict[str, Any]:
    data = json.loads(_extract_json(raw))
    return _ensure_keys(data, schema.IMPLEMENTER_SCHEMA["required"])
