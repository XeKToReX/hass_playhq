"""Constants for the PlayHQ integration."""

DOMAIN = "playhq"
PLATFORMS = ["sensor"]

CONF_KIND = "kind"
KIND_TEAM = "team"
KIND_PLAYER = "player"

CONF_ORG_ID = "org_id"
CONF_ORG_NAME = "org_name"
CONF_TEAM_ID = "team_id"
CONF_TEAM_NAME = "team_name"
CONF_GRADE_NAME = "grade_name"
CONF_TENANT = "tenant"

CONF_PROFILE_ID = "profile_id"
CONF_PLAYER_NAME = "player_name"

CONF_SPORT = "sport"
SPORT_AFL = "afl"
SPORT_BASKETBALL = "basketball"
SPORT_CRICKET = "cricket"
DEFAULT_SPORT = SPORT_AFL

SPORT_LABELS = {
    SPORT_AFL: "AFL",
    SPORT_BASKETBALL: "Basketball",
    SPORT_CRICKET: "Cricket",
}

DEFAULT_TENANT = "afl"

# Poll interval when nothing live is happening, vs. while a game is in progress.
IDLE_UPDATE_INTERVAL = 300  # seconds
LIVE_UPDATE_INTERVAL = 20   # seconds

# Player stats aren't live - they only change after a game is finalised.
PLAYER_UPDATE_INTERVAL = 1800  # seconds

MANUFACTURER = "PlayHQ (unofficial)"
