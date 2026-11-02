"""Calendar with all collection dates."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .coordinator import EdgConfigEntry, EdgCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EdgConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([EdgCalendar(entry.runtime_data)])


class EdgCalendar(CoordinatorEntity[EdgCoordinator], CalendarEntity):
    """All bins of one address as all-day events."""

    _attr_has_entity_name = True
    _attr_translation_key = "calendar"

    def __init__(self, coordinator: EdgCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_calendar"
        self._attr_device_info = coordinator.device_info

    def _events(self) -> list[CalendarEvent]:
        events = [
            CalendarEvent(
                start=day,
                end=day + timedelta(days=1),
                summary=waste.name,
                description=f"{waste.bin_size}, {waste.frequency}",
                location=self.coordinator.config_entry.title,
            )
            for waste in self.coordinator.data.values()
            for day in waste.dates
        ]
        return sorted(events, key=lambda e: (e.start, e.summary))

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        return next((e for e in self._events() if e.start >= today), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        start = dt_util.as_local(start_date).date()
        end = dt_util.as_local(end_date).date()
        return [e for e in self._events() if e.end > start and e.start <= end]
