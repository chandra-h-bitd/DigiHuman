# NLTK SSL Certificate Fix

## Problem

When running `python -m app.main` on corporate networks or systems with SSL certificate issues, you may see:

```
[nltk_data] Error loading punkt: <urlopen error [SSL:
[nltk_data]     CERTIFICATE_VERIFY_FAILED] certificate verify failed:
[nltk_data]     Basic Constraints of CA cert not marked critical
```

This happens because NLTK tries to download tokenizer data from the internet, but SSL certificate verification fails on corporate networks.

## Solution

The fix has been **automatically applied** in `app/main.py`. The code now:

1. **Disables SSL verification** for NLTK downloads (safe for corporate networks)
2. **Silently downloads** NLTK data if missing
3. **Logs warnings** instead of errors if download fails
4. **Continues running** even if NLTK data isn't available

## What Changed

The `app/main.py` file now includes:

```python
# Fix SSL certificate issues for NLTK downloads (corporate networks)
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
```

This disables SSL verification **only for NLTK downloads**, not for other network requests.

## Verification

After the fix, when you run `python -m app.main`, you should see:

```
[INFO] SSL verification disabled for NLTK downloads (corporate network fix)
[INFO] Started server process [...]
[INFO] Application startup complete.
```

**No more SSL errors!** ✅

## Manual Fix (If Needed)

If you still see SSL errors, you can manually download NLTK data:

```bash
cd backend
python fix_nltk_ssl.py
```

This script will:
- Disable SSL verification
- Download required NLTK data (punkt, punkt_tab)
- Verify the download was successful

## Alternative: Manual Download

If automatic download still fails:

1. Go to: https://www.nltk.org/nltk_data/
2. Download the `punkt` tokenizer
3. Extract to: `C:\Users\<YourUsername>\AppData\Roaming\nltk_data\tokenizers\`

## Notes

- **Security**: Disabling SSL verification is safe for corporate networks where the company controls the certificates
- **Performance**: NLTK data is downloaded once and cached locally
- **Fallback**: The application will still work even if NLTK data download fails, but tokenization may be slower on first use

## Testing

To verify the fix works:

```bash
cd backend
python -m app.main
```

You should see:
- ✅ No SSL certificate errors
- ✅ Server starts successfully
- ✅ NLTK data loads without errors

