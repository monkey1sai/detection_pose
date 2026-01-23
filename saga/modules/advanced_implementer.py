"""
Advanced Implementer module for SAGA automated code generation.

Generates Python scoring functions and tool integrations:
- Dynamic scoring code generation
- Tool call wrappers for external APIs
- Sandbox-safe code validation
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AdvancedImplementer:
    """Advanced implementer with automated code generation capabilities.
    
    Generates scoring functions based on planner specifications:
    1. Python scoring functions for each objective
    2. Tool call wrappers for external evaluators
    3. Composite scoring functions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Any = None):
        """Initialize implementer.
        
        Args:
            config: Configuration for code generation
            llm_client: Optional LLM client for AI-assisted code generation
        """
        self.config = config or {}
        self.llm_client = llm_client
        self.use_llm = self.config.get("use_llm", False) and llm_client is not None
        
        # Predefined scoring templates
        self.scoring_templates = {
            "length": self._length_scorer_template,
            "keyword": self._keyword_scorer_template,
            "similarity": self._similarity_scorer_template,
            "diversity": self._diversity_scorer_template,
        }
        
        logger.info(f"[AdvancedImplementer] Initialized with use_llm={self.use_llm}")
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate scoring code based on plan.
        
        Args:
            state: Contains plan info, constraints, objectives
            
        Returns:
            Dictionary with scoring_code, tools, and metadata
        """
        logger.info("[AdvancedImplementer] Generating implementation...")
        
        plan = state.get("plan", {})
        constraints = state.get("constraints", [])
        task = (state.get("task", "") or "").strip().lower()
        objectives = state.get("objectives", ["length", "keyword", "quality"])
        if not isinstance(objectives, list) or not objectives:
            objectives = ["length", "keyword", "quality"]
        
        # Generate scoring code
        if task == "symbolic_regression":
            scoring_code = self._symbolic_regression_scorer()
            is_valid, validation_msg = self._validate_code(scoring_code)
        elif self.use_llm:
            scoring_code = self._generate_with_llm(plan, constraints, objectives)
            is_valid, validation_msg = self._validate_code(scoring_code)
        else:
            scoring_code = self._generate_from_templates(objectives, constraints)
            is_valid, validation_msg = self._validate_code(scoring_code)
        
        if not is_valid:
            logger.warning(f"[AdvancedImplementer] Code validation failed: {validation_msg}")
            scoring_code = self._fallback_scorer()
        
        # Generate tool wrappers
        tools = self._generate_tools(plan)
        
        result = {
            "scoring_code": scoring_code,
            "tools": tools,
            "is_valid": is_valid,
            "validation_message": validation_msg,
            "objectives": objectives
        }
        
        logger.info(f"[AdvancedImplementer] Implementation complete, valid={is_valid}")
        return result

    def _symbolic_regression_scorer(self) -> str:
        """
        Generate a sandbox-safe scoring function for symbolic regression.

        Requirements:
        - No imports (sandbox blocks __import__)
        - No eval/exec (blocked by validator)
        - Uses `ast` injected by sandbox worker to parse expressions safely
        - Expects `context["dataset"]` = list[(x, y)]
        """
        return r'''
def score(text: str, context: dict) -> list:
    """
    Symbolic regression scoring.

    Returns [fit_score, validity_score, simplicity_score] in [0, 1].
    - fit_score: normalized MSE against dataset
    - validity_score: 1 if expression parses + evaluates on dataset, else 0
    - simplicity_score: shorter expressions score higher
    """
    expr = (text or "").strip()
    dataset = context.get("dataset", [])

    # 1) Quick character whitelist to prevent non-math junk.
    allowed = "0123456789xX+-*/(). _"
    ok_chars = True
    for ch in expr:
        if ch not in allowed:
            ok_chars = False
            break

    if (not expr) or (not ok_chars) or (not dataset):
        return [0.0, 0.0, 0.0]

    # 2) Safe AST evaluation (no eval).
    def _calc(node, x):
        if node.__class__ is ast.Expression:
            return _calc(node.body, x)
        if node.__class__ is ast.BinOp:
            left = _calc(node.left, x)
            right = _calc(node.right, x)
            op = node.op
            if op.__class__ is ast.Add:
                return left + right
            if op.__class__ is ast.Sub:
                return left - right
            if op.__class__ is ast.Mult:
                return left * right
            if op.__class__ is ast.Div:
                if right == 0:
                    return 1e9
                return left / right
            if op.__class__ is ast.Pow:
                return left ** right
            raise Exception("bad-op")
        if node.__class__ is ast.UnaryOp:
            v = _calc(node.operand, x)
            if node.op.__class__ is ast.USub:
                return -v
            if node.op.__class__ is ast.UAdd:
                return v
            raise Exception("bad-unary")
        if node.__class__ is ast.Name:
            if node.id == "x":
                return x
            raise Exception("bad-name")
        if node.__class__ is ast.Constant:
            return float(node.value)
        # Fallback for older AST nodes (e.g. ast.Num)
        try:
            return float(node.n)
        except:
            pass
        raise Exception("bad-node")

    try:
        tree = ast.parse(expr, mode="eval")
    except:
        return [0.0, 0.0, 0.0]

    # 3) Fit score (normalized MSE).
    n = len(dataset)
    ys = []
    i = 0
    while i < n:
        ys.append(float(dataset[i][1]))
        i += 1

    y_mean = sum(ys) / max(n, 1)
    var = 0.0
    i = 0
    while i < n:
        dy = ys[i] - y_mean
        var += dy * dy
        i += 1
    var = var / max(n, 1)

    sum_sq = 0.0
    i = 0
    while i < n:
        x = float(dataset[i][0])
        y_true = float(dataset[i][1])
        try:
            y_pred = float(_calc(tree, x))
        except:
            return [0.0, 0.0, 0.0]
        err = y_pred - y_true
        sum_sq += err * err
        i += 1

    mse = sum_sq / max(n, 1)
    mse_norm = mse / (var + 1e-9)
    fit_score = 1.0 - min(mse_norm, 1.0)
    fit_score = max(0.0, fit_score)

    # 4) Simplicity score
    simplicity_score = 1.0 - min(len(expr) / 50.0, 1.0)
    simplicity_score = max(0.0, simplicity_score)

    return [fit_score, 1.0, simplicity_score]
'''
    
    def _generate_from_templates(
        self, objectives: List[str], constraints: List[str]
    ) -> str:
        """Generate scoring code from predefined templates."""
        scorer_parts = []
        
        for i, obj in enumerate(objectives):
            template_func = self.scoring_templates.get(obj, self._generic_scorer_template)
            scorer_parts.append(template_func(i, obj))
        
        # Combine into single scoring function
        code = '''
def score(text: str, context: dict) -> list:
    """Score a candidate text on multiple objectives."""
    scores = []
    keywords = context.get("keywords", [])
    
'''
        for part in scorer_parts:
            code += f"    # Objective scoring\n    {part}\n\n"
        
        code += '''    return scores
'''
        return code
    
    def _generate_with_llm(
        self, plan: Dict, constraints: List[str], objectives: List[str]
    ) -> str:
        """Generate scoring code using LLM."""
        prompt = f"""Generate a Python scoring function for the following objectives:
