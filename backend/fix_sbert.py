#!/usr/bin/env python3
"""
Fix script for SBERT/huggingface_hub compatibility issues
"""
import subprocess
import sys
import os

def fix_sbert_issue():
    """Fix the huggingface_hub compatibility issue"""
    print("🔧 Fixing SBERT/huggingface_hub compatibility issue...")
    
    try:
        # Upgrade huggingface_hub
        print("📥 Upgrading huggingface_hub...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "huggingface_hub"], check=True)
        
        # Also upgrade sentence-transformers to ensure compatibility
        print("📥 Upgrading sentence-transformers...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "sentence-transformers"], check=True)
        
        print("✅ SBERT compatibility issue fixed!")
        print("🚀 You can now restart your backend server")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to fix SBERT issue: {e}")
        print("💡 Try running manually:")
        print("   pip install --upgrade huggingface_hub sentence-transformers")
        return False
    
    return True

if __name__ == "__main__":
    fix_sbert_issue()
