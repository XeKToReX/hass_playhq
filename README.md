# PlayHQ for Home Assistant

Unofficial Home Assistant integration for [PlayHQ](https://www.playhq.com) - live
scores, next match, last result for a team, and career/season stats for a
player, using PlayHQ's public (unauthenticated) GraphQL APIs. No PlayHQ login
required.

Supports any sport PlayHQ powers - AFL, basketball, and cricket are built in
(the scoreline formatting is tailored to each: goals.behinds for AFL, a plain
score for basketball, runs/wickets/overs per innings for cricket).

Not affiliated with or endorsed by PlayHQ.

## Install

### HACS (custom repository, until this is in the default store)
1. HACS -> Integrations -> ⋮ -> Custom repositories -> add this repo URL, category "Integration".
2. Install "PlayHQ", restart Home Assistant.

### Manual
Copy `custom_components/playhq` into your `config/custom_components/` folder and restart.

## Setup

Settings -> Devices & Services -> Add Integration -> **PlayHQ**, then:

1. **Pick the sport** - AFL, Basketball, or Cricket.
2. **For basketball or cricket, pick the PlayHQ tenant** - unlike AFL (one
   national tenant, `afl`), basketball and cricket are each run by separate
   state or national bodies, each its own PlayHQ tenant. It's the first part
   of the URL on any of that body's PlayHQ pages - e.g. `basketball-victoria`
   in `playhq.com/basketball-victoria/org/...`, or `cricket-australia` in
   `playhq.com/cricket-australia/org/...`. Cricket defaults to
   `cricket-australia`; basketball has no single default since it's split by
   state (`basketball-victoria`, `basketball-wa`, ...) - check a club's PlayHQ
   URL if you're not sure.
3. **Choose what to track:**
   - **A team** - search for your club, pick it from the results, then pick a
     team. Creates `sensor.<team>_status` with the team's live/next/last-result
     data as attributes; state is `live`, `scheduled`, `final`, or `unknown`.
   - **A player** - PlayHQ has no public player search, so you enter their
     **profile ID** (a UUID) directly - it's the ID in a public PlayHQ
     player-profile page URL, e.g.
     `https://www.playhq.com/.../profile/<this-part>`. Creates
     `sensor.<player>_games_played` with career and current-season statistics as
     attributes; state is the player's career games-played count.

Add another integration entry per team or player you want to track.

## Card

The `playhq-card` Lovelace card is bundled and auto-registered as a frontend
resource - no manual resource setup needed. Add it via the dashboard UI (it
has a full visual editor: pick the entity from a dropdown, toggle which
sections show, and reorder them with the arrow buttons), or in YAML:

```yaml
type: custom:playhq-card
entity: sensor.your_team_status   # or sensor.your_player_games_played
title: My Team                    # optional, defaults to the team/player name
show_logos: true
show_quarters: true
section_order: [live, next, last_result, career, season]
disabled_sections: []             # e.g. [career, season] to hide those on a team card
```

Sections a team entity has no data for (`career`, `season`) and sections a
player entity has no data for (`live`, `next`, `last_result`) are simply
skipped, so the same card config works for either entity type.

## How it works / limitations

This uses the same anonymous GraphQL endpoints PlayHQ's own app and website
use for public score/fixture/profile viewing (`api.playhq.com`,
`spectator.playhq.com`, `search.playhq.com`). PlayHQ has no official public
API, so field names were reverse-engineered from live traffic and may change
without notice - if the integration starts erroring, check for an update or
open an issue.

Team polling is every 5 minutes normally, and every 20 seconds while a
tracked team has a game in progress. Player stats only change after a game is
finalised, so those poll every 30 minutes.

Player tracking requires you to already know the player's profile ID - there
is no anonymous way to search for a player by name on PlayHQ, only clubs and
teams are searchable.

PlayHQ uses one shared GraphQL schema across every sport it powers, so the
same queries work for AFL, basketball, and cricket - only the scoring fields
differ. The quarter-by-quarter breakdown table is AFL-specific (basketball and
cricket results don't carry period-by-period stats the same way); basketball
shows a plain score and cricket shows a per-innings scorecard instead.
