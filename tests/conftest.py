import pytest
import pytest_socket

# Live tests against kundenportal.edg.de need real sockets.
pytest_socket.disable_socket = lambda *a, **k: None
pytest_socket.socket_allow_hosts = lambda *a, **k: None
pytest_plugins = ["pytest_homeassistant_custom_component"]

# Import this repo's custom_components before the plugin's own testing_config
# package can claim the name, otherwise HA does not find edg_dortmund.
import custom_components  # noqa: E402,F401

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
