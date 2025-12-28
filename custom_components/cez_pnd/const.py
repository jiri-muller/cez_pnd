"""Constants for the ČEZ Distribuce PND integration."""

DOMAIN = "cez_pnd"

# API endpoints
API_BASE_URL = "https://pnd.cezdistribuce.cz/cezpnd2"
API_LOGIN_URL = f"{API_BASE_URL}/oauth2/authorization/mepas-external"
API_DATA_URL = f"{API_BASE_URL}/external/data"

# Assembly IDs
ID_ASSEMBLY_CONSUMPTION = -1021
ID_ASSEMBLY_PRODUCTION = -1022

# Default values
DEFAULT_DEVICE_ID = "86180"
