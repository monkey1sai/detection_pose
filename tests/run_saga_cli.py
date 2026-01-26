
import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from saga.runner import SagaRunner
from saga.config import SagaConfig
from saga.outer_loop import LogEvent, IterationResult

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("SagaCLI")

async def main():
    # 1. Setup Config
    # Ensure SGLang URL is correct (defaulting to localhost:30000 or whatever is standard)
    # We'll use defaults or env vars
    config = SagaConfig()
    
    # Force LLM usage if not already set (assuming we want to test LLM)
    config.use_llm_modules = True
    config.use_groq = True
    config.groq_api_key = os.getenv("GROQ_API_KEY") or ""
    config.groq_model = "llama-3.3-70b-versatile" # Use a fast model
    
    print(f"--- SAGA CLI TEST ---")
    print(f"Using Groq: {config.use_groq}")
    
    runner = SagaRunner(config)
    print(f"Generator: {runner.generator.get_name()}")
    
    # 2. Define Task
    # Data: y = x^2 + 3x - 2
    # Points: (-2, -4), (-1, -4), (0, -2), (1, 2), (2, 8)
    dataset_str = "[(-2, -4), (-1, -4), (0, -2), (1, 2), (2, 8)]"
    keywords = ["symbolic_regression", "formula", "equation"]
    
    overrides = {
        "inner_iterations": 1, # Minimal run
        "batch_size": 2,
        "max_iters": 1
    }

    print("\n[Starting Run]...")
    async for event in runner.run(dataset_str, keywords, mode="autopilot", config_overrides=overrides):
        if isinstance(event, LogEvent):
            if event.level == "llm":
                print(f"\n[BLUE LOG] {event.message}")
            else:
                # print(f"[{event.level.upper()}] {event.message}")
                pass
        
        if isinstance(event, IterationResult):
            print(f"\n>>> Iteration {event.iteration} Best: {event.best_candidate} (Score: {event.best_score:.4f})")
            if event.best_score > 0.99:
                print("Convergence reached!")
                break

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
