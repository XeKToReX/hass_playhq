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

# PlayHQ's publicProfileStatistics only returns a stat category once it has at
# least one recorded event, rather than returning it with a count of 0 - so a
# player who e.g. hasn't scored yet has no "points" entry at all. These are
# the categories PlayHQ documents as always tracked per sport, zero-filled in
# when the API omits them so they still show up (as 0) on the player sensor.
PLAYER_STAT_DEFAULTS: dict[str, dict[str, int]] = {
    SPORT_AFL: {"APPEARANCE": 0, "GOAL_COUNT": 0},
    SPORT_BASKETBALL: {"APPEARANCE": 0, "TOTAL_FOULS": 0, "TOTAL_SCORE": 0},
}

DEFAULT_TENANT = "afl"

# Poll interval when nothing live is happening, vs. while a game is in progress.
IDLE_UPDATE_INTERVAL = 300  # seconds
LIVE_UPDATE_INTERVAL = 20   # seconds

# Player stats aren't live - they only change after a game is finalised.
PLAYER_UPDATE_INTERVAL = 1800  # seconds

MANUFACTURER = "PlayHQ (unofficial)"
