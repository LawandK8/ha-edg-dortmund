"""Client for the EDG Dortmund waste calendar (kundenportal.edg.de).

The portal is a server-side rendered form (Athos WasteManagementServlet):
first letter of the street -> street -> house number -> list of dates.
Each step is a multipart POST that carries all hidden fields of the
previous page, so the client replays the form like a browser would.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import html
import re
import unicodedata

import aiohttp

BASE_URL = "https://kundenportal.edg.de/WasteManagementDortmund/WasteManagementServlet"
TIMEOUT = aiohttp.ClientTimeout(total=30)

_INPUT_RE = re.compile(r"<INPUT[^>]*>", re.I)
_NAME_RE = re.compile(r'NAME="([^"]*)"', re.I)
_VALUE_RE = re.compile(r'VALUE="([^"]*)"', re.I)
_SELECT_RE = re.compile(r'<SELECT NAME="([^"]*)"[^>]*>(.*?)</SELECT>', re.I | re.S)
_OPTION_RE = re.compile(r'<OPTION VALUE="([^"]*)"', re.I)
_CLUSTER_RE = re.compile(r'<SPAN class="cluster" ID="TermineCluster([^"]+)">', re.I)
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


class EdgError(Exception):
    """Base error."""


class EdgConnectionError(EdgError):
    """Portal not reachable or returned an unexpected page."""


class EdgAddressError(EdgError):
    """Street or house number not known to the portal."""


@dataclass
class WasteType:
    """One bin (fraction + size + rhythm) with its collection dates."""

    key: str
    name: str
    frequency: str
    bin_size: str
    dates: list[date] = field(default_factory=list)


def normalize(text: str) -> str:
    """Normalize street names so user input matches portal spelling."""
    text = html.unescape(text).replace("\xa0", " ").strip().lower()
    text = unicodedata.normalize("NFC", text)
    text = text.replace("ß", "ss")
    text = re.sub(r"strasse\b", "str.", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _text(value: str) -> str:
    return html.unescape(value).replace("\xa0", " ").strip()


def _fields(page: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for tag in _INPUT_RE.findall(page):
        name = _NAME_RE.search(tag)
        if name:
            value = _VALUE_RE.search(tag)
            data[name.group(1)] = html.unescape(value.group(1)) if value else ""
    return data


def _selects(page: str) -> dict[str, list[str]]:
    return {
        name: [html.unescape(v) for v in _OPTION_RE.findall(body) if v]
        for name, body in _SELECT_RE.findall(page)
    }


def _p(page: str, element_id: str) -> str:
    match = re.search(rf'<P ID="{re.escape(element_id)}">(.*?)</P>', page, re.S)
    return _text(match.group(1)) if match else ""


def parse_dates(page: str) -> list[WasteType]:
    """Parse the 'Terminliste' result page."""
    result: list[WasteType] = []
    for key in _CLUSTER_RE.findall(page):
        start = page.find(f'ID="TermineCluster{key}"')
        end = page.find("</UL>", start)
        block = page[start:end]
        dates = sorted(
            {
                date(int(y), int(m), int(d))
                for d, m, y in _DATE_RE.findall(block)
            }
        )
        result.append(
            WasteType(
                key=key,
                name=_p(block, f"Label{key}"),
                frequency=_p(block, f"Turnus{key}"),
                bin_size=_p(block, f"Tonnenart{key}"),
                dates=dates,
            )
        )
    return result


class EdgClient:
    """Walks through the portal form for one address."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        # The portal keeps state in a servlet session, so the caller must
        # pass a session with its own cookie jar.
        self._session = session
        self._page = ""

    async def _get_start(self) -> None:
        try:
            async with self._session.get(
                BASE_URL,
                params={"SubmitAction": "wasteDisposalServices", "InFrameMode": "TRUE"},
                timeout=TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                self._page = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EdgConnectionError(str(err)) from err
        if 'NAME="Ort"' not in self._page:
            raise EdgConnectionError("Unexpected start page")

    async def _submit(self, action: str, **values: str) -> None:
        data = _fields(self._page)
        data.update(values)
        data["SubmitAction"] = action
        form = aiohttp.FormData(default_to_multipart=True)
        for name, value in data.items():
            form.add_field(name, value)
        try:
            async with self._session.post(BASE_URL, data=form, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                self._page = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EdgConnectionError(str(err)) from err

    async def _streets_for_letter(self, letter: str) -> list[str]:
        await self._submit("CITYCHANGED", Ort=letter)
        return _selects(self._page).get("Strasse", [])

    async def _letter_for(self, street: str) -> str:
        """Return the 'Ort' option (first-letter group) for a street."""
        letters = _selects(self._page).get("Ort", [])
        first = street[:1].upper()
        if first in letters:
            return first
        # Streets like "I. Kampstr." or umlauts are grouped differently.
        for letter in letters:
            if street.upper().startswith(letter):
                return letter
        raise EdgAddressError(f"No street group for {street!r}")

    async def search_streets(self, query: str) -> list[str]:
        """Return portal street names matching the user input."""
        await self._get_start()
        wanted = normalize(query)
        letters = _selects(self._page).get("Ort", [])
        first = wanted[:1].upper()
        candidates = [l for l in letters if l.upper() == first or l.lower() == first.lower()]
        if not candidates:
            candidates = letters
        exact: list[str] = []
        partial: list[str] = []
        for letter in candidates:
            for street in await self._streets_for_letter(letter):
                norm = normalize(street)
                if norm == wanted:
                    exact.append(street)
                elif wanted in norm:
                    partial.append(street)
        return exact or partial

    async def house_numbers(self, street: str) -> list[str]:
        await self._get_start()
        letter = await self._letter_for(_text(street))
        await self._streets_for_letter(letter)
        await self._submit("STREETCHANGED", Ort=letter, Strasse=street)
        return [_text(n) for n in _selects(self._page).get("Hausnummer", [])]

    async def fetch(self, street: str, house_number: str) -> list[WasteType]:
        """Return all waste types with dates for an address."""
        await self._get_start()
        letter = await self._letter_for(_text(street))
        await self._streets_for_letter(letter)
        await self._submit("STREETCHANGED", Ort=letter, Strasse=street)
        numbers = _selects(self._page).get("Hausnummer", [])
        match = next(
            (n for n in numbers if normalize(n) == normalize(house_number)), None
        )
        if numbers and match is None:
            raise EdgAddressError(f"House number {house_number!r} not found")
        await self._submit(
            "forward", Ort=letter, Strasse=street, Hausnummer=match or ""
        )
        if _fields(self._page).get("PageName") != "Terminliste":
            raise EdgAddressError("Address not accepted by portal")
        return parse_dates(self._page)
