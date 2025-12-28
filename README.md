# ČEZ Distribuce PND Integration for Home Assistant

This custom integration allows you to fetch energy consumption and production data from the ČEZ Distribuce Portal Naměřených Dat (PND) and display it in Home Assistant.

## ✅ Status: Working and Tested

Successfully tested on 2025-12-28. See [TESTING_RESULTS.md](TESTING_RESULTS.md) for detailed test results.

## Quick Start

```bash
# Test authentication first (optional but recommended)
python3 test_auth.py your.email@gmail.com your_password

# If successful, install in Home Assistant
cp -r custom_components/cez_pnd /path/to/homeassistant/config/custom_components/
# Then restart Home Assistant and add the integration via Settings → Integrations
```

## Features

- Fetches daily energy consumption data
- Fetches daily energy production data (for solar installations)
- Automatic authentication with the PND portal
- Updates every hour
- Provides additional attributes (min, max, meter name, date range)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/cez_pnd` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "ČEZ Distribuce PND"
4. Enter your credentials:
   - **Username**: Your ČEZ Distribuce portal username
   - **Password**: Your ČEZ Distribuce portal password
   - **Device ID** (optional): Leave as default unless you have a specific device ID

## Sensors

The integration creates two sensors:

- **ČEZ PND Energy Consumption**: Daily energy consumption in kWh
- **ČEZ PND Energy Production**: Daily energy production in kWh (from solar panels)

### Additional Attributes

Each sensor provides these additional attributes:

- `last_value`: The most recent data point value
- `min`: Minimum value for the period
- `max`: Maximum value for the period
- `meter_name`: Name of the meter from PND
- `date_from`: Start date of the data period
- `date_to`: End date of the data period
- `last_update`: Timestamp of the last update

## Troubleshooting

### Authentication Issues

If you experience authentication issues:

1. Verify your credentials are correct by logging into the PND portal manually
2. Check the Home Assistant logs for detailed error messages
3. The integration may need to be updated if ČEZ changes their authentication flow

### No Data Available

- The PND portal typically has a delay in making data available
- Data is fetched for the previous day, not the current day
- Check that your account has access to consumption/production data in the portal

### Session Expires

The integration automatically re-authenticates if the session expires. If you see repeated authentication attempts:

1. Check your credentials
2. Verify you can log in manually to the portal
3. Review Home Assistant logs for specific error messages

## Notes

- This is an unofficial integration and is not affiliated with ČEZ Distribuce
- The integration reverse-engineers the PND portal API, so it may break if ČEZ changes their portal
- Data is updated every hour by default
- Only daily historical data is currently supported (not real-time)

## Support

For issues and feature requests, please open an issue on GitHub.

## License

This project is licensed under the MIT License.
