#!/usr/bin/env python3
"""
Local LLM Installation Script
Downloads and installs the best available local LLM models for fallback
"""
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_models_dir() -> Path:
    """Get the models directory path"""
    script_dir = Path(__file__).parent
    models_dir = script_dir / "app" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir

def get_available_models() -> List[Dict]:
    """Get list of available GPT4All models"""
    try:
        from gpt4all import GPT4All
        return GPT4All.list_models()
    except ImportError:
        logger.error("GPT4All not installed. Please install it first: pip install gpt4all")
        return []

def select_best_models() -> List[Dict]:
    """Select the best models for different use cases"""
    models = get_available_models()
    if not models:
        return []
    
    # Define our preferred models in order of preference
    preferred_models = [
        # Best overall fast chat model (4GB RAM)
        "mistral-7b-openorca.gguf2.Q4_0.gguf",
        # Best instruction following model (4GB RAM)  
        "mistral-7b-instruct-v0.1.Q4_0.gguf",
        # Small but good model (2GB RAM)
        "orca-mini-3b-gguf2-q4_0.gguf",
        # Fast model with good quality (4GB RAM)
        "gpt4all-falcon-newbpe-q4_0.gguf"
    ]
    
    selected = []
    for model in models:
        if model['filename'] in preferred_models:
            selected.append(model)
    
    return selected

def download_model(model_info: Dict, models_dir: Path) -> bool:
    """Download a specific model"""
    filename = model_info['filename']
    model_path = models_dir / filename
    
    if model_path.exists():
        logger.info(f"✅ Model already exists: {filename}")
        return True
    
    try:
        logger.info(f"🔄 Downloading {model_info['name']} ({filename})...")
        logger.info(f"   Size: {int(model_info['filesize']) / (1024**3):.1f} GB")
        logger.info(f"   RAM Required: {model_info['ramrequired']} GB")
        
        from gpt4all import GPT4All
        
        # Download the model
        model = GPT4All(filename, model_path=str(models_dir))
        logger.info(f"✅ Successfully downloaded: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to download {filename}: {e}")
        return False

def install_local_llm_models():
    """Main installation function"""
    logger.info("🚀 Starting Local LLM Installation...")
    
    # Check if GPT4All is installed
    try:
        import gpt4all
        version = getattr(gpt4all, '__version__', 'unknown')
        logger.info(f"✅ GPT4All version: {version}")
    except ImportError:
        logger.error("❌ GPT4All not installed. Installing...")
        os.system(f"{sys.executable} -m pip install gpt4all")
        try:
            import gpt4all
            version = getattr(gpt4all, '__version__', 'unknown')
            logger.info(f"✅ GPT4All installed: {version}")
        except ImportError:
            logger.error("❌ Failed to install GPT4All")
            return False
    
    # Get models directory
    models_dir = get_models_dir()
    logger.info(f"📁 Models directory: {models_dir}")
    
    # Select best models
    selected_models = select_best_models()
    if not selected_models:
        logger.error("❌ No models available")
        return False
    
    logger.info(f"📋 Selected {len(selected_models)} models for installation:")
    for model in selected_models:
        logger.info(f"   - {model['name']} ({model['filename']})")
    
    # Download models
    success_count = 0
    for model in selected_models:
        if download_model(model, models_dir):
            success_count += 1
    
    logger.info(f"🎉 Installation complete! {success_count}/{len(selected_models)} models installed successfully")
    
    if success_count > 0:
        logger.info("✅ Local LLM fallback is now available!")
        logger.info("💡 The system will automatically use these models when cloud APIs are unavailable")
    else:
        logger.warning("⚠️ No models were installed. The system will use heuristic fallback only")
    
    return success_count > 0

def check_system_requirements():
    """Check if system meets requirements for local LLM"""
    import psutil
    
    # Check available RAM
    available_ram = psutil.virtual_memory().available / (1024**3)  # GB
    logger.info(f"💾 Available RAM: {available_ram:.1f} GB")
    
    if available_ram < 4:
        logger.warning("⚠️ Low RAM detected. Consider using smaller models or cloud APIs")
        return False
    
    # Check disk space
    models_dir = get_models_dir()
    disk_usage = psutil.disk_usage(str(models_dir.parent))
    free_space = disk_usage.free / (1024**3)  # GB
    logger.info(f"💿 Available disk space: {free_space:.1f} GB")
    
    if free_space < 10:
        logger.warning("⚠️ Low disk space. Models require ~10GB total")
        return False
    
    return True

if __name__ == "__main__":
    print("🤖 Local LLM Installation Script")
    print("=" * 50)
    
    # Check system requirements
    if not check_system_requirements():
        print("❌ System requirements not met. Continue anyway? (y/N): ", end="")
        if input().lower() != 'y':
            sys.exit(1)
    
    # Install models
    success = install_local_llm_models()
    
    if success:
        print("\n🎉 Local LLM installation completed successfully!")
        print("💡 Your system now has robust fallback capabilities")
    else:
        print("\n❌ Local LLM installation failed")
        print("💡 The system will still work with cloud APIs and heuristic fallback")
    
    sys.exit(0 if success else 1)
