"""
gmxFlow License Validation
Workshop exclusive access system.
"""

import os
import hashlib
import json
from pathlib import Path

# License file location (in user's home directory)
LICENSE_FILE = Path.home() / ".gmxflow_license"

# ==============================================
# WORKSHOP KEY CONFIGURATION
# ==============================================

# List of valid workshop key hashes (SHA256)
# Keys are format: GMX-WS26-XXXX
VALID_KEY_HASHES = [
    "00b1ac0b1e505c69efa4dc87a07dcfd440ee9bada43a9699836d24e16fe62a28",
    "4d00a0bf2a0521ef3f481ec91d6c29e335682802cff33c9059814f108277595d",
    "4bc4ed8378b62f6736d0eb39adbe60faed387af71003002261f039a4ff8c0900",
    "8b08467808f124d5f03230f1885c03cdf188a678fbc91a42824e6c8c768164e0",
    "102c02e55a5cb89f2b669a62feb88d9b779783a04a14407b1f3e8add44a3dc9b",
    "7bf65b27ac23ece9e291ce38ce6eb264ae3145aaa07577e216bbed4eb1272438",
    "6c6118a8df7844fb039fcd9ae2d45a760522dbd9d2626aebf3a503a03875fa14",
    "ef053c95378c4fca1ee40d258377907bef2072af245e1f95ee05591895151498",
    "950b8f65a5fd13249477b61b5129d9fbe0dd37e5c6846c8336c7b1fa61ff1003",
    "bbe98deb6041c43e11825ddf6f520f49b8e9cca459208b525f0bb9b0e47e79f1",
    "8a322de8de4a8e8b83881b321fbe1457a1f7ff953824b5b396d3167c90409d70",
    "8080dbebd94be436245d256744a2a75ed3e4fcea1826df3ec95d7fa512ad58ac",
    "1188dcb485888bdb908c114f8d3d193e128fc7a11b6e467009396ab2de93d300",
    "74ea1e0b194c14bec46b30b5e65d2b19ee870d64394552897a9e0c5001582dae",
    "9278126e65acc128d99688e5cbd718c41a5c710ec4bcc047cc326a85cbe3bbae",
    "b40c7667d4784de606f453b51979092113f466a7be2cba963e2e8991c84ccb66",
    "4992f355f9f46c3ad97e8f8f3c3c15eaee6f5d250796571e58c96b5170725719",
    "6a9e6ed12030805be18e320d870f25629a1b38f8f87e9d1d5f014e2561334061",
    "7dcb5a4a4dd604e27e3bce144b116d7ad6399dfbcee3f1e26e10014615728ad0",
    "0705a916a64c8e5459ba3d6af052f29e773c548e6f711276657fc8effd0a863b",
]

# Your master key hash (key: "GMXFLOW_MASTER_2026_SAGAR")  
MASTER_KEY_HASH = "e3d13db46a321e1fac6ef58588733e6cd6e2dbef6e3e7db7d47379ce8b5fd815"

# ==============================================


def hash_key(key: str) -> str:
    """Hash a license key using SHA256."""
    return hashlib.sha256(key.strip().upper().encode()).hexdigest()


def validate_key(key: str) -> bool:
    """Check if a key is valid."""
    key_hash = hash_key(key)
    return key_hash == MASTER_KEY_HASH or key_hash in VALID_KEY_HASHES


def is_licensed() -> bool:
    """Check if current installation is licensed."""
    if LICENSE_FILE.exists():
        try:
            with open(LICENSE_FILE, 'r') as f:
                data = json.load(f)
                return data.get("activated", False) == True
        except:
            pass
    return False


def save_license(key: str) -> bool:
    """Save a valid license."""
    if validate_key(key):
        try:
            with open(LICENSE_FILE, 'w') as f:
                json.dump({"activated": True, "version": "2026.0.1"}, f)
            return True
        except:
            pass
    return False


def prompt_for_license() -> bool:
    """Prompt user for license key."""
    print("\n" + "=" * 55)
    print("  gmxFlow - Workshop Exclusive Access")
    print("=" * 55)
    print("\n  This software requires a license key.")
    print("  If you attended a gmxFlow workshop, you received")
    print("  your unique access key during the session.\n")
    
    for attempt in range(3):
        key = input("  Enter license key: ").strip()
        
        if validate_key(key):
            if save_license(key):
                print("\n  ✓ License activated successfully!")
                print("    You now have lifetime access to gmxFlow.\n")
                return True
            else:
                print("  ✗ Failed to save license. Check permissions.")
        else:
            remaining = 2 - attempt
            if remaining > 0:
                print(f"  ✗ Invalid key. {remaining} attempts remaining.\n")
            else:
                print("\n  ✗ Too many failed attempts.")
                print("    Contact workshop organizer for assistance.\n")
    
    return False


def check_license() -> bool:
    """Main license check - call at app startup."""
    if is_licensed():
        return True
    return prompt_for_license()


# ==============================================
# KEY GENERATION UTILITY (For your use only)
# ==============================================

if __name__ == "__main__":
    print("\n=== gmxFlow Key Generator ===\n")
    print("Enter a key to see its hash:\n")
    
    while True:
        key = input("Key (or 'quit'): ").strip()
        if key.lower() == 'quit':
            break
        
        h = hash_key(key)
        print(f"Hash: {h}\n")
        print("Copy this hash to VALID_KEY_HASHES in license_check.py\n")
