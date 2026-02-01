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
# The actual key is NOT stored here - only the hash
# This prevents people from reading the key from source code

# Workshop 2026 Key Hash (key: "GMXFLOW-WORKSHOP-2026")
WORKSHOP_KEY_HASH = "e3a624afe88878256da60955402f7f44e90bfdcb39b7b9ae3aff5f0083e12e18"

# Your master key hash (key: "GMXFLOW_MASTER_2026_SAGAR")  
MASTER_KEY_HASH = "e3d13db46a321e1fac6ef58588733e6cd6e2dbef6e3e7db7d47379ce8b5fd815"

# ==============================================


def hash_key(key: str) -> str:
    """Hash a license key using SHA256."""
    return hashlib.sha256(key.strip().upper().encode()).hexdigest()


def validate_key(key: str) -> bool:
    """Check if a key is valid."""
    key_hash = hash_key(key)
    return key_hash == WORKSHOP_KEY_HASH or key_hash == MASTER_KEY_HASH


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
    print("  your access key during the session.\n")
    
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
# Run: python license_check.py
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
        print("Copy this hash to WORKSHOP_KEY_HASH in license_check.py\n")
