"""The PlayHQ integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_TEAM_ID, CONF_TEAM_NAME, CONF_TENANT, DEFAULT_TENANT, DOMAIN, PLATFORMS
from .coordinator import PlayHQCoordinator

_LOGGER = logging.getLogger(__name__)

CARD_URL_BASE = f"/{DOMAIN}_files"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the bundled Lovelace card and register it as a frontend resource."""
    card_path = str(Path(__file__).parent / "www" / "playhq-card.js")
    card_url = f"{CARD_URL_BASE}/playhq-card.js"

    if hasattr(hass.http, "async_register_static_paths"):
        # HA >= 2024.7
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(card_url, card_path, cache_headers=False)]
        )
    else:
        hass.http.register_static_path(card_url, card_path, cache_headers=False)

    from homeassistant.components.frontend import add_extra_js_url

    add_extra_js_url(hass, card_url)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = PlayHQCoordinator(
        hass,
        team_id=entry.data[CONF_TEAM_ID],
        team_name=entry.data[CONF_TEAM_NAME],
        tenant=entry.data.get(CONF_TENANT, DEFAULT_TENANT),
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
