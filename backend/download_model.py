"""Quick script to download a small local LLM model for testing"""
import os
from pathlib import Path

print("Downloading small local LLM model for fallback testing...")
print("This will download ~2GB of data. Please wait...")

# Get models directory
models_dir = Path(__file__).parent / "app" / "models"
models_dir.mkdir(parents=True, exist_ok=True)

print(f"Models directory: {models_dir}")

try:
    from gpt4all import GPT4All
    
    # Download a small, fast model
    model_name = "orca-mini-3b-gguf2-q4_0.gguf"
    print(f"\nDownloading {model_name}...")
    print("This is a 2GB model optimized for speed and low memory usage")
    
    model = GPT4All(model_name, model_path=str(models_dir))
    
    print(f"\n[SUCCESS] Model downloaded successfully!")
    print(f"Location: {models_dir / model_name}")
    
    # Test the model
    print("\nTesting model...")
    response = model.generate("What is 2+2?", max_tokens=50)
    print(f"Test response: {response}")
    
    print("\n[OK] Local LLM is ready for use!")
    
except Exception as e:
    print(f"\n[ERROR] Failed to download model: {e}")
    print("\nThe system will continue to work with heuristic fallback")

