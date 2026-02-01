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

# Valid license key hashes (SHA256)
# Add new workshop participant keys here
# Generate hash: echo -n "YOUR_KEY" | sha256sum
VALID_KEY_HASHES = [
    # Workshop 2026 - Batch 1
    "5e884898da28047d9169bda8e6e5c8c6e6f831a4d9ea5c1a0a3f0f2c1b3d4e5f",  # Example
    # Add more hashes here as you generate keys for participants
]

# Master key that always works (for you)
MASTER_KEY_HASH = hashlib.sha256(b"GMXFLOW_MASTER_2026_SAGAR").hexdigest()


def hash_key(key: str) -> str:
    """Hash a license key."""
    return hashlib.sha256(key.strip().encode()).hexdigest()


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
                stored_hash = data.get("key_hash", "")
                return stored_hash == MASTER_KEY_HASH or stored_hash in VALID_KEY_HASHES
        except:
            pass
    return False


def save_license(key: str) -> bool:
    """Save a valid license key."""
    if validate_key(key):
        try:
            with open(LICENSE_FILE, 'w') as f:
                json.dump({
                    "key_hash": hash_key(key),
                    "activated": True
                }, f)
            return True
        except:
            pass
    return False


def prompt_for_license() -> bool:
    """
    Prompt user for license key.
    Returns True if valid key entered, False otherwise.
    """
    print("\n" + "=" * 50)
    print("  gmxFlow - Workshop Exclusive Access")
    print("=" * 50)
    print("\nThis software requires a license key.")
    print("If you attended a gmxFlow workshop, you should")
    print("have received your unique access key.\n")
    
    for attempt in range(3):
        key = input("Enter license key: ").strip()
        
        if validate_key(key):
            if save_license(key):
                print("\n✓ License activated successfully!")
                print("  You now have lifetime access to gmxFlow.\n")
                return True
            else:
                print("✗ Failed to save license. Check permissions.")
        else:
            remaining = 2 - attempt
            if remaining > 0:
                print(f"✗ Invalid key. {remaining} attempts remaining.")
            else:
                print("\n✗ Too many failed attempts.")
                print("  Contact the workshop organizer for assistance.")
    
    return False


def check_license() -> bool:
    """
    Main license check - call this at app startup.
    Returns True if licensed, False if not.
    """
    if is_licensed():
        return True
    return prompt_for_license()


# ============================================
# KEY GENERATION (For your use only)
# ============================================

def generate_key_hash(key: str):
    """
    Generate a hash for a new key.
    Run this to add new workshop participants:
    
    python -c "from license_check import generate_key_hash; generate_key_hash('WORKSHOP2026-PARTICIPANT-001')"
    """
    h = hash_key(key)
    print(f"Key: {key}")
    print(f"Hash: {h}")
    print(f"\nAdd this hash to VALID_KEY_HASHES in license_check.py")


if __name__ == "__main__":
    # Test
    print("Master key hash:", MASTER_KEY_HASH)
    print("\nTo generate a new key hash:")
    print("  python license_check.py generate YOUR_KEY_HERE")
    
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "generate":
        generate_key_hash(sys.argv[2])
