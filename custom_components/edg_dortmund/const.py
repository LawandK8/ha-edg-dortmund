"""Constants for the EDG Abfallkalender integration."""

from datetime import timedelta

DOMAIN = "edg_dortmund"

CONF_STREET = "street"
CONF_HOUSE_NUMBER = "house_number"

UPDATE_INTERVAL = timedelta(hours=12)

ATTRIBUTION = "Daten: EDG Entsorgung Dortmund GmbH"