Objectives: {objectives}
Constraints: {constraints}
Focus areas: {plan.get('focus_objectives', [])}

Requirements:
1. Function signature: def score(text: str, context: dict) -> list
2. Return a list of floats, one per objective, in range [0, 1]
3. Use only safe operations (no file I/O, network, imports)
4. Include docstring explaining each score dimension

Output only the Python code, no explanation."""
        
        try:
            response = self.llm_client.call(prompt)
            raw = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            # Extract code block if present
            if "```python" in raw:
                raw = raw.split("```python")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            return raw.strip()
        except Exception as e:
            logger.error(f"[AdvancedImplementer] LLM generation failed: {e}")
            return self._generate_from_templates(objectives, constraints)
    
    def _length_scorer_template(self, idx: int, name: str) -> str:
        """Template for length-based scoring."""
        return f'''# Score {idx}: {name}
    target_len = context.get("target_length", 50)
    len_score = 1.0 - min(abs(len(text) - target_len) / target_len, 1.0)
    scores.append(max(0.0, len_score))'''
    
    def _keyword_scorer_template(self, idx: int, name: str) -> str:
        """Template for keyword matching scoring."""
        return f'''# Score {idx}: {name}
    if keywords:
        matches = sum(1 for kw in keywords if kw.lower() in text.lower())
        kw_score = matches / len(keywords)
    else:
        kw_score = 1.0
    scores.append(kw_score)'''
    
    def _similarity_scorer_template(self, idx: int, name: str) -> str:
        """Template for similarity scoring."""
        return f'''# Score {idx}: {name}
    reference = context.get("reference", "")
    if reference:
        common = set(text.lower().split()) & set(reference.lower().split())
        sim_score = len(common) / max(len(set(text.lower().split())), 1)
    else:
        sim_score = 0.5
    scores.append(sim_score)'''
    
    def _diversity_scorer_template(self, idx: int, name: str) -> str:
        """Template for diversity scoring."""
        return f'''# Score {idx}: {name}
    words = text.split()
    if words:
        unique_ratio = len(set(words)) / len(words)
    else:
        unique_ratio = 0.0
    scores.append(unique_ratio)'''
    
    def _generic_scorer_template(self, idx: int, name: str) -> str:
        """Generic fallback scorer template."""
        return f'''# Score {idx}: {name}
    scores.append(0.5)  # Default score for {name}'''
    
    def _validate_code(self, code: str) -> tuple[bool, str]:
        """Validate generated code for safety and correctness."""
        # Check for forbidden operations
        forbidden = [
            "import os", "import sys", "import subprocess",
            "open(", "exec(", "eval(",
            "__import__", "globals", "locals",
            "file", "input("
        ]
        
        for pattern in forbidden:
            if pattern in code:
                return False, f"Forbidden pattern: {pattern}"
        
        # Try to compile
        try:
            compile(code, "<scoring>", "exec")
            return True, "OK"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
    
    def _fallback_scorer(self) -> str:
        """Return safe fallback scoring function."""
        return '''
def score(text: str, context: dict) -> list:
    """Fallback scorer with basic metrics."""
    keywords = context.get("keywords", [])
    
    # Length score
    len_score = min(len(text) / 100, 1.0)
    
    # Keyword score  
    if keywords:
        kw_score = sum(1 for kw in keywords if kw.lower() in text.lower()) / len(keywords)
    else:
        kw_score = 1.0
    
    # Quality score (basic)
    quality = 0.5
    
    return [len_score, kw_score, quality]
'''
    
    def _generate_tools(self, plan: Dict) -> List[Dict[str, Any]]:
        """Generate tool call definitions."""
        tools = []
        
        # Add basic tools
        tools.append({
            "name": "text_scorer",
            "description": "Score candidate text",
            "parameters": {
                "text": {"type": "string"},
                "context": {"type": "object"}
            }
        })
        
        # Add strategy-specific tools
        strategy = plan.get("strategy", "balance")
        if strategy == "exploration":
            tools.append({
                "name": "diversity_checker",
                "description": "Check diversity of candidates",
                "parameters": {
                    "candidates": {"type": "array"}
                }
            })
        
        return tools
