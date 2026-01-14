from __future__ import annotations

from typing import Any, Dict

from saga.adapters.sglang_adapter import SGLangAdapter
from saga.llm.parser import parse_analyzer_output, parse_implementer_output, parse_planner_output
from saga.llm.prompts import analyzer_prompt, implementer_prompt, planner_prompt
from saga.modules.base import Module


class LLMAnalyzer(Module):
    """Analyzer module backed by SGLang."""

    def __init__(self, client: SGLangAdapter):
        self.client = client

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = analyzer_prompt(state.get("text", ""), state.get("keywords", []))
        raw = self.client.call(prompt)["choices"][0]["message"]["content"]
        return parse_analyzer_output(raw)


class LLMPlanner(Module):
    """Planner module backed by SGLang."""

    def __init__(self, client: SGLangAdapter):
        self.client = client

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = planner_prompt(state.get("analysis", {}))
        raw = self.client.call(prompt)["choices"][0]["message"]["content"]
        return parse_planner_output(raw)


class LLMImplementer(Module):
    """Implementer module backed by SGLang."""

    def __init__(self, client: SGLangAdapter):
        self.client = client

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = implementer_prompt(state.get("plan", {}))
        raw = self.client.call(prompt)["choices"][0]["message"]["content"]
        return parse_implementer_output(raw)
