from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

DOMAIN = "edg_dortmund"

async def test_flow_and_entities(hass, socket_enabled):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert r["type"] is FlowResultType.FORM
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"street": "nichtda", "house_number": "1"})
    assert r["errors"] == {"street": "street_not_found"}
    # "11" is listed as "11 -13" -> dropdown step
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"street": "westenhellweg", "house_number": "11"})
    assert r["step_id"] == "house_number", r
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"house_number": "11 -13"})
    assert r["type"] is FlowResultType.CREATE_ENTRY, r
    print("TITLE", r["title"], r["data"])
    await hass.async_block_till_done()
    for s in sorted(hass.states.async_all(), key=lambda s: s.entity_id):
        print(s.entity_id, s.state, dict(s.attributes))
    assert hass.states.get("sensor.edg_abfall_westenhellweg_11_13_restabfall").state.startswith("2026")

async def test_hohe_strasse(hass, socket_enabled):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"street": "Baackweg", "house_number": "1"})
    assert r["type"] is FlowResultType.CREATE_ENTRY, r
    await hass.async_block_till_done()
    for s in hass.states.async_all(): print(s.entity_id, s.state)
    nxt = hass.states.get("sensor.edg_abfall_baackweg_1_next_collection")
    assert " · " in nxt.state and nxt.attributes["date"].startswith("2026")
