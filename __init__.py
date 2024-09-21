import logging

from .coordinator import InkbirdCoordinator

from .inkbird_ble_custom import InkbirdIamT1Device
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT]

_LOGGER = logging.getLogger(DOMAIN)
type InkbirdConfigEntry = ConfigEntry[InkbirdIamT1Device]

async def async_setup_entry(hass: HomeAssistant, entry: InkbirdConfigEntry) -> bool:
    """Set up INKBIRD BLE device from a config entry."""
    device: InkbirdIamT1Device | None = entry.data.get("device")
    assert device is not None
    _LOGGER.debug("Setting up %s entry", DOMAIN)

    coordinator: DataUpdateCoordinator = InkbirdCoordinator(hass, _LOGGER, DOMAIN, device)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: InkbirdConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)