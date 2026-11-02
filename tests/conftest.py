import pytest
import pytest_socket

# Live tests against kundenportal.edg.de need real sockets.
pytest_socket.disable_socket = lambda *a, **k: None
pytest_socket.socket_allow_hosts = lambda *a, **k: None
pytest_plugins = ["pytest_homeassistant_custom_component"]

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
