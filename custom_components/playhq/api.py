"""Thin async client for PlayHQ's public (unauthenticated) GraphQL APIs.

These are the same endpoints the PlayHQ mobile app and website use for
anonymous "discover"/spectator access - no PlayHQ account or API key is
required. Reverse-engineered by capturing the app's own traffic; PlayHQ has
no public/documented API, so field names here are only as stable as
PlayHQ's own app.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_URL = "https://api.playhq.com/graphql"
SPECTATOR_URL = "https://spectator.playhq.com/graphql"
SEARCH_URL = "https://search.playhq.com/graphql"

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class PlayHQApiError(Exception):
    """Raised when a PlayHQ GraphQL call fails or returns errors."""


def _headers(tenant: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "tenant": tenant,
        "x-phq-tenant": tenant,
        "Origin": "https://www.playhq.com",
        "User-Agent": "home-assistant-playhq/0.1",
    }


# ---------------------------------------------------------------------------
# GraphQL documents
# ---------------------------------------------------------------------------
SEARCH_QUERY = """
query Search($filter: SearchFilter!) {
  search(filter: $filter) {
    results { ... on Organisation { id routingCode name type __typename } __typename }
    __typename
  }
}
"""

COMPETITIONS_QUERY = """
query OrganisationCompetitions($organisationId: ID!) {
  discoverCompetitions(organisationID: $organisationId) {
    id
    name
    seasons(organisationID: $organisationId) {
      id name status { value __typename } __typename
    }
    __typename
  }
}
"""

SEASON_TEAMS_QUERY = """
query Season($isClub: Boolean!, $filter: DiscoverTeamsFilter!) {
  discoverTeams(filter: $filter) @include(if: $isClub) {
    id name grade { name __typename } __typename
  }
}
"""

LOGO_FRAGMENT = """
logo {
  sizes {
    url
    dimensions { width height __typename }
    __typename
  }
  __typename
}
"""

TEAM_RESULT_FRAGMENT = """
statistics { type { value __typename } count __typename }
periods {
  type
  closureStatus
  period { value __typename }
  statistics { type { value __typename } count __typename }
  __typename
}
__typename
"""

TEAM_FIXTURE_QUERY = f"""
query TeamFixture($teamID: ID!) {{
  discoverTeamFixture(teamID: $teamID) {{
    fixture {{
      games {{
        id
        dates
        status {{ value __typename }}
        allocation {{
          time
          court {{
            name
            venue {{
              name
              address
              suburb
              state
              postcode
              __typename
            }}
            __typename
          }}
          __typename
        }}
        home {{
          ... on DiscoverTeam {{ id name {LOGO_FRAGMENT} __typename }}
          ... on ProvisionalTeam {{ name __typename }}
          __typename
        }}
        away {{
          ... on DiscoverTeam {{ id name {LOGO_FRAGMENT} __typename }}
          ... on ProvisionalTeam {{ name __typename }}
          __typename
        }}
        result {{
          home {{ {TEAM_RESULT_FRAGMENT} }}
          away {{ {TEAM_RESULT_FRAGMENT} }}
          __typename
        }}
        __typename
      }}
      __typename
    }}
    __typename
  }}
}}
"""

LIVE_TEAM_RESULT_FRAGMENT = """
statistics { type { value __typename } count __typename }
periods(scope: BY_PERIOD) {
  period { value __typename }
  statistics { type { value __typename } count __typename }
  closureStatus
  role
  __typename
}
__typename
"""

LIVE_GAME_QUERY = f"""
query Game($id: ID!) {{
  game(id: $id) {{
    id
    status
    updatedAt
    lastEventRecordedAt
    clock {{
      overtimeSequenceNo
      period
      periodValue
      time
      status
      lastUpdatedAt
      __typename
    }}
    result {{
      currentPeriod {{ value primarySide __typename }}
      home {{ {LIVE_TEAM_RESULT_FRAGMENT} }}
      away {{ {LIVE_TEAM_RESULT_FRAGMENT} }}
      __typename
    }}
    __typename
  }}
}}
"""


# ---------------------------------------------------------------------------
# Small shape-independent helpers reused by the coordinator
# ---------------------------------------------------------------------------
def stat(stats_list: list[dict] | None, key: str) -> Any:
    for s in stats_list or []:
        if s["type"]["value"] == key:
            return s["count"]
    return None


def periods_by_quarter(periods: list[dict] | None) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for p in periods or []:
        val = (p.get("period") or {}).get("value")
        if val:
            out[val] = p.get("statistics") or []
    return out


def extract_score(result: dict | None):
    """Works for both the TeamFixture-style and live-game-style `result` - same shape."""
    if not result:
        return [], [], {}, {}
    home = result.get("home") or {}
    away = result.get("away") or {}
    return (
        home.get("statistics") or [],
        away.get("statistics") or [],
        periods_by_quarter(home.get("periods")),
        periods_by_quarter(away.get("periods")),
    )


def pick_logo_url(team: dict | None, target_width: int = 64) -> str | None:
    sizes = ((team or {}).get("logo") or {}).get("sizes") or []
    if not sizes:
        return None
    best = min(sizes, key=lambda s: abs((s.get("dimensions") or {}).get("width", 0) - target_width))
    return best.get("url")


def venue_text(game: dict) -> str | None:
    court = ((game.get("allocation") or {}).get("court")) or {}
    venue = court.get("venue") or {}
    parts = [p for p in (venue.get("name") or court.get("name"), venue.get("suburb")) if p]
    return ", ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Player statistics (publicProfileStatistics) - anonymous, but there is no
# anonymous player search on PlayHQ, so the caller must already know the
# profile ID (a UUID, e.g. from a public PlayHQ player-profile page URL).
# ---------------------------------------------------------------------------
PLAYER_STATISTICS_QUERY = """
query PublicProfileStatistics($profileID: ID!) {
  publicProfileStatistics(profileID: $profileID) {
    careerStatistics {
      totalStatistics { count details { value __typename } gameFormat __typename }
      clubStatistics {
        club { id name __typename }
        statistics { count details { value __typename } gameFormat __typename }
        __typename
      }
      __typename
    }
    seasonStatistics {
      name
      statistics {
        role
        club { id name __typename }
        totalStatistics { count details { value __typename } gameFormat __typename }
        teamStatistics {
          team {
            ... on DiscoverTeam { id name __typename }
            ... on ProvisionalTeam { name __typename }
            __typename
          }
          totalStatistics { count details { value __typename } gameFormat __typename }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}
"""


class PlayHQClient:
    """Async wrapper around PlayHQ's discover/spectator GraphQL endpoints."""

    def __init__(self, session: aiohttp.ClientSession, tenant: str = "afl") -> None:
        self._session = session
        self._tenant = tenant

    async def _gql(self, url: str, operation_name: str, query: str, variables: dict) -> dict:
        try:
            async with self._session.post(
                url,
                json={"operationName": operation_name, "query": query, "variables": variables},
                headers=_headers(self._tenant),
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise PlayHQApiError(f"{operation_name}: HTTP {resp.status}: {text[:300]}")
                data = json.loads(text)
        except aiohttp.ClientError as err:
            raise PlayHQApiError(f"{operation_name}: network error: {err}") from err

        if "errors" in data:
            raise PlayHQApiError(f"{operation_name}: {data['errors']}")
        return data.get("data") or {}

    async def search_organisations(self, query_text: str) -> list[dict]:
        data = await self._gql(
            SEARCH_URL,
            "Search",
            SEARCH_QUERY,
            {
                "filter": {
                    "meta": {"limit": 20, "page": 1},
                    "organisation": {"query": query_text, "types": ["CLUB", "ASSOCIATION"], "tenantSlug": self._tenant},
                }
            },
        )
        return data["search"]["results"]

    async def get_competitions(self, org_id: str) -> list[dict]:
        data = await self._gql(API_URL, "OrganisationCompetitions", COMPETITIONS_QUERY, {"organisationId": org_id})
        return data.get("discoverCompetitions") or []

    async def get_teams(self, org_id: str, season_id: str) -> list[dict]:
        data = await self._gql(
            API_URL,
            "Season",
            SEASON_TEAMS_QUERY,
            {"isClub": True, "filter": {"seasonID": season_id, "organisationID": org_id}},
        )
        return data.get("discoverTeams") or []

    async def get_all_games(self, team_id: str) -> list[dict]:
        data = await self._gql(API_URL, "TeamFixture", TEAM_FIXTURE_QUERY, {"teamID": team_id})
        rounds = data.get("discoverTeamFixture") or []
        games: list[dict] = []
        for rnd in rounds:
            games.extend((rnd.get("fixture") or {}).get("games") or [])
        return games

    async def get_live_detail(self, game_id: str) -> dict | None:
        data = await self._gql(SPECTATOR_URL, "Game", LIVE_GAME_QUERY, {"id": game_id})
        return data.get("game")

    async def get_player_statistics(self, profile_id: str) -> dict | None:
        data = await self._gql(API_URL, "PublicProfileStatistics", PLAYER_STATISTICS_QUERY, {"profileID": profile_id})
        return data.get("publicProfileStatistics")


def pick_active_season(competition: dict) -> dict | None:
    for season in competition.get("seasons") or []:
        if (season.get("status") or {}).get("value") == "ACTIVE":
            return season
    seasons = competition.get("seasons") or []
    return seasons[0] if seasons else None
