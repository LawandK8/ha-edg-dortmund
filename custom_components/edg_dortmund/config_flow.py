"""Config flow: the user types street and house number.

If the street is ambiguous or the house number is written differently on
the portal (e.g. "11 -13"), the flow offers a dropdown to pick from.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import EdgAddressError, EdgClient, EdgConnectionError, normalize
from .const import CONF_HOUSE_NUMBER, CONF_STREET, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _label(value: str) -> str:
    return value.replace("\xa0", " ")


def _dropdown(values: list[str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[SelectOptionDict(value=v, label=_label(v)) for v in values],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class EdgConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up one address."""

    VERSION = 1

    def __init__(self) -> None:
        self._streets: list[str] = []
        self._street = ""
        self._house_numbers: list[str] = []
        self._house_number = ""

    async def _run(self, method: str, *args: str) -> Any:
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
            return await getattr(EdgClient(session), method)(*args)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._house_number = user_input[CONF_HOUSE_NUMBER].strip()
            try:
                self._streets = await self._run("search_streets", user_input[CONF_STREET])
            except EdgConnectionError:
                errors["base"] = "cannot_connect"
            else:
                if not self._streets:
                    errors[CONF_STREET] = "street_not_found"
                elif len(self._streets) == 1:
                    self._street = self._streets[0]
                    return await self._resolve_house_number()
                else:
                    return await self.async_step_street()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_STREET): str,
                        vol.Required(CONF_HOUSE_NUMBER): str,
                    }
                ),
                user_input,
            ),
            errors=errors,
        )

    async def async_step_street(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Several streets matched the input."""
        if user_input is not None:
            self._street = user_input[CONF_STREET]
            return await self._resolve_house_number()
        return self.async_show_form(
            step_id="street",
            data_schema=vol.Schema({vol.Required(CONF_STREET): _dropdown(self._streets)}),
        )

    async def _resolve_house_number(self) -> ConfigFlowResult:
        try:
            self._house_numbers = await self._run("house_numbers", self._street)
        except EdgConnectionError:
            return self.async_abort(reason="cannot_connect")
        except EdgAddressError:
            return self.async_abort(reason="street_not_found")

        if not self._house_numbers:
            return await self._create("")
        match = next(
            (
                n
                for n in self._house_numbers
                if normalize(n) == normalize(self._house_number)
            ),
            None,
        )
        if match is not None:
            return await self._create(match)
        return await self.async_step_house_number()

    async def async_step_house_number(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """House number not found as typed: let the user pick."""
        if user_input is not None:
            return await self._create(user_input[CONF_HOUSE_NUMBER])
        return self.async_show_form(
            step_id="house_number",
            data_schema=vol.Schema(
                {vol.Required(CONF_HOUSE_NUMBER): _dropdown(self._house_numbers)}
            ),
            description_placeholders={
                "street": _label(self._street),
                "house_number": self._house_number,
            },
        )

    async def _create(self, house_number: str) -> ConfigFlowResult:
        await self.async_set_unique_id(
            f"{normalize(self._street)}|{normalize(house_number)}"
        )
        self._abort_if_unique_id_configured()
        try:
            types = await self._run("fetch", self._street, house_number)
        except EdgConnectionError:
            return self.async_abort(reason="cannot_connect")
        except EdgAddressError:
            _LOGGER.exception("EDG portal rejected address")
            return self.async_abort(reason="street_not_found")
        if not types:
            return self.async_abort(reason="no_dates")
        title = f"{_label(self._street)} {house_number}".strip()
        return self.async_create_entry(
            title=title,
            data={CONF_STREET: self._street, CONF_HOUSE_NUMBER: house_number},
        )
