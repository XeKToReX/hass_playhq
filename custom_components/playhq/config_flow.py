"""Config flow for PlayHQ: track a team (search a club) or a player (by profile ID)."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlayHQApiError, PlayHQClient, pick_active_season
from .const import (
    CONF_GRADE_NAME,
    CONF_KIND,
    CONF_ORG_ID,
    CONF_ORG_NAME,
    CONF_PLAYER_NAME,
    CONF_PROFILE_ID,
    CONF_SPORT,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    CONF_TENANT,
    DEFAULT_TENANT,
    DOMAIN,
    KIND_PLAYER,
    KIND_TEAM,
    SPORT_AFL,
    SPORT_BASKETBALL,
    SPORT_CRICKET,
)

_LOGGER = logging.getLogger(__name__)

CRICKET_DEFAULT_TENANT = "cricket-australia"


class PlayHQConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Track a PlayHQ team (search a club) or a player (by profile ID)."""

    VERSION = 1

    def __init__(self) -> None:
        self._orgs: list[dict] = []
        self._teams: list[dict] = []
        self._selected_org: dict | None = None
        self._sport: str = SPORT_AFL
        self._tenant: str = DEFAULT_TENANT

    def _client(self) -> PlayHQClient:
        return PlayHQClient(async_get_clientsession(self.hass), tenant=self._tenant)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        return self.async_show_menu(
            step_id="user",
            menu_options=["sport_afl", "sport_basketball", "sport_cricket"],
        )

    async def async_step_sport_afl(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        self._sport = SPORT_AFL
        self._tenant = DEFAULT_TENANT
        return await self.async_step_kind()

    async def async_step_sport_basketball(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        self._sport = SPORT_BASKETBALL
        return await self.async_step_tenant()

    async def async_step_sport_cricket(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        self._sport = SPORT_CRICKET
        return await self.async_step_tenant()

    async def async_step_tenant(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Basketball and cricket are run by separate state/national bodies, each its own PlayHQ tenant."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._tenant = user_input["tenant"].strip()
            return await self.async_step_kind()

        if self._sport == SPORT_CRICKET:
            schema = vol.Schema({vol.Required("tenant", default=CRICKET_DEFAULT_TENANT): str})
        else:
            schema = vol.Schema({vol.Required("tenant"): str})
        return self.async_show_form(
            step_id="tenant",
            data_schema=schema,
            errors=errors,
            description_placeholders={"sport": self._sport},
        )

    async def async_step_kind(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if self._sport == SPORT_CRICKET:
            # Cricket player profiles live on Cricket Australia's own site
            # (play.cricket.com.au), not PlayHQ's shared profile system - there's
            # no publicProfileStatistics data to query for a cricket.com.au profile ID.
            menu_options = ["track_team"]
            note = (
                "Player tracking isn't available for cricket - cricket player "
                "profiles live on Cricket Australia's own site "
                "(play.cricket.com.au), not PlayHQ's shared profile system."
            )
        else:
            menu_options = ["track_team", "track_player"]
            note = ""
        return self.async_show_menu(
            step_id="kind",
            menu_options=menu_options,
            description_placeholders={"note": note},
        )

    # -- Team flow -----------------------------------------------------
    async def async_step_track_team(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            query_text = user_input["club_search"].strip()
            try:
                self._orgs = await self._client().search_organisations(query_text)
            except PlayHQApiError as err:
                _LOGGER.warning("PlayHQ search failed: %s", err)
                errors["base"] = "search_failed"
            else:
                if not self._orgs:
                    errors["base"] = "no_results"
                else:
                    return await self.async_step_org()

        schema = vol.Schema({vol.Required("club_search"): str})
        return self.async_show_form(step_id="track_team", data_schema=schema, errors=errors)

    async def async_step_org(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        org_choices = {org["routingCode"]: f'{org["name"]} ({org["type"]})' for org in self._orgs}

        if user_input is not None:
            self._selected_org = next(o for o in self._orgs if o["routingCode"] == user_input["organisation"])
            try:
                teams = await self._load_teams(self._selected_org["routingCode"])
            except PlayHQApiError as err:
                _LOGGER.warning("PlayHQ team lookup failed: %s", err)
                errors["base"] = "team_lookup_failed"
            else:
                if not teams:
                    errors["base"] = "no_teams"
                else:
                    self._teams = teams
                    return await self.async_step_team()

        schema = vol.Schema({vol.Required("organisation"): vol.In(org_choices)})
        return self.async_show_form(step_id="org", data_schema=schema, errors=errors)

    async def _load_teams(self, org_id: str) -> list[dict]:
        client = self._client()
        competitions = await client.get_competitions(org_id)
        teams: list[dict] = []
        for comp in competitions:
            season = pick_active_season(comp)
            if not season:
                continue
            comp_teams = await client.get_teams(org_id, season["id"])
            for team in comp_teams:
                team = dict(team)
                team["_competition_name"] = comp["name"]
                teams.append(team)
        return teams

    async def async_step_team(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        team_choices = {}
        for team in self._teams:
            grade = (team.get("grade") or {}).get("name")
            label = team["name"]
            if grade:
                label = f'{label} - {grade}'
            team_choices[team["id"]] = label

        if user_input is not None:
            team = next(t for t in self._teams if t["id"] == user_input["team"])
            await self.async_set_unique_id(f"team_{self._tenant}_{team['id']}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=team["name"],
                data={
                    CONF_KIND: KIND_TEAM,
                    CONF_SPORT: self._sport,
                    CONF_TENANT: self._tenant,
                    CONF_ORG_ID: self._selected_org["routingCode"],
                    CONF_ORG_NAME: self._selected_org["name"],
                    CONF_TEAM_ID: team["id"],
                    CONF_TEAM_NAME: team["name"],
                    CONF_GRADE_NAME: (team.get("grade") or {}).get("name"),
                },
            )

        schema = vol.Schema({vol.Required("team"): vol.In(team_choices)})
        return self.async_show_form(step_id="team", data_schema=schema, errors=errors)

    # -- Player flow -----------------------------------------------------
    async def async_step_track_player(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """PlayHQ has no anonymous player search, so the user supplies the profile ID directly.

        It's the UUID visible in the URL of a public PlayHQ player-profile page
        (e.g. https://www.playhq.com/.../profile/<this-part>), or found via a
        game centre lineup.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            profile_id = user_input["profile_id"].strip()
            player_name = user_input["player_name"].strip()
            try:
                stats = await self._client().get_player_statistics(profile_id)
            except PlayHQApiError as err:
                _LOGGER.warning("PlayHQ player lookup failed: %s", err)
                errors["base"] = "player_lookup_failed"
            else:
                if stats is None:
                    errors["base"] = "player_not_found"
                else:
                    await self.async_set_unique_id(f"player_{self._tenant}_{profile_id}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=player_name,
                        data={
                            CONF_KIND: KIND_PLAYER,
                            CONF_SPORT: self._sport,
                            CONF_TENANT: self._tenant,
                            CONF_PROFILE_ID: profile_id,
                            CONF_PLAYER_NAME: player_name,
                        },
                    )

        schema = vol.Schema({vol.Required("profile_id"): str, vol.Required("player_name"): str})
        return self.async_show_form(step_id="track_player", data_schema=schema, errors=errors)
