"""PlayHQ sensor: one entity per tracked team, state = current status."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GRADE_NAME, CONF_ORG_NAME, CONF_TEAM_ID, CONF_TEAM_NAME, DOMAIN, MANUFACTURER
from .coordinator import PlayHQCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: PlayHQCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PlayHQTeamSensor(coordinator, entry)])


class PlayHQTeamSensor(CoordinatorEntity[PlayHQCoordinator], SensorEntity):
    """Represents a single tracked PlayHQ team."""

    _attr_has_entity_name = True
    _attr_translation_key = "team_status"
    _attr_icon = "mdi:scoreboard-outline"

    def __init__(self, coordinator: PlayHQCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.data[CONF_TEAM_ID]}_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_TEAM_ID])},
            name=entry.data[CONF_TEAM_NAME],
            manufacturer=MANUFACTURER,
            model=entry.data.get(CONF_GRADE_NAME) or "Team",
            configuration_url="https://www.playhq.com",
        )

    @property
    def native_value(self) -> str:
        data = self.coordinator.data or {}
        if data.get("live"):
            return "live"
        if data.get("next"):
            return "scheduled"
        if data.get("last_result"):
            return "final"
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "team_name": self._entry.data.get(CONF_TEAM_NAME),
            "org_name": self._entry.data.get(CONF_ORG_NAME),
            "grade_name": self._entry.data.get(CONF_GRADE_NAME),
            "live": data.get("live"),
            "next_match": data.get("next"),
            "last_result": data.get("last_result"),
            "games_count": data.get("games_count"),
        }
