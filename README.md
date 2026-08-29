# PlayHQ for Home Assistant

Unofficial Home Assistant integration for [PlayHQ](https://www.playhq.com) - live
scores, next match, and last result for a team, using PlayHQ's public
(unauthenticated) GraphQL APIs. No PlayHQ login required.

Not affiliated with or endorsed by PlayHQ.

## Install

### HACS (custom repository, until this is in the default store)
1. HACS -> Integrations -> ⋮ -> Custom repositories -> add this repo URL, category "Integration".
2. Install "PlayHQ", restart Home Assistant.

### Manual
Copy `custom_components/playhq` into your `config/custom_components/` folder and restart.

## Setup

Settings -> Devices & Services -> Add Integration -> **PlayHQ**.
Search for your club, pick it from the results, then pick your team. A sensor
(`sensor.<team>_status`) is created with the team's live/next/last-result data
as attributes, and its state is `live`, `scheduled`, `final`, or `unknown`.

Add another integration entry per team you want to track.

## Card

The `playhq-card` Lovelace card is bundled and auto-registered as a frontend
resource - no manual resource setup needed. Example:

```yaml
type: custom:playhq-card
entity: sensor.your_team_status
show_live: true
show_next: true
show_last_result: true
show_logos: true
show_quarters: true
```

All `show_*` options default to `true`; set any to `false` to hide that
section. `title` optionally overrides the card header.

## How it works / limitations

This uses the same anonymous GraphQL endpoints PlayHQ's own app and website
use for public score/fixture viewing (`api.playhq.com`, `spectator.playhq.com`,
`search.playhq.com`). PlayHQ has no official public API, so field names were
reverse-engineered from live traffic and may change without notice - if the
integration starts erroring, check for an update or open an issue.

Polling is every 5 minutes normally, and every 20 seconds while a tracked
team has a game in progress.
