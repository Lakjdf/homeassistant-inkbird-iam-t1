from __future__ import annotations

from logging import Logger
import logging
import struct

from bluetooth_data_tools import human_readable_name

import dataclasses
from typing import Any, Type

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice

from enum import Enum

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import CHAR_WRITE_UUID

_LOGGER = logging.getLogger("inkbird")

class ALARM_MODE(Enum):
    OFF         = 1
    ONCE        = 2
    EVERY_TIME  = 3

class SAMPLING_INTERVAL(Enum):
    ONE     = 1
    TWO     = 2
    FIVE    = 5
    TEN     = 10

class TEMPERATURE_UNIT(Enum):
    CELSIUS     = 1
    FAHRENHEIT  = 2

"""Parse constant predefined notifications."""
class InkbirdNotification:
    _mapping = {
        "55aa0409000000000c": ALARM_MODE.OFF,
        "55aa0409010000000d": ALARM_MODE.ONCE,
        "55aa0409010100000e": ALARM_MODE.EVERY_TIME,

        "55aa020b0000000001a4b1": SAMPLING_INTERVAL.ONE,
        "55aa020b0100000001a4b2": SAMPLING_INTERVAL.TWO,
        "55aa020b0200000001a4b3": SAMPLING_INTERVAL.FIVE,
        "55aa020b0400000001a4b5": SAMPLING_INTERVAL.TEN,

        "55aa050c0000000000000010": TEMPERATURE_UNIT.CELSIUS,
        "55aa050c0000000000000111": TEMPERATURE_UNIT.FAHRENHEIT,
    }
    _value2notification = {v: k for k,v in _mapping.items()}

    def parse(cls: Type, notification: bytes) -> ALARM_MODE | SAMPLING_INTERVAL | TEMPERATURE_UNIT | None:
        value = InkbirdNotification._mapping.get(notification.hex())
        return value if isinstance(value, cls) else None

    def create_response(value: Any) -> bytes:
        return bytes.fromhex(InkbirdNotification._value2notification[value])


@dataclasses.dataclass
class InkbirdIamT1Device:
    manufacturer: str = ""
    sw_version: str = ""
    model: str = ""
    address: str = ""

    alarm_mode: ALARM_MODE | None = None
    sampling_interval: SAMPLING_INTERVAL | None = None
    temperature_unit: TEMPERATURE_UNIT | None = None

    sensors: dict[SensorDeviceClass, Any] = dataclasses.field(default_factory=lambda: {})

    def from_dict(data: dict) -> InkbirdIamT1Device:
        device = InkbirdIamT1Device(**data)
        device.alarm_mode = ALARM_MODE(device.alarm_mode) if device.alarm_mode else None
        device.sampling_interval = SAMPLING_INTERVAL(device.sampling_interval) if device.sampling_interval else None
        device.temperature_unit = TEMPERATURE_UNIT(device.temperature_unit) if device.temperature_unit else None
        return device

    def name(self) -> str:
        return human_readable_name(None, self.model, self.address)
    
    async def write_alarm_mode(self, client: BleakClient, mode: ALARM_MODE):
        data = InkbirdNotification.create_response(mode)
        await client.write_gatt_char(CHAR_WRITE_UUID, data)

    async def write_sampling_interval(self, client: BleakClient, interval: SAMPLING_INTERVAL):
        data = InkbirdNotification.create_response(interval)
        await client.write_gatt_char(CHAR_WRITE_UUID, data)

    def update(self, notification: bytearray):
        def parse_temperature() -> float | None:
            sign_byte, high_byte, low_byte = struct.unpack_from('BBB', notification, offset=4)
            temperature_raw = (high_byte << 8) | low_byte
            if sign_byte == 1:
                temperature_raw = -temperature_raw
            temperature = temperature_raw / 10
            if self.temperature_unit == TEMPERATURE_UNIT.FAHRENHEIT:
                temperature = TemperatureConverter().convert(temperature, UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.CELSIUS)
            elif not self.temperature_unit:
                temperature = None
            return round(temperature, 1) if temperature else None
        
        def parse_humidity() -> float:
            return struct.unpack_from('>H', notification, offset=7)[0] / 10

        def parse_co2() -> float:
            return struct.unpack_from('>H', notification, offset=9)[0]

        def parse_pressure() -> float:
            return struct.unpack_from('>H', notification, offset=11)[0]
        
        if not notification.startswith(b"\x55\xaa"):
            _LOGGER.info("Unknown notification: %s", notification)
            return
        
        match notification[2]:
            case 0x01:
                # sensor data
                self.sensors.update({
                    SensorDeviceClass.TEMPERATURE:          parse_temperature(),
                    SensorDeviceClass.HUMIDITY:             parse_humidity(),
                    SensorDeviceClass.CO2:                  parse_co2(),
                    SensorDeviceClass.ATMOSPHERIC_PRESSURE: parse_pressure()
                })
                _LOGGER.debug("Received sensor update: %s", self.sensors)
            case 0x02:
                # sampling interval
                self.sampling_interval = InkbirdNotification.parse(SAMPLING_INTERVAL, notification)
                _LOGGER.debug("Received interval     : %s", self.sampling_interval)
            case 0x03:
                # co2 limits
                return
            case 0x04:
                # alarm mode
                self.alarm_mode = InkbirdNotification.parse(ALARM_MODE, notification)
                _LOGGER.debug("Received alarm mode   : %s", self.alarm_mode)
            case 0x05:
                # Celsius / Fahrenheit
                self.temperature_unit = InkbirdNotification.parse(TEMPERATURE_UNIT, notification)
                _LOGGER.debug("Received temp unit    : %s", self.temperature_unit)
            case _:
                _LOGGER.debug("Unknown notification  : %s", notification)

class DeviceInfoChars(Enum):
    FirmwareRevision    = "00002a26-0000-1000-8000-00805f9b34fb" # YBWY02-V1.0
    Model               = "0000ff91-0000-1000-8000-00805f9b34fb" # Ink@IAM-T1

class InkbirdIamT1DeviceData:
    def __init__(self, logger: Logger):
        self.logger = logger

    async def _get_char_value(self, client: BleakClient, uuid: str) -> str:
        try:
            data = await client.read_gatt_char(uuid)
        except BleakError as err:
            self.logger.debug("Failed to read 'characterstic' %s", uuid, exc_info=err)
        return data or ""

    async def _get_device_characteristics(
        self, client: BleakClient, device: InkbirdIamT1Device
    ) -> InkbirdIamT1Device:
        """Get the general properties of the device (not the sensor values)."""
        device.address = client.address
        device.manufacturer = "INKBIRD"

        device.sw_version   = self._get_char_value(client, DeviceInfoChars.FirmwareRevision.value)
        device.model        = self._get_char_value(client, DeviceInfoChars.Model.value)
        return device

    async def update_device_only(self, ble_device: BLEDevice) -> InkbirdIamT1Device:
        """Connect to the device through BLE and retrieve relevant data."""
        device = InkbirdIamT1Device()
        client = BleakClient(ble_device)
        await client.connect()
        try:
            device = await self._get_device_characteristics(client, device)
        finally:
            await client.disconnect()

        self.logger.debug("Retrieved device info %s", device)
        return device
