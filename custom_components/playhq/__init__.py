"""The PlayHQ integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_KIND,
    CONF_PLAYER_NAME,
    CONF_PROFILE_ID,
    CONF_SPORT,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    CONF_TENANT,
    DEFAULT_SPORT,
    DEFAULT_TENANT,
    DOMAIN,
    KIND_PLAYER,
    PLATFORMS,
)
from .coordinator import PlayHQCoordinator
from .player_coordinator import PlayHQPlayerCoordinator

_LOGGER = logging.getLogger(__name__)

CARD_URL_BASE = f"/{DOMAIN}_files"
CARD_URL = f"{CARD_URL_BASE}/playhq-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the bundled Lovelace card and register it as a dashboard resource."""
    card_path = str(Path(__file__).parent / "www" / "playhq-card.js")

    if hasattr(hass.http, "async_register_static_paths"):
        # HA >= 2024.7
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, card_path, cache_headers=False)]
        )
    else:
        hass.http.register_static_path(CARD_URL, card_path, cache_headers=False)

    if hass.is_running:
        hass.async_create_task(_async_register_card_resource(hass))
    else:
        @callback
        def _on_started(_event: object) -> None:
            hass.async_create_task(_async_register_card_resource(hass))

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)
    return True


async def _async_register_card_resource(hass: HomeAssistant) -> None:
    """Add the card to the storage-mode Lovelace resources collection, if available.

    This is what actually makes a dashboard load the card's JS - simply serving the
    file (above) or using add_extra_js_url is not reliable for non-default/
    storage-mode dashboards in modern Home Assistant.
    """
    lovelace_data = hass.data.get("lovelace")
    resources = getattr(lovelace_data, "resources", None)
    if resources is None:
        _LOGGER.warning(
            "Could not auto-register the PlayHQ card resource (Lovelace not in "
            "storage mode yet, or not loaded). Add it manually: Settings > "
            "Dashboards > Resources > Add Resource, URL '%s', type JavaScript Module.",
            CARD_URL,
        )
        return

    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        for item in resources.async_items():
            if item.get("url") == CARD_URL:
                return

        await resources.async_create_item({"res_type": "module", "url": CARD_URL})
        _LOGGER.info("Registered PlayHQ card as a Lovelace resource: %s", CARD_URL)
    except Exception:  # noqa: BLE001 - best-effort; never block startup on this
        _LOGGER.exception(
            "Failed to auto-register the PlayHQ card resource. Add it manually: "
            "Settings > Dashboards > Resources > Add Resource, URL '%s', type "
            "JavaScript Module.",
            CARD_URL,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.data.get(CONF_KIND) == KIND_PLAYER:
        coordinator = PlayHQPlayerCoordinator(
            hass,
            profile_id=entry.data[CONF_PROFILE_ID],
            player_name=entry.data[CONF_PLAYER_NAME],
            tenant=entry.data.get(CONF_TENANT, DEFAULT_TENANT),
        )
    else:
        coordinator = PlayHQCoordinator(
            hass,
            team_id=entry.data[CONF_TEAM_ID],
            team_name=entry.data[CONF_TEAM_NAME],
            tenant=entry.data.get(CONF_TENANT, DEFAULT_TENANT),
            sport=entry.data.get(CONF_SPORT, DEFAULT_SPORT),
        )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
