import sys
import os
import argparse
import asyncio
import time
import json
import aiohttp
import statistics
import random
import threading
import subprocess
from typing import List, Dict, Any

# Force UTF-8 output for Windows console
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

print("Starting Final Benchmark Script...", flush=True)

def load_env_file(filepath):
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    except:
        pass

load_env_file('.env')

VLLM_URL = "http://localhost:8082/v1/chat/completions"
API_KEY = os.getenv("VLLM_API_KEY", "your-secure-api-key-here")
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

class SystemMonitor:
    def __init__(self, interval=0.5):
        self.interval = interval
        self.running = False
        self.gpu_stats = []
        self.vram_stats = []
        self.thread = None

    def get_gpu_stats(self):
        try:
            cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits"
            output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            util, mem = output.split(',')
            return float(util), float(mem)
        except:
            return 0.0, 0.0

    def _monitor_loop(self):
        while self.running:
            gpu_util, gpu_mem = self.get_gpu_stats()
            self.gpu_stats.append(gpu_util)
            self.vram_stats.append(gpu_mem)
            time.sleep(self.interval)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def report(self):
        if not self.gpu_stats: return "No GPU data."
        return (f"    GPU Util: Avg {statistics.mean(self.gpu_stats):.1f}% | Max {max(self.gpu_stats):.1f}%\n"
                f"    GPU VRAM: Avg {statistics.mean(self.vram_stats):.0f} MB | Max {max(self.vram_stats):.0f} MB")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "process_ecommerce_order",
            "description": "Complex order tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "customer": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "vip": {"type": "string", "enum": ["std", "gold"]}
                        }
                    },
                    "items": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "qty": {"type": "integer"}}}}
                },
                "required": ["order_id", "customer", "items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_logs",
            "description": "Log tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "cluster": {"type": "string"},
                    "range": {"type": "object", "properties": {"s": {"type": "string"}, "e": {"type": "string"}}}
                },
                "required": ["cluster", "range"]
            }
        }
    }
]

def generate_request(idx):
    scenarios = [
        (f"Order #{idx} for customer VIP-123. 2 laptops and 1 mouse.", "process_ecommerce_order"),
        (f"Logs for Alpha cluster from 10am to 11am today.", "analyze_logs")
    ]
    return random.choice(scenarios)

async def make_request(session, req_id):
    prompt, _ = generate_request(req_id)
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": "You are an assistant. Use tools."}, {"role": "user", "content": prompt}],
        "tools": TOOLS,
        "stream": True
    }
    
    start = time.perf_counter()
    ttft = None
    output = ""
    tokens = 0
    
    try:
        async with session.post(VLLM_URL, json=payload, headers={"Authorization": f"Bearer {API_KEY}"}) as resp:
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith("data: ") and line != "data: [DONE]":
                    if ttft is None: ttft = time.perf_counter()
                    try:
                        delta = json.loads(line[6:])["choices"][0]["delta"]
                        if "tool_calls" in delta:
                            for tc in delta["tool_calls"]:
                                if "function" in tc:
                                    args = tc["function"].get("arguments", "")
                                    output += args
                                    tokens += len(args) / 4
                        if "content" in delta and delta["content"]:
                            output += delta["content"]
                            tokens += len(delta["content"]) / 4
                    except:
                        pass
    except Exception as e:
        print(f"Error: {e}")
        
    end = time.perf_counter()
    print(f"[{req_id}] In: {prompt[:40]}... | Out: {output[:50]}...", flush=True)
    return {"ttft": (ttft-start) if ttft else (end-start), "total": end-start, "tokens": max(1, tokens)}

async def run(concurrency, total):
    print(f"Running {total} requests ({concurrency} conc)...", flush=True)
    monitor = SystemMonitor()
    monitor.start()
    
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.perf_counter()
        for i in range(total):
            async def worker(idx):
                async with sem: return await make_request(session, idx)
            tasks.append(worker(i))
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
    
    monitor.stop()
    valid = [r for r in results if "error" not in r]
    duration = end_time - start_time
    
    print("\n" + "="*50)
    print("REPORT")
    print("="*50)
    print(f"Avg TTFT: {statistics.mean(r['ttft'] for r in valid):.4f}s")
    print(f"Avg Total: {statistics.mean(r['total'] for r in valid):.4f}s")
    print(f"System RPS: {len(valid)/duration:.2f} req/s")
    print(f"System TPS: {sum(r['tokens'] for r in valid)/duration:.2f} tokens/s")
    print("-"*50)
    print("RESOURCES")
    print(monitor.report())
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--total", type=int, default=20)
    args = parser.parse_args()
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run(args.concurrency, args.total))
