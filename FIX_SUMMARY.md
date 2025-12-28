# Fix for "Error communicating with API" Issue

## Problem

After adding the integration to Home Assistant, the following error occurred:
```
Nastavení se nezdařilo, bude se zkoušet znovu:
Error communicating with API: 0, message='', url='https://pnd.cezdistribuce.cz/cezpnd2/external/data'
```

## Root Cause

The integration had **two critical bugs**:

### 1. **Missing Initial Authentication**
The `async_get_data()` method was called by the coordinator immediately during setup, but `async_authenticate()` was never called first. This meant the API client had no session cookies and couldn't fetch data.

### 2. **Incorrect Date Format**
The date interval was incorrectly formatted:
```python
# BEFORE (incorrect)
interval_from = start_date.strftime(date_format).replace(" 00:00", " 00:00")  # Does nothing!
interval_to = end_date.strftime(date_format).replace(" 00:00", " 00:00")
```

This would create dates like "27.12.2025 19:30" to "28.12.2025 19:30" instead of fetching a complete day's data.

## Solution

### Fix 1: Auto-Authentication in `async_get_data()`

Added authentication check at the start of `async_get_data()`:

```python
async def async_get_data(self) -> dict[str, Any]:
    """Fetch data from the PND portal."""
    # Ensure we're authenticated first
    if not self._cookies:
        _LOGGER.debug("No session cookies found, authenticating...")
        await self.async_authenticate()

    # ... rest of the method
```

This ensures that:
- First call will authenticate automatically
- Subsequent calls reuse the session
- If session expires (caught by retry logic), it re-authenticates

### Fix 2: Correct Date Formatting

Fixed the date range to fetch a complete day:

```python
# AFTER (correct)
# Get yesterday's data
start_date = end_date - timedelta(days=1)

# Format dates for full day (00:00 to 23:59)
date_format = "%d.%m.%Y %H:%M"
interval_from = start_date.replace(hour=0, minute=0, second=0).strftime(date_format)
interval_to = start_date.replace(hour=23, minute=59, second=59).strftime(date_format)
```

This creates correct date ranges like:
- `"27.12.2025 00:00"` to `"27.12.2025 23:59"`

### Fix 3: Better Error Handling and Logging

Added:
- More detailed error logging with error types
- Better handling of aiohttp ClientError exceptions
- Clear cookies when re-authenticating
- Debug logging for troubleshooting

```python
except aiohttp.ClientError as err:
    _LOGGER.error(
        "Network error fetching data for assembly %s: %s (type: %s)",
        id_assembly,
        err,
        type(err).__name__,
    )
    raise
```

## Files Modified

- `custom_components/cez_pnd/api.py` - Lines 123-281

## How to Apply the Fix

### If Already Installed:

1. **Replace the file**:
   ```bash
   cp custom_components/cez_pnd/api.py /config/custom_components/cez_pnd/api.py
   ```

2. **Restart Home Assistant**:
   ```bash
   ha core restart
   ```

3. **Reload the integration**:
   - Go to Settings → Devices & Services
   - Find "ČEZ Distribuce PND"
   - Click the three dots → Reload

### If Not Yet Installed:

Just copy the updated `custom_components/cez_pnd` directory to your Home Assistant and configure normally.

## Expected Behavior After Fix

1. **During Setup**:
   - Integration will authenticate automatically
   - First data fetch will succeed
   - Sensors will be created with yesterday's data

2. **During Operation**:
   - Updates every hour
   - Auto re-authenticates if session expires
   - Fetches complete day's data (00:00 to 23:59)

3. **In Logs** (Debug mode):
   ```
   [cez_pnd] No session cookies found, authenticating...
   [cez_pnd] Starting OAuth2 flow
   [cez_pnd] CAS Login URL: https://cas.cez.cz/cas/login?service=...
   [cez_pnd] Extracted execution token (length: 8617)
   [cez_pnd] Attempting login to CAS
   [cez_pnd] Login response status: 200
   [cez_pnd] Authentication successful
   [cez_pnd] Fetching data from 27.12.2025 00:00 to 27.12.2025 23:59
   [cez_pnd] Fetching data for assembly -1021
   [cez_pnd] Response status: 200, URL: https://pnd.cezdistribuce.cz/...
   [cez_pnd] Received data: {...}
   ```

## Testing

To verify the fix works, check Home Assistant logs after reloading:

```bash
# View logs
tail -f /config/home-assistant.log | grep cez_pnd

# Or in HA UI:
# Settings → System → Logs → Search for "cez_pnd"
```

You should see:
- ✅ Authentication messages
- ✅ Data fetch messages
- ✅ No error messages
- ✅ Sensors updating with data

## Verification

After applying the fix, you should see:

### In Home Assistant:

1. **Sensors Created**:
   - `sensor.cez_pnd_energy_consumption`
   - `sensor.cez_pnd_energy_production`

2. **Sensor States** (example):
   - Consumption: `28.028 kWh`
   - Production: `0.0 kWh`

3. **Sensor Attributes**:
   ```yaml
   last_value: 28.028
   min: 28.028
   max: 28.028
   total: 28.028
   meter_name: "+A d/84075547"
   date_from: "27.12.2025"
   date_to: "27.12.2025"
   last_update: "2025-12-28T21:00:00"
   ```

4. **No Errors** in:
   - Integration status
   - System logs
   - Sensor availability

## Additional Notes

- The integration now properly handles the complete authentication flow
- Session cookies are maintained across requests
- Re-authentication happens automatically when needed
- Complete day's data is fetched (not partial periods)
- All error messages are more descriptive for easier debugging

## Support

If issues persist after applying this fix:

1. Enable debug logging:
   ```yaml
   # configuration.yaml
   logger:
     default: warning
     logs:
       custom_components.cez_pnd: debug
   ```

2. Restart HA and check logs for detailed error messages

3. Verify credentials still work at https://pnd.cezdistribuce.cz

4. Check that device_id is correct (should be "86180" or auto-detected)
