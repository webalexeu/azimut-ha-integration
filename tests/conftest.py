"""Fixtures for Azimut Energy integration tests."""
from __future__ import annotations

import importlib.util
import sys
import types
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.const import CONF_HOST

# Add the workspace root to Python path for imports
workspace_root = Path(__file__).parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# Set up custom_components.azimut_energy import structure
# This allows tests to import from custom_components.azimut_energy
# even though the code is in the root directory

# Create custom_components module structure
if "custom_components" not in sys.modules:
    custom_components = types.ModuleType("custom_components")
    sys.modules["custom_components"] = custom_components

if "custom_components.azimut_energy" not in sys.modules:
    azimut_energy = types.ModuleType("custom_components.azimut_energy")
    azimut_energy.__path__ = []  # Make it a package
    sys.modules["custom_components.azimut_energy"] = azimut_energy

    # Load root-level modules and attach them to custom_components.azimut_energy
    module_names = ["const", "mqtt_client", "sensor", "config_flow", "diagnostics"]
    for module_name in module_names:
        spec = importlib.util.spec_from_file_location(
            f"custom_components.azimut_energy.{module_name}",
            workspace_root / f"{module_name}.py",
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"custom_components.azimut_energy.{module_name}"] = module
            spec.loader.exec_module(module)
            setattr(azimut_energy, module_name, module)

    # Load __init__.py
    init_spec = importlib.util.spec_from_file_location(
        "custom_components.azimut_energy.__init__",
        workspace_root / "__init__.py",
    )
    if init_spec and init_spec.loader:
        init_module = importlib.util.module_from_spec(init_spec)
        sys.modules["custom_components.azimut_energy.__init__"] = init_module
        init_spec.loader.exec_module(init_module)
        azimut_energy.async_setup_entry = init_module.async_setup_entry

# Import after module setup
from custom_components.azimut_energy.const import CONF_SERIAL, DOMAIN  # noqa: E402, I001


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.azimut_energy.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_mqtt_client() -> Generator[MagicMock, None, None]:
    """Mock the AzimutMQTTClient."""
    with patch(
        "custom_components.azimut_energy.mqtt_client.AzimutMQTTClient",
        autospec=True,
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()
        mock_client.listen = AsyncMock()
        mock_client.listen_with_reconnect = AsyncMock()
        mock_client.is_connected = True
        mock_client.set_discovery_callback = MagicMock()
        mock_client.set_state_callback = MagicMock()
        mock_client.set_connection_callback = MagicMock()
        yield mock_client


@pytest.fixture
def mock_mqtt_client_cannot_connect() -> Generator[MagicMock, None, None]:
    """Mock the AzimutMQTTClient that cannot connect."""
    with patch(
        "custom_components.azimut_energy.mqtt_client.AzimutMQTTClient",
        autospec=True,
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=False)
        mock_client.disconnect = AsyncMock()
        mock_client.is_connected = False
        yield mock_client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_SERIAL: "504589",
    }
    entry.options = {}
    entry.unique_id = "azimut_energy_504589"
    entry.title = "Azimut Battery 504589"
    return entry
