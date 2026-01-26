import asyncio
import logging
import time
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())


# Link to project root
sys.path.append(os.getcwd())

from saga.adapters.sglang_adapter import SGLangAdapter
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Benchmark")

def benchmark():
    # Default from saga/config.py
    default_url = "http://localhost:8082/v1/chat/completions"
    url = os.getenv("SAGA_SGLANG_URL") or os.getenv("SGLANG_BASE_URL", default_url)
    
    # Ensure full endpoint if base url is provided
    if not url.endswith("/v1/chat/completions"):
        url = url.rstrip("/") + "/v1/chat/completions"

    timeout = int(os.getenv("SGLANG_TIMEOUT", "300"))
    api_key = os.getenv("SGLANG_API_KEY", "")
    
    logger.info(f"Connecting to SGLang at {url} with timeout {timeout}s")
    
    adapter = SGLangAdapter(url, api_key=api_key)
    adapter.timeout = timeout
    
    print("-" * 50)
    print("Test 1: Simple Probe (Warmup)")
    start = time.time()
    try:
        # Chat completion format
        res = adapter.call("Hello, are you there?", max_tokens=10)
        end = time.time()
        print(f"Status: Success")
        print(f"Response: {res}")
        print(f"Time: {end - start:.4f}s")
    except Exception as e:
        print(f"Status: Failed - {e}")

    print("-" * 50)
    print("Test 2: Complex Math Prompt (Simulation)")
    prompt_content = """You are a Mathematical Reasoning Agent.
Find a python formula `y = f(x)` that fits the following dataset: [(-2, -4), (-1, -4), (0, -2), (1, 2), (2, 8)]
Please provide 5 candidate formulas in the format `y = ...`.
"""
    start = time.time()
    try:
        res = adapter.call(prompt_content, max_tokens=500, temperature=0.6)
        end = time.time()
        print(f"Status: Success")
        print(f"Time: {end - start:.4f}s")
        # print(f"Response snippet: {str(res)[:100]}...")
    except Exception as e:
        print(f"Status: Failed - {e}")
    print("-" * 50)

if __name__ == "__main__":
    benchmark()
