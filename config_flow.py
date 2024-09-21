import logging
from typing import Any

from .inkbird_ble_custom import InkbirdIamT1Device, InkbirdIamT1DeviceData
import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import AbortFlow, FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(DOMAIN)

SELECTION_TITLE = "Select a device:"

class InspectorBLEConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, InkbirdIamT1Device] = {}

    async def _get_device_data(self, service_info: BluetoothServiceInfo) -> InkbirdIamT1Device:
        ble_device = bluetooth.async_ble_device_from_address(self.hass, service_info.address)
        if ble_device is None:
            raise AbortFlow("cannot_connect")

        deviceData = InkbirdIamT1DeviceData(_LOGGER)
        return await deviceData.update_device_only(ble_device)
    
    async def _update_device_data(self, service_info: BluetoothServiceInfo):
        try:
            device = await self._get_device_data(service_info)
        except AbortFlow:
            return self.async_abort(reason="cannot_connect")
        except Exception:
            return self.async_abort(reason="unknown")

        self._discovered_devices[device.address] = device
        self.context["title_placeholders"] = {"name": device.name()}
    
    def _show_selection_form(self, step_id: str) -> FlowResult:
        default_address = next(iter(self._discovered_devices.values())).address if self._discovered_devices else None
        titles = {device.address: device.name() for device in self._discovered_devices.values()}
        self._set_confirm_only()
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(SELECTION_TITLE, default=default_address): vol.In(titles),
                }
            ),
        )

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfo) -> FlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Discovered BLE device: %s", discovery_info.name)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        await self._update_device_data(discovery_info)
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        _LOGGER.debug("async_step_bluetooth_confirm %s %s", user_input, self._discovered_devices)
        """Handle the bluetooth confirmation step."""
        if user_input is None or SELECTION_TITLE not in user_input:
            return self._show_selection_form("bluetooth_confirm")
        else:
            address = user_input[SELECTION_TITLE]
            return self.async_create_entry(title=address, data={"device": self._discovered_devices[address]})

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is None or SELECTION_TITLE not in user_input:
            current_addresses = self._async_current_ids()
            for discovery_info in async_discovered_service_info(self.hass):
                address = discovery_info.address
                if address in current_addresses or address in self._discovered_devices:
                    _LOGGER.debug("Detected a device that's already configured: %s", address)
                    continue

                if not discovery_info.advertisement.local_name:
                    continue
                if not discovery_info.advertisement.local_name.startswith("Ink@IAM-T"):
                    continue

                await self._update_device_data(discovery_info)

            if not self._discovered_devices:
                return self.async_abort(reason="no_devices_found")

            return self._show_selection_form("user")
        
        else:
            address = user_input[SELECTION_TITLE]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            device = self._discovered_devices[address]
            self.context["title_placeholders"] = {"name": device.name()}
            return self.async_create_entry(title=address, data={"device": device})