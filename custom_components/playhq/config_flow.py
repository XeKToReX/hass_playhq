"""Config flow for PlayHQ: search a club, then pick a team to track."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlayHQApiError, PlayHQClient, pick_active_season
from .const import (
    CONF_GRADE_NAME,
    CONF_ORG_ID,
    CONF_ORG_NAME,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    CONF_TENANT,
    DEFAULT_TENANT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class PlayHQConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Search PlayHQ for a club, then choose one of its teams."""

    VERSION = 1

    def __init__(self) -> None:
        self._orgs: list[dict] = []
        self._teams: list[dict] = []
        self._selected_org: dict | None = None

    def _client(self) -> PlayHQClient:
        return PlayHQClient(async_get_clientsession(self.hass), tenant=DEFAULT_TENANT)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
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
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

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
            await self.async_set_unique_id(team["id"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=team["name"],
                data={
                    CONF_TENANT: DEFAULT_TENANT,
                    CONF_ORG_ID: self._selected_org["routingCode"],
                    CONF_ORG_NAME: self._selected_org["name"],
                    CONF_TEAM_ID: team["id"],
                    CONF_TEAM_NAME: team["name"],
                    CONF_GRADE_NAME: (team.get("grade") or {}).get("name"),
                },
            )

        schema = vol.Schema({vol.Required("team"): vol.In(team_choices)})
        return self.async_show_form(step_id="team", data_schema=schema, errors=errors)
