"""
Fix NLTK SSL certificate issues for corporate networks
Run this script once to download NLTK data with SSL verification disabled
"""
import ssl
import nltk
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_nltk_ssl():
    """Disable SSL verification for NLTK downloads"""
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        logger.warning("SSL context creation not available")
        return False
    else:
        ssl._create_default_https_context = _create_unverified_https_context
        logger.info("SSL verification disabled for NLTK downloads")
        return True

def download_nltk_data():
    """Download required NLTK data"""
    logger.info("Downloading NLTK data...")
    
    # Fix SSL first
    if not fix_nltk_ssl():
        logger.error("Failed to fix SSL context")
        return False
    
    # Download punkt tokenizer
    try:
        logger.info("Downloading punkt tokenizer...")
        nltk.download('punkt', quiet=False)
        logger.info("[OK] punkt downloaded successfully")
    except Exception as e:
        logger.error(f"[FAIL] Failed to download punkt: {e}")
        return False
    
    # Download punkt_tab (optional, newer version)
    try:
        logger.info("Downloading punkt_tab tokenizer...")
        nltk.download('punkt_tab', quiet=False)
        logger.info("[OK] punkt_tab downloaded successfully")
    except Exception as e:
        logger.warning(f"[WARN] Failed to download punkt_tab (optional): {e}")
        # This is optional, so we continue
    
    logger.info("[OK] NLTK data download complete!")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("NLTK SSL Fix & Data Download")
    print("=" * 60)
    print()
    
    if download_nltk_data():
        print("\n[OK] Success! NLTK data is now available.")
        print("You can now run 'python -m app.main' without SSL errors.")
    else:
        print("\n[FAIL] Failed to download NLTK data.")
        print("The application may still work, but tokenization may be slower.")
        print("\nAlternative: Download NLTK data manually:")
        print("1. Go to: https://www.nltk.org/nltk_data/")
        print("2. Download 'punkt' tokenizer")
        print("3. Extract to: ~/nltk_data/tokenizers/")

