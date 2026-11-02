"""EDG Abfallkalender Dortmund."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .coordinator import EdgConfigEntry, EdgCoordinator

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: EdgConfigEntry) -> bool:
    coordinator = EdgCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # "Next date" and "days until" change at midnight even without new data.
    @callback
    def _midnight(_now: datetime) -> None:
        coordinator.async_update_listeners()

    entry.async_on_unload(
        async_track_time_change(hass, _midnight, hour=0, minute=0, second=5)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EdgConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
