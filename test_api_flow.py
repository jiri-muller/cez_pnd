#!/usr/bin/env python3
"""Test the complete API flow as Home Assistant would use it."""
import asyncio
import sys

# Mock Home Assistant aiohttp client
class MockHass:
    pass

async def test_api_flow(username: str, password: str, device_id: str = "86180"):
    """Test the complete API flow."""
    print("Testing API Flow (simulating Home Assistant)")
    print("=" * 80)

    # Import after path setup
    import aiohttp
    from datetime import datetime

    # Simulate what Home Assistant does
    hass = MockHass()

    # Create a real session like HA does
    session = aiohttp.ClientSession()

    # Import the API
    sys.path.insert(0, '/home/jiri_muller/workspace/ha/pnd/custom_components')
    from cez_pnd.api import CezPndApi

    # Create API instance (overwrites session)
    api = CezPndApi(username, password, device_id, hass)
    api.session = session  # Use our session

    try:
        print("\n1. Testing async_get_data() without prior authentication")
        print("   (This is what HA coordinator calls)")

        data = await api.async_get_data()

        print("\n✅ SUCCESS! Data fetched:")
        print(f"\n📊 Consumption:")
        print(f"   Total: {data['consumption']['total']} {data['consumption']['unit']}")
        print(f"   Date: {data['consumption']['date_from']} - {data['consumption']['date_to']}")

        print(f"\n📊 Production:")
        print(f"   Total: {data['production']['total']} {data['production']['unit']}")
        print(f"   Date: {data['production']['date_from']} - {data['production']['date_to']}")

        print(f"\n🕐 Last Update: {data['last_update']}")

        print("\n" + "=" * 80)
        print("✅ API Flow Test PASSED")
        print("=" * 80)

    except Exception as err:
        print(f"\n❌ ERROR: {err}")
        print(f"   Type: {type(err).__name__}")
        import traceback
        traceback.print_exc()

    finally:
        await session.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_api_flow.py <username> <password> [device_id]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    device_id = sys.argv[3] if len(sys.argv) > 3 else "86180"

    asyncio.run(test_api_flow(username, password, device_id))
