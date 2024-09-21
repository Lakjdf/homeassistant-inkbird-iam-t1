from datetime import timedelta
from bleak import BleakClient
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .inkbird_ble_custom.parser import ALARM_MODE, InkbirdIamT1Device, SAMPLING_INTERVAL

from .inkbird_ble_custom.const import CHAR_NOTIFY_UUID, CHAR_WRITE_UUID, CONNECT_WRITE_DATA

class InkbirdCoordinator(DataUpdateCoordinator[InkbirdIamT1Device]):
    def __init__(self, hass, logger, name, device: InkbirdIamT1Device):
        """
        Initialize the coordinator. 
        The udpate_interval is not used to poll updates,
        but for checking whether the device is still connected.
        """
        super().__init__(hass, logger, name=name, update_interval=timedelta(minutes=5))
        logger.info("Initializing InkbirdCoordinator with %s", device)
        # For some reason the ConfigEntry data is provided as a dict sometimes
        if isinstance(device, dict):
            device = InkbirdIamT1Device.from_dict(device)
        logger.info("initialized coordinator with %s", device)
        self.client = BleakClient(device.address)
        self.data = device

    async def _async_setup(self) -> None:
        """Establish connection and listen to notifications."""
        try:
            await self.client.connect()
            await self.client.start_notify(CHAR_NOTIFY_UUID, self._notification_handler)
            # Set device into "connected" state. Also leads to the current state being notified.
            await self.client.write_gatt_char(CHAR_WRITE_UUID, CONNECT_WRITE_DATA)
            self.logger.info("Connected to device and started notifications.")
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            raise UpdateFailed(f"Failed to connect: {e}")

    async def async_shutdown(self) -> None:
        """Disconnect and stop notifications."""
        try:
            if self.client.is_connected:
                await self.client.stop_notify(CHAR_NOTIFY_UUID)
                await self.client.disconnect()
                self.logger.info("Disconnected from Bluetooth device.")
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
        return await super().async_shutdown()

    def _notification_handler(self, _: int, data: bytearray):
        """Handle incoming notifications from the device."""
        self.logger.debug(f"Received notification : {data.hex()}")
        self.data.update(data)
        self.async_update_listeners()

    async def _async_update_data(self) -> InkbirdIamT1Device:
        """Reconnect if device disconnected."""
        if not self.client.is_connected:
            self.logger.info("Device disonnected. Reconnecting...")
            await self._async_setup()

        return self.data
    
    async def update_alarm_mode(self, mode: ALARM_MODE):
        try:
            self.logger.debug("Writing alarm mode    : %s", mode)
            await self.data.write_alarm_mode(self.client, mode)
        except Exception as e:
            raise UpdateFailed(f"Failed to write alarm mode: {e}")
        
    async def update_sampling_interval(self, interval: SAMPLING_INTERVAL):
        try:
            self.logger.debug("Writing interval      : %s", interval)
            await self.data.write_sampling_interval(self.client, interval)
        except Exception as e:
            raise UpdateFailed(f"Failed to write sampling inteval: {e}")