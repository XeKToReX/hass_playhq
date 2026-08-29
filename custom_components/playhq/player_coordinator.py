"""Data update coordinator for a single tracked PlayHQ player profile."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PlayHQApiError, PlayHQClient
from .const import DOMAIN, PLAYER_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


def _stat_key(stat: dict) -> Any:
    details = stat.get("details") or []
    return details[0].get("value") if details else None


def _stat(stats_list: list[dict] | None, key: str) -> Any:
    for s in stats_list or []:
        if _stat_key(s) == key:
            return s.get("count")
    return None


class PlayHQPlayerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls a player's public career/season statistics."""

    def __init__(self, hass: HomeAssistant, profile_id: str, player_name: str, tenant: str) -> None:
        self.profile_id = profile_id
        self.player_name = player_name
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
                "statistics": {
                    _stat_key(s): s.get("count") for s in c.get("statistics") or []
                },
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
                        "statistics": {
                            _stat_key(s): s.get("count")
                            for s in reg.get("totalStatistics") or []
                        },
                        "teams": [
                            {
                                "team_name": (t.get("team") or {}).get("name"),
                                "statistics": {
                                    _stat_key(s): s.get("count")
                                    for s in t.get("totalStatistics") or []
                                },
                            }
                            for t in reg.get("teamStatistics") or []
                        ],
                    }
                    for reg in regs
                ],
            }

        return {
            "career": {
                "totals": {_stat_key(s): s.get("count") for s in career_totals},
                "clubs": career_clubs,
            },
            "current_season": current_season,
            "games_played": _stat(career_totals, "APPEARANCE"),
        }
