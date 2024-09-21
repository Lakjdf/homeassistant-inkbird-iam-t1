"""Support for inkbird ble sensors."""

from .coordinator import InkbirdCoordinator

from .inkbird_ble_custom import InkbirdIamT1Device

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    CONCENTRATION_PARTS_PER_MILLION,
    UnitOfTemperature,
    UnitOfPressure
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import InkbirdConfigEntry

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key=f"{SensorDeviceClass.TEMPERATURE}_{UnitOfTemperature.CELSIUS}",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=f"{SensorDeviceClass.HUMIDITY}_{PERCENTAGE}",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=f"{SensorDeviceClass.CO2}_{CONCENTRATION_PARTS_PER_MILLION}",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=f"{SensorDeviceClass.ATMOSPHERIC_PRESSURE}_{UnitOfPressure.HPA}",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
    )
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: InkbirdConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the INKBIRD BLE sensors."""
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [InkbirdSensorEntity(coordinator, coordinator.data, desc) for desc in SENSOR_DESCRIPTIONS]
    async_add_entities(entities)


class InkbirdSensorEntity(CoordinatorEntity[InkbirdCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: InkbirdCoordinator,
        device: InkbirdIamT1Device,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Populate the entity with relevant data."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{device.model} {device.address}_{entity_description.key}"

        self._id = device.address
        self._attr_device_info = DeviceInfo(
            connections={
                (
                    CONNECTION_BLUETOOTH,
                    device.address,
                )
            },
            name=device.model,
            manufacturer=device.manufacturer,
            model=device.model,
            sw_version=device.sw_version,
        )

    @property
    def native_value(self) -> float:
        """Return the value reported by the sensor."""
        try:
            return self.coordinator.data.sensors[self.entity_description.device_class]
        except KeyError:
            return None
        