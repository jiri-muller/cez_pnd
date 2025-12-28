# How to Update Home Assistant with the Latest Fix

## Current Status

❌ **Your Home Assistant is still using the OLD version of the code**

The logs show:
```
Line 16: ERROR: Unexpected redirect after login: https://dip.cezdistribuce.cz/irj/portal?zpnd
```

This error message was **removed** in the latest fix, so you're definitely running old code.

---

## Method 1: Replace the File via SSH/Terminal

If you have SSH access to your Home Assistant:

```bash
# SSH into your Home Assistant
ssh root@homeassistant.local  # or your HA IP address

# Download the latest version
wget https://raw.githubusercontent.com/jiri-muller/cez_pnd/main/custom_components/cez_pnd/api.py \
  -O /config/custom_components/cez_pnd/api.py

# Restart Home Assistant
ha core restart
```

---

## Method 2: Replace via File Editor Add-on

If you have the File Editor add-on installed:

1. Open **File Editor** in Home Assistant
2. Navigate to: `config/custom_components/cez_pnd/api.py`
3. Delete the entire contents
4. Go to: https://raw.githubusercontent.com/jiri-muller/cez_pnd/main/custom_components/cez_pnd/api.py
5. Copy ALL the content
6. Paste into File Editor
7. Save the file
8. Go to Settings → System → Restart Home Assistant

---

## Method 3: Replace via Samba/Network Share

If you have Samba share enabled:

1. On your computer, connect to `\\homeassistant.local\config`
2. Navigate to: `custom_components\cez_pnd\`
3. Download the latest `api.py` from:
   https://raw.githubusercontent.com/jiri-muller/cez_pnd/main/custom_components/cez_pnd/api.py
4. Replace the file
5. Restart Home Assistant

---

## Method 4: Copy from Your Local Workspace

If you're developing on the same machine as Home Assistant:

```bash
# Copy the updated file from your workspace
sudo cp /home/jiri_muller/workspace/ha/pnd/custom_components/cez_pnd/api.py \
  /path/to/homeassistant/config/custom_components/cez_pnd/api.py

# Restart Home Assistant
ha core restart
```

---

## Verify the Update Worked

After restarting, check the logs. You should see:

✅ **NEW logs (correct):**
```
DEBUG: Login response status: 200
DEBUG: Login response URL: https://dip.cezdistribuce.cz/irj/portal?zpnd
DEBUG: Login successful, redirected to: https://dip.cezdistribuce.cz/irj/portal?zpnd
INFO: Authentication successful
DEBUG: Fetching data for assembly -1021
DEBUG: Response status: 200
```

❌ **OLD logs (wrong - if you still see this, update didn't work):**
```
ERROR: Unexpected redirect after login: https://dip.cezdistribuce.cz/irj/portal?zpnd
ERROR: Network error fetching data for assembly -1021: TooManyRedirects
```

---

## Common Issues

### "Permission Denied"
Run with `sudo` or ensure you have write permissions to the config directory.

### "File Not Found"
The Home Assistant config directory might be in a different location:
- Docker: Usually `/usr/share/hassio/homeassistant/`
- Core install: Usually `/home/homeassistant/.homeassistant/`
- Supervised: Usually `/usr/share/hassio/homeassistant/`

### "Still Getting Errors After Update"
1. Make sure you restarted Home Assistant (not just reloaded the integration)
2. Check the file was actually replaced (check file modification date)
3. Try removing and re-adding the integration completely

---

## Need Help?

The latest working code is at:
https://github.com/jiri-muller/cez_pnd/blob/main/custom_components/cez_pnd/api.py

Commit: `c600ca5` - "Fix redirect validation to accept dip.cezdistribuce.cz"
