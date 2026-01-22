import os
import sys
import argparse
from pathlib import Path

def check_model_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-file-check", action="store_true", help="Skip checking if GGUF file exists")
    args = parser.parse_args()

    print("========================================")
    print(" SGLang Model Compatibility Check")
    print("========================================")

    model = os.getenv("SGLANG_MODEL", "")
    load_format = os.getenv("SGLANG_LOAD_FORMAT", "")
    quantization = os.getenv("SGLANG_QUANTIZATION", "")

    if not model:
        print("[ERROR] SGLANG_MODEL is not set.")
        sys.exit(1)

    print(f"Model Target: {model}")
    print(f"Load Format:  {load_format}")

    # Check for GGUF
    is_gguf_format = load_format.lower() == "gguf" or model.lower().endswith(".gguf")
    
    if is_gguf_format:
        print("[INFO] Detected GGUF configuration.")
        
        # Check if model is a local path
        if model.startswith("/") or model.startswith("."):
            model_path = Path(model)
            if args.skip_file_check:
                print(f"[INFO] Skipping file existence check for: {model}")
            elif not model_path.exists():
                print(f"[ERROR] GGUF file not found at: {model}")
                print("       Please ensure 'model_fetch' service has completed or check SGLANG_MODEL path.")
                sys.exit(1)
            else:
                print(f"[OK] GGUF file exists: {model} ({model_path.stat().st_size / (1024**3):.2f} GB)")
        else:
            # It's a repo-id?? SGLang usually expects local path for GGUF --model-path
            # If user passed a repo-id for GGUF, SGLang might fail or try to download implicitly if supported.
            # But usually for GGUF we want strict paths.
            print(f"[WARNING] SGLANG_MODEL looks like a Repo ID but format is GGUF. SGLang typically requires a local file path for --model-path when using GGUF.")
            
    else:
        # HuggingFace Model
        print(f"[INFO] Detected HuggingFace Model ID (or path).")
        # Check for known unsupported types (example)
        unsupported_keywords = ["mamba", "rwkv"] # SGLang specific support check? 
        # SGLang supports LLaMA, Mistral, Gemma, Qwen, DeepSeek, etc.
        # It does not support Mamba (SSM) yet (as of early 2025 maybe? It's v0.4+).
        # Assuming current version constraints.
        
        for kw in unsupported_keywords:
            if kw in model.lower():
                print(f"[WARNING] Model '{model}' might be architecture '{kw}' which may not be fully supported by SGLang.")
                
    # Check for compatibility logic
    # Real validation would require importing sglang, but we want a lightweight pre-check.
    
    print("[OK] basic configuration check passed.")
    sys.exit(0)

if __name__ == "__main__":
    check_model_config()
