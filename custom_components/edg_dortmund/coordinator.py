"""Data update coordinator for EDG Abfallkalender."""

from __future__ import annotations

from datetime import date
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EdgClient, EdgError, WasteType
from .const import CONF_HOUSE_NUMBER, CONF_STREET, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type EdgConfigEntry = ConfigEntry[EdgCoordinator]


class EdgCoordinator(DataUpdateCoordinator[dict[str, WasteType]]):
    """Fetches all collection dates for one address."""

    config_entry: EdgConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EdgConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=UPDATE_INTERVAL,
        )
        self.street: str = entry.data[CONF_STREET]
        self.house_number: str = entry.data[CONF_HOUSE_NUMBER]
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"EDG Abfall {entry.title}",
            manufacturer="EDG Entsorgung Dortmund GmbH",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.edg.de/abfallkalender",
        )

    async def _async_update_data(self) -> dict[str, WasteType]:
        # Own cookie jar: the portal tracks the form steps in a servlet session.
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
            try:
                types = await EdgClient(session).fetch(self.street, self.house_number)
            except EdgError as err:
                raise UpdateFailed(f"EDG Abfallkalender: {err}") from err
        return {waste.key: waste for waste in types}

    def upcoming(self, key: str) -> list[date]:
        """Collection dates from today on for one waste type."""
        waste = self.data.get(key)
        if waste is None:
            return []
        today = dt_util.now().date()
        return [d for d in waste.dates if d >= today]
