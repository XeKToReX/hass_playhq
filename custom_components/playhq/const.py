"""Constants for the PlayHQ integration."""

DOMAIN = "playhq"
PLATFORMS = ["sensor"]

CONF_ORG_ID = "org_id"
CONF_ORG_NAME = "org_name"
CONF_TEAM_ID = "team_id"
CONF_TEAM_NAME = "team_name"
CONF_GRADE_NAME = "grade_name"
CONF_TENANT = "tenant"

DEFAULT_TENANT = "afl"

# Poll interval when nothing live is happening, vs. while a game is in progress.
IDLE_UPDATE_INTERVAL = 300  # seconds
LIVE_UPDATE_INTERVAL = 20   # seconds

MANUFACTURER = "PlayHQ (unofficial)"
