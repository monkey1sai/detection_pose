import json
from typing import List

from saga.llm.schema import ANALYZER_SCHEMA, IMPLEMENTER_SCHEMA, PLANNER_SCHEMA


def _schema_block(schema: dict) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2)


def analyzer_prompt(text: str, keywords: List[str]) -> str:
    return (
        "你是 Analyzer。請嚴格輸出 JSON，符合以下 schema：\n"
        f"{_schema_block(ANALYZER_SCHEMA)}\n"
        "只輸出 JSON，不要其他文字。\n"
        f"Text: {text}\nKeywords: {keywords}\n"
    )


def planner_prompt(analysis: dict) -> str:
    return (
        "你是 Planner。請嚴格輸出 JSON，符合以下 schema：\n"
        f"{_schema_block(PLANNER_SCHEMA)}\n"
        "只輸出 JSON，不要其他文字。\n"
        f"Analysis: {json.dumps(analysis, ensure_ascii=False)}\n"
    )


def implementer_prompt(plan: dict) -> str:
    return (
        "你是 Implementer。請輸出 scoring_code 的 Python 內容，並嚴格輸出 JSON 符合 schema：\n"
        f"{_schema_block(IMPLEMENTER_SCHEMA)}\n"
        "只輸出 JSON，不要其他文字。\n"
        f"Plan: {json.dumps(plan, ensure_ascii=False)}\n"
    )
