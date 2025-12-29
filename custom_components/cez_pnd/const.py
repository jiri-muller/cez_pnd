"""Constants for the ČEZ Distribuce PND integration."""

DOMAIN = "cez_pnd"

# API endpoints
API_BASE_URL = "https://pnd.cezdistribuce.cz/cezpnd2"
API_LOGIN_URL = f"{API_BASE_URL}/oauth2/authorization/mepas-external"
API_DATA_URL = f"{API_BASE_URL}/external/data"

# Assembly IDs for daily energy (kWh)
ID_ASSEMBLY_CONSUMPTION = -1021
ID_ASSEMBLY_PRODUCTION = -1022

# Assembly IDs for 15-minute power (kW)
ID_ASSEMBLY_CONSUMPTION_POWER = -1001
ID_ASSEMBLY_PRODUCTION_POWER = -1002

# Default values
DEFAULT_DEVICE_ID = "86180"
