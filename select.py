from .coordinator import InkbirdCoordinator

from .inkbird_ble_custom import InkbirdIamT1Device, ALARM_MODE, SAMPLING_INTERVAL

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import InkbirdConfigEntry

async def async_setup_entry(
    hass: HomeAssistant,
    entry: InkbirdConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the INKBIRD BLE sensors."""
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        InkbirdAlarmSelectEntity(coordinator, coordinator.data),
        InkbirdSamplingIntervalSelectEntity(coordinator, coordinator.data)
    ]
    async_add_entities(entities)

class InkbirdAlarmSelectEntity(CoordinatorEntity[InkbirdCoordinator], SelectEntity):
    def __init__(self, coordinator: InkbirdCoordinator, device: InkbirdIamT1Device):
        super().__init__(coordinator)
        self._attr_name = f"{device.model} Alarm Mode"
        self._attr_unique_id = f"{device.model}_{device.address}_alarm_mode"
        self._attr_options = [mode.name for mode in ALARM_MODE]
        self._attr_icon = "mdi:alarm"

    @property
    def current_option(self):
        """Return the current alarm mode."""
        mode = self.coordinator.data.alarm_mode
        return mode.name if mode else mode

    async def async_select_option(self, option: str):
        """Set the alarm mode."""
        await self.coordinator.update_alarm_mode(ALARM_MODE[option])
            
class InkbirdSamplingIntervalSelectEntity(CoordinatorEntity[InkbirdCoordinator], SelectEntity):
    def __init__(self, coordinator: InkbirdCoordinator, device: InkbirdIamT1Device):
        super().__init__(coordinator)
        self._attr_name = f"{device.model} Sampling Interval"
        self._attr_unique_id = f"{device.model}_{device.address}_sampling_inteval"
        self._attr_options = [interval.name for interval in SAMPLING_INTERVAL]
        self._attr_icon = "mdi:timer"

    @property
    def current_option(self):
        interval = self.coordinator.data.sampling_interval
        return interval.name if interval else interval

    async def async_select_option(self, option: str):
        await self.coordinator.update_sampling_interval(SAMPLING_INTERVAL[option])