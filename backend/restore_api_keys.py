"""
Script to check and optionally restore API keys
"""
import requests

BASE_URL = "http://localhost:8000"

print("\nChecking current API key status...")
response = requests.get(f"{BASE_URL}/config")
if response.status_code == 200:
    config = response.json()
    print(f"\nCurrent Configuration:")
    print(f"  Gemini API Key: {config.get('gemini_api_key', 'NOT SET')}")
    print(f"  ChatGPT API Key: {config.get('chatgpt_api_key', 'NOT SET')}")
    
    # Check if they are the invalid test keys
    gemini_key = config.get('gemini_api_key', '')
    chatgpt_key = config.get('chatgpt_api_key', '')
    
    if gemini_key == 'INVALID_TEST_KEY' or chatgpt_key == 'INVALID_TEST_KEY':
        print("\n[WARNING] Test keys detected!")
        print("Please restore your valid API keys using:")
        print("  1. The frontend Settings tab, OR")
        print("  2. Direct API call:")
        print(f'\n     import requests')
        print(f'     requests.post("{BASE_URL}/config", json={{')
        print(f'         "key_name": "gemini_api_key",')
        print(f'         "key_value": "YOUR_ACTUAL_GEMINI_KEY"')
        print(f'     }})')
    else:
        print("\n[OK] API keys look valid")
else:
    print(f"Could not retrieve config: {response.status_code}")

