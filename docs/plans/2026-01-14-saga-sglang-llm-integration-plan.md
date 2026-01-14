# SAGA LLM Integration (Analyzer/Planner/Implementer) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 將 SGLang 真實接入 Analyzer / Planner / Implementer，使用嚴格 JSON 輸出，並保持 outer/inner loop 解耦。

**Architecture:** 新增 LLM prompt 與 JSON schema 驗證層，提供三個節點的 LLM 版本實作；Runner 依 config 切換本地預設模組或 LLM 模組。

**Tech Stack:** Python 3.10+, FastAPI client (urllib), jsonschema（若要引入），pytest

---

### Task 1: 定義 LLM 節點輸出 JSON Schema 與 parser

**Files:**
- Create: `saga/llm/schema.py`
- Create: `saga/llm/parser.py`
- Test: `tests/test_llm_parser.py`

**Step 1: Write the failing test**

```python
# tests/test_llm_parser.py
from saga.llm.parser import parse_analyzer_output

def test_parse_analyzer_output():
    raw = '{"issues":["low_coverage"],"summary":"coverage low"}'
    data = parse_analyzer_output(raw)
    assert "issues" in data
```

**Step 2: Run test to verify it fails**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_llm_parser.py::test_parse_analyzer_output -v`  
Expected: FAIL (ImportError)

**Step 3: Write minimal implementation**

```python
# saga/llm/schema.py
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
```

```python
# saga/llm/parser.py
import json
from saga.llm import schema

def parse_analyzer_output(raw: str):
    return json.loads(raw)
```

**Step 4: Run test to verify it passes**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_llm_parser.py::test_parse_analyzer_output -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/llm/schema.py saga/llm/parser.py tests/test_llm_parser.py
git commit -m "feat: add llm output schemas and parser"
```

---

### Task 2: LLM Prompt Templates

**Files:**
- Create: `saga/llm/prompts.py`
- Test: `tests/test_llm_prompts.py`

**Step 1: Write the failing test**

```python
# tests/test_llm_prompts.py
from saga.llm.prompts import analyzer_prompt

def test_analyzer_prompt_contains_schema():
    p = analyzer_prompt("text", ["k1"])
    assert "issues" in p
```

**Step 2: Run test to verify it fails**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_llm_prompts.py::test_analyzer_prompt_contains_schema -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# saga/llm/prompts.py
from saga.llm.schema import ANALYZER_SCHEMA, PLANNER_SCHEMA, IMPLEMENTER_SCHEMA

def analyzer_prompt(text: str, keywords: list[str]) -> str:
    return f"Return JSON: {ANALYZER_SCHEMA}\\nText: {text}\\nKeywords: {keywords}"
```

**Step 4: Run test to verify it passes**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_llm_prompts.py::test_analyzer_prompt_contains_schema -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/llm/prompts.py tests/test_llm_prompts.py
git commit -m "feat: add llm prompts"
```

---

### Task 3: LLM 模組實作（Analyzer/Planner/Implementer）

**Files:**
- Create: `saga/modules/llm.py`
- Modify: `saga/runner.py`
- Test: `tests/test_llm_modules.py`

**Step 1: Write the failing test**

```python
# tests/test_llm_modules.py
from saga.modules.llm import LLMAnalyzer

def test_llm_analyzer_returns_dict():
    a = LLMAnalyzer(None)
    assert isinstance(a._dummy_response(), dict)
```

**Step 2: Run test to verify it fails**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_llm_modules.py::test_llm_analyzer_returns_dict -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# saga/modules/llm.py
from saga.modules.base import Module
from saga.llm.prompts import analyzer_prompt

class LLMAnalyzer(Module):
    def __init__(self, client):
        self.client = client
    def _dummy_response(self):
        return {"issues": ["low_coverage"], "summary": "stub"}
    def run(self, state):
        return self._dummy_response()
```

**Step 4: Run test to verify it passes**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_llm_modules.py::test_llm_analyzer_returns_dict -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/modules/llm.py saga/runner.py tests/test_llm_modules.py
git commit -m "feat: add llm modules"
```

---

### Task 4: Config 切換與 SGLang 調用

**Files:**
- Modify: `saga/config.py`
- Modify: `saga/adapters/sglang_adapter.py`
- Modify: `saga/runner.py`
- Test: `tests/test_llm_integration_flag.py`

**Step 1: Write the failing test**

```python
# tests/test_llm_integration_flag.py
from saga.config import SagaConfig

def test_config_has_llm_flag():
    cfg = SagaConfig()
    assert hasattr(cfg, "use_llm_modules")
```

**Step 2: Run test to verify it fails**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_llm_integration_flag.py::test_config_has_llm_flag -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

Add `use_llm_modules` and wiring in runner.

**Step 4: Run test to verify it passes**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/test_llm_integration_flag.py::test_config_has_llm_flag -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/config.py saga/adapters/sglang_adapter.py saga/runner.py tests/test_llm_integration_flag.py
git commit -m "feat: wire llm modules and config flags"
```

---

### Task 5: README 更新

**Files:**
- Modify: `README.md`

**Step 1: Update docs**
- 新增 LLM 節點開關與 JSON schema 說明

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add llm module usage"
```

---

Plan complete and saved to `docs/plans/2026-01-14-saga-sglang-llm-integration-plan.md`. Two execution options:

1. Subagent-Driven (this session)
2. Parallel Session (separate)

Which approach?
