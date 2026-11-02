"""Sensors: next collection date per waste type."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION
from .coordinator import EdgConfigEntry, EdgCoordinator

ICONS = {
    "Restabfall": "mdi:trash-can",
    "Bioabfall": "mdi:leaf",
    "Altpapier": "mdi:newspaper-variant-outline",
    "Wertstoffe": "mdi:recycle",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EdgConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def add_new_types() -> None:
        new = [key for key in coordinator.data if key not in known]
        known.update(new)
        if new:
            async_add_entities(WasteSensor(coordinator, key) for key in new)

    async_add_entities([NextCollectionSensor(coordinator)])
    add_new_types()
    entry.async_on_unload(coordinator.async_add_listener(add_new_types))


def _days_until(day: date | None) -> int | None:
    return (day - dt_util.now().date()).days if day else None


class WasteSensor(CoordinatorEntity[EdgCoordinator], SensorEntity):
    """Next collection date of one bin."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: EdgCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        waste = coordinator.data[key]
        # Two bins of the same kind (e.g. 120 l and 240 l) get the size appended.
        same_name = [w for w in coordinator.data.values() if w.name == waste.name]
        self._attr_name = (
            f"{waste.name} {waste.bin_size}" if len(same_name) > 1 else waste.name
        )
        self._attr_icon = ICONS.get(waste.name, "mdi:trash-can-outline")
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return super().available and self._key in self.coordinator.data

    @property
    def native_value(self) -> date | None:
        upcoming = self.coordinator.upcoming(self._key)
        return upcoming[0] if upcoming else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        waste = self.coordinator.data[self._key]
        upcoming = self.coordinator.upcoming(self._key)
        return {
            "days_until": _days_until(upcoming[0] if upcoming else None),
            "upcoming": [d.isoformat() for d in upcoming],
            "frequency": waste.frequency,
            "bin_size": waste.bin_size,
        }


class NextCollectionSensor(CoordinatorEntity[EdgCoordinator], SensorEntity):
    """Next collection of any bin."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_collection"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: EdgCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_next"
        self._attr_device_info = coordinator.device_info

    def _next(self) -> tuple[date | None, list[str]]:
        first: date | None = None
        names: list[str] = []
        for key, waste in self.coordinator.data.items():
            upcoming = self.coordinator.upcoming(key)
            if not upcoming:
                continue
            if first is None or upcoming[0] < first:
                first, names = upcoming[0], [waste.name]
            elif upcoming[0] == first:
                names.append(waste.name)
        return first, names

    @property
    def native_value(self) -> date | None:
        return self._next()[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        first, names = self._next()
        return {"days_until": _days_until(first), "types": names}
