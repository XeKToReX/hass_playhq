"""Data update coordinator for a single tracked PlayHQ player profile."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PlayHQApiError, PlayHQClient
from .const import DOMAIN, PLAYER_STAT_DEFAULTS, PLAYER_UPDATE_INTERVAL, SPORT_AFL

_LOGGER = logging.getLogger(__name__)


def _stat_key(stat: dict) -> Any:
    details = stat.get("details")
    if isinstance(details, list):
        return details[0].get("value") if details else None
    if isinstance(details, dict):
        return details.get("value")
    return None


def _stat(stats_list: list[dict] | None, key: str) -> Any:
    for s in stats_list or []:
        if _stat_key(s) == key:
            return s.get("count")
    return None


def _stats_dict(stats_list: list[dict] | None, sport: str) -> dict[str, Any]:
    """{stat_key: count}, zero-filled for categories PlayHQ omits when unrecorded."""
    computed = {_stat_key(s): s.get("count") for s in stats_list or []}
    return {**PLAYER_STAT_DEFAULTS.get(sport, {}), **computed}


class PlayHQPlayerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls a player's public career/season statistics."""

    def __init__(
        self, hass: HomeAssistant, profile_id: str, player_name: str, tenant: str, sport: str = SPORT_AFL
    ) -> None:
        self.profile_id = profile_id
        self.player_name = player_name
        self.sport = sport
        self.client = PlayHQClient(async_get_clientsession(hass), tenant=tenant)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_player_{player_name}",
            update_interval=timedelta(seconds=PLAYER_UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            stats = await self.client.get_player_statistics(self.profile_id)
        except PlayHQApiError as err:
            raise UpdateFailed(str(err)) from err

        if not stats:
            return {"career": None, "current_season": None, "games_played": None}

        career = stats.get("careerStatistics") or {}
        career_totals = career.get("totalStatistics") or []
        career_clubs = [
            {
                "club_name": (c.get("club") or {}).get("name"),
                "statistics": _stats_dict(c.get("statistics"), self.sport),
            }
            for c in career.get("clubStatistics") or []
        ]

        seasons = stats.get("seasonStatistics") or []
        current_season = None
        if seasons:
            latest = seasons[-1]
            regs = latest.get("statistics") or []
            current_season = {
                "season_name": latest.get("name"),
                "registrations": [
                    {
                        "role": reg.get("role"),
                        "club_name": (reg.get("club") or {}).get("name"),
                        "statistics": _stats_dict(reg.get("totalStatistics"), self.sport),
                        "teams": [
                            {
                                "team_name": (t.get("team") or {}).get("name"),
                                "statistics": _stats_dict(t.get("totalStatistics"), self.sport),
                            }
                            for t in reg.get("teamStatistics") or []
                        ],
                    }
                    for reg in regs
                ],
            }

        return {
            "career": {
                "totals": _stats_dict(career_totals, self.sport),
                "clubs": career_clubs,
            },
            "current_season": current_season,
            "games_played": _stat(career_totals, "APPEARANCE"),
        }
