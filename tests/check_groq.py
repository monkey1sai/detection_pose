
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

try:
    from saga.adapters.groq_adapter import GroqAdapter
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

try:
    api_key = os.getenv("GROQ_API_KEY") or ""
    adapter = GroqAdapter(api_key=api_key, model="llama-3.3-70b-versatile")
    print("Initialization successful")
    
    # Try a call?
    # res = adapter.call("Hello")
    # print(res)
except Exception as e:
    print(f"Initialization failed: {e}")
    import traceback
    traceback.print_exc()
