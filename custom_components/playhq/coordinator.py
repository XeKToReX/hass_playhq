"""Data update coordinator for a single tracked PlayHQ team."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    PlayHQApiError,
    PlayHQClient,
    extract_score,
    pick_logo_url,
    stat,
    venue_text,
)
from .const import DOMAIN, IDLE_UPDATE_INTERVAL, LIVE_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

QUARTER_LABELS = {"FIRST_QTR": "Q1", "SECOND_QTR": "Q2", "THIRD_QTR": "Q3", "FOURTH_QTR": "Q4"}


class PlayHQCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls a team's fixture (and live game clock, when relevant)."""

    def __init__(self, hass: HomeAssistant, team_id: str, team_name: str, tenant: str) -> None:
        self.team_id = team_id
        self.team_name = team_name
        self.client = PlayHQClient(async_get_clientsession(hass), tenant=tenant)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{team_name}",
            update_interval=timedelta(seconds=IDLE_UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            games = await self.client.get_all_games(self.team_id)
        except PlayHQApiError as err:
            raise UpdateFailed(str(err)) from err

        live_games = [g for g in games if (g.get("status") or {}).get("value") == "IN_PROGRESS"]
        finals = [g for g in games if (g.get("status") or {}).get("value") == "FINAL"]
        upcoming = [
            g for g in games
            if (g.get("status") or {}).get("value") not in ("IN_PROGRESS", "FINAL")
        ]

        live_data = None
        if live_games:
            game = live_games[0]
            try:
                live_detail = await self.client.get_live_detail(game["id"])
            except PlayHQApiError as err:
                _LOGGER.warning("PlayHQ live detail fetch failed for %s: %s", game["id"], err)
                live_detail = None
            live_data = self._build_live(game, live_detail)
            self.update_interval = timedelta(seconds=LIVE_UPDATE_INTERVAL)
        else:
            self.update_interval = timedelta(seconds=IDLE_UPDATE_INTERVAL)

        next_game = None
        if upcoming:
            next_game = min(upcoming, key=lambda g: (g.get("dates") or ["9999"])[0])

        last_result = None
        if finals:
            last_result = max(finals, key=lambda g: (g.get("dates") or [""])[0])

        return {
            "team_name": self.team_name,
            "live": live_data,
            "next": self._build_upcoming(next_game) if next_game else None,
            "last_result": self._build_result(last_result) if last_result else None,
            "games_count": len(games),
        }

    @staticmethod
    def _team_summary(team: dict) -> dict:
        return {"name": team.get("name"), "logo": pick_logo_url(team)}

    def _build_upcoming(self, game: dict) -> dict:
        home, away = game.get("home") or {}, game.get("away") or {}
        allocation = game.get("allocation") or {}
        return {
            "id": game.get("id"),
            "dates": game.get("dates") or [],
            "time": allocation.get("time"),
            "venue": venue_text(game),
            "home": self._team_summary(home),
            "away": self._team_summary(away),
        }

    def _build_result(self, game: dict) -> dict:
        home, away = game.get("home") or {}, game.get("away") or {}
        home_stats, away_stats, _, _ = extract_score(game.get("result"))
        return {
            "id": game.get("id"),
            "dates": game.get("dates") or [],
            "home": self._team_summary(home),
            "away": self._team_summary(away),
            "home_score": stat(home_stats, "TOTAL_SCORE"),
            "away_score": stat(away_stats, "TOTAL_SCORE"),
        }

    def _build_live(self, game: dict, live_detail: dict | None) -> dict:
        home, away = game.get("home") or {}, game.get("away") or {}
        result = live_detail.get("result") if live_detail else game.get("result")
        clock = (live_detail or {}).get("clock") or {}
        home_stats, away_stats, home_periods, away_periods = extract_score(result)

        period_label = clock.get("period")
        if not period_label:
            current_period = (result or {}).get("currentPeriod") or {}
            period_label = QUARTER_LABELS.get(current_period.get("value"), current_period.get("value"))

        return {
            "id": game.get("id"),
            "venue": venue_text(game),
            "home": self._team_summary(home),
            "away": self._team_summary(away),
            "home_score": stat(home_stats, "TOTAL_SCORE"),
            "away_score": stat(away_stats, "TOTAL_SCORE"),
            "home_goals": stat(home_stats, "TOTAL_GOALS"),
            "home_behinds": stat(home_stats, "TOTAL_BEHINDS"),
            "away_goals": stat(away_stats, "TOTAL_GOALS"),
            "away_behinds": stat(away_stats, "TOTAL_BEHINDS"),
            "period": period_label,
            "clock_time": clock.get("time"),
            "clock_paused": clock.get("status") not in (None, "RESUME"),
            "home_periods": home_periods,
            "away_periods": away_periods,
            "updated_at": (live_detail or {}).get("updatedAt"),
        }
