# Installation Guide

## Testing Authentication First

Before installing in Home Assistant, test if the authentication works:

```bash
# Install required dependency
pip3 install aiohttp

# Run the test script
python3 test_auth.py YOUR_USERNAME YOUR_PASSWORD [YOUR_DEVICE_ID]
```

This will test the authentication and show you if data can be fetched successfully.

## Installing in Home Assistant

### Option 1: Manual Installation

1. Copy the `custom_components/cez_pnd` directory to your Home Assistant's `config/custom_components/` directory:

   ```bash
   # If you're on the same machine as Home Assistant
   cp -r custom_components/cez_pnd /path/to/homeassistant/config/custom_components/

   # Or use scp if Home Assistant is on another machine
   scp -r custom_components/cez_pnd user@homeassistant:/config/custom_components/
   ```

2. Restart Home Assistant

3. Go to Settings → Devices & Services → Add Integration → Search for "ČEZ Distribuce PND"

### Option 2: HACS Installation (Recommended)

1. Make sure HACS is installed in your Home Assistant instance

2. Add this repository as a custom repository in HACS:
   - Open HACS
   - Go to Integrations
   - Click the three dots menu (top right)
   - Select "Custom repositories"
   - Add the repository URL: `https://github.com/YOUR_USERNAME/ha-cez-pnd`
   - Category: Integration
   - Click "Add"

3. Find "ČEZ Distribuce PND" in HACS and install it

4. Restart Home Assistant

5. Go to Settings → Devices & Services → Add Integration → Search for "ČEZ Distribuce PND"

## Configuration

When adding the integration, you'll need:

- **Username**: Your ČEZ Distribuce portal username/email
- **Password**: Your ČEZ Distribuce portal password
- **Device ID** (optional): Usually you can leave this as the default value

## What You'll Get

After successful configuration, you'll have two sensors:

1. **sensor.cez_pnd_energy_consumption** - Daily energy consumption in kWh
2. **sensor.cez_pnd_energy_production** - Daily energy production in kWh

Each sensor includes additional attributes:
- `last_value`: Most recent measurement
- `min`, `max`: Min/max values for the period
- `meter_name`: Name from the PND portal
- `date_from`, `date_to`: Data period
- `last_update`: Last update timestamp

## Troubleshooting

### Integration not showing up

1. Make sure you've copied the files to the correct location
2. Check that the directory structure is correct: `config/custom_components/cez_pnd/`
3. Restart Home Assistant
4. Check the logs for any errors: Settings → System → Logs

### Authentication fails

1. First test with the `test_auth.py` script to verify credentials
2. Make sure you can log in manually at https://pnd.cezdistribuce.cz
3. Check the Home Assistant logs for detailed error messages
4. The authentication flow may need adjustment if ČEZ has changed their login process

### No data showing

1. Check if you have data available in the PND portal itself
2. The integration fetches yesterday's data (today's data may not be available yet)
3. Look at the sensor attributes to see the date range of the data
4. Check the logs for any API errors

## Next Steps

Once installed, you can:
- Create dashboards to visualize your consumption and production
- Set up automations based on energy usage
- Use the data in Energy Dashboard (if configured)
- Create templates to calculate costs, savings, etc.

## Publishing to GitHub

To share this integration:

1. Initialize git repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - ČEZ PND integration"
   ```

2. Create a repository on GitHub (e.g., `ha-cez-pnd`)

3. Push to GitHub:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/ha-cez-pnd.git
   git branch -M main
   git push -u origin main
   ```

4. Update the URLs in `manifest.json` and `README.md` with your actual GitHub repository URL
