
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Load .env explicitly
load_dotenv()

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
    config = SagaConfig()
    
    # 2. Parse arguments (Minimal implementation)
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        # Default scenario
        dataset_str = "[(-2, -4), (-1, -4), (0, -2), (1, 2), (2, 8)]"
        keywords = ["symbolic_regression", "formula", "equation"]
    else:
        print("Usage: python saga_cli.py run")
        return

    print(f"--- SAGA CLI ---")
    
    runner = SagaRunner(config)
    print(f"Generator: {runner.generator.get_name()}")
    
    print("\n[Starting Run]...")
    async for event in runner.run(dataset_str, keywords, mode="autopilot"):
        if isinstance(event, LogEvent):
            if event.level == "llm":
                print(f"[LLM] {event.message}")
            else:
                print(f"[{event.level.upper()}] {event.message}")
        
        if isinstance(event, IterationResult):
            print(f"\n>>> Iteration {event.iteration} Best: {event.best_candidate} (Score: {event.best_score:.4f})")
            if event.best_score > 0.99:
                print("Convergence reached!")
                break

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
