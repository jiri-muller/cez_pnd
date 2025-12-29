#!/usr/bin/env python3
"""Test script to verify all imports work correctly."""
import sys
import os

# Add custom_components to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

def test_imports():
    """Test that all modules can be imported without errors."""
    errors = []

    # Test API module
    try:
        from cez_pnd import api_requests
        print("✅ api_requests.py imports successfully")
    except Exception as e:
        errors.append(f"❌ api_requests.py: {e}")

    # Test sensor module
    try:
        from cez_pnd import sensor
        print("✅ sensor.py imports successfully")
    except Exception as e:
        errors.append(f"❌ sensor.py: {e}")

    # Test __init__ module
    try:
        from cez_pnd import __init__
        print("✅ __init__.py imports successfully")
    except Exception as e:
        errors.append(f"❌ __init__.py: {e}")

    # Test const module
    try:
        from cez_pnd import const
        print("✅ const.py imports successfully")
    except Exception as e:
        errors.append(f"❌ const.py: {e}")

    if errors:
        print("\n❌ ERRORS FOUND:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ All modules imported successfully!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
