# ČEZ PND Integration - Quick Reference

## Installation (3 Steps)

```bash
# 1. Test credentials (optional)
python3 test_auth.py jiri.mull@gmail.com your_password

# 2. Copy to Home Assistant
cp -r custom_components/cez_pnd /config/custom_components/

# 3. Restart HA and add via UI
# Settings → Integrations → Add Integration → "ČEZ Distribuce PND"
```

## Configuration

| Field | Value | Notes |
|-------|-------|-------|
| Username | jiri.mull@gmail.com | Your ČEZ portal email |
| Password | ••••••••••••••••••• | Your ČEZ portal password |
| Device ID | 86180 | Auto-detected, usually don't change |

## Sensors Created

### sensor.cez_pnd_energy_consumption
- **State**: Daily consumption (kWh)
- **Attributes**: min, max, total, date_from, date_to, meter_name

### sensor.cez_pnd_energy_production
- **State**: Daily production (kWh)
- **Attributes**: min, max, total, date_from, date_to, meter_name

## Update Schedule
- **Frequency**: Every 1 hour
- **Data Delay**: ~24 hours (previous day's data)

## Troubleshooting

### Auth fails
```bash
# Test credentials first
python3 test_auth.py your.email@gmail.com your_password

# Check if you can log in at:
# https://pnd.cezdistribuce.cz
```

### No data showing
- Wait 24 hours after setup (data is delayed)
- Check HA logs: Settings → System → Logs
- Search for "cez_pnd"

### Integration unavailable
```bash
# Check logs in HA
# Re-enter credentials in integration config
# Or reload the integration
```

## API Endpoints (Technical)

```
Auth: https://pnd.cezdistribuce.cz/cezpnd2/oauth2/authorization/mepas-external
Login: https://cas.cez.cz/cas/login
Data: https://pnd.cezdistribuce.cz/cezpnd2/external/data
```

## File Locations

```
config/
└── custom_components/
    └── cez_pnd/
        ├── __init__.py          # Main integration
        ├── api.py               # Auth & data fetching
        ├── config_flow.py       # UI setup
        ├── sensor.py            # Sensor entities
        ├── manifest.json        # Metadata
        └── translations/        # UI strings
```

## Quick Commands

```bash
# Check integration logs
tail -f /config/home-assistant.log | grep cez_pnd

# Test auth standalone
python3 test_auth.py email password

# Restart HA (SSH/Terminal)
ha core restart

# Reload integration (Developer Tools → YAML → Reload Integrations)
```

## Data Format

### Consumption
- **ID**: -1021
- **Meter**: +A d/84075547
- **Unit**: kWh

### Production
- **ID**: -1022
- **Meter**: -A d/84075547
- **Unit**: kWh

## Support

1. Check [TESTING_RESULTS.md](TESTING_RESULTS.md)
2. Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
3. Test with `test_auth.py`
4. Open GitHub issue with logs

## Version Info

- **Version**: 0.1.0
- **HA Min Version**: 2023.1.0
- **IoT Class**: Cloud Polling
- **Tested**: 2025-12-28

---

**Status**: ✅ Working | **License**: MIT | **Source**: [GitHub](#)
