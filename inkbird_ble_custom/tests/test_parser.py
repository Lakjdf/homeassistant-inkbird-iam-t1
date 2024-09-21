from parser import InkbirdIamT1Device, ALARM_MODE, SAMPLING_INTERVAL, TEMPERATURE_UNIT
from homeassistant.components.sensor import SensorDeviceClass
import pytest

def test_notification_sensor():
    device = InkbirdIamT1Device(temperature_unit=TEMPERATURE_UNIT.CELSIUS)
    notification = "55aa011000010301fe028003eb010185"

    device.update(bytes.fromhex(notification))

    assert device.sensors[SensorDeviceClass.TEMPERATURE] == 25.9
    assert device.sensors[SensorDeviceClass.HUMIDITY] == 51
    assert device.sensors[SensorDeviceClass.CO2] == 640
    assert device.sensors[SensorDeviceClass.ATMOSPHERIC_PRESSURE] == 1003

def test_notification_sensor_fahrenheit():
    device = InkbirdIamT1Device(temperature_unit=TEMPERATURE_UNIT.FAHRENHEIT)
    notification = "55aa011010031e027605ea03f101008d"

    device.update(bytes.fromhex(notification))

    assert device.sensors[SensorDeviceClass.TEMPERATURE] == 26.6
    assert device.sensors[SensorDeviceClass.HUMIDITY] == 63
    assert device.sensors[SensorDeviceClass.CO2] == 1514
    assert device.sensors[SensorDeviceClass.ATMOSPHERIC_PRESSURE] == 1009

@pytest.mark.parametrize("notification, expected", [
    ("55aa0409000000000c", ALARM_MODE.OFF),
    ("55aa0409010000000d", ALARM_MODE.ONCE),
    ("55aa0409010100000e", ALARM_MODE.EVERY_TIME),
    ("55aa04090000000000", None),
])
def test_notification_alarm_mode(notification, expected):
    device = InkbirdIamT1Device()

    device.update(bytes.fromhex(notification))

    assert device.alarm_mode == expected

@pytest.mark.parametrize("notification, expected", [
    ("55aa020b0000000001a4b1", SAMPLING_INTERVAL.ONE),
    ("55aa020b0100000001a4b2", SAMPLING_INTERVAL.TWO),
    ("55aa020b0200000001a4b3", SAMPLING_INTERVAL.FIVE),
    ("55aa020b0400000001a4b5", SAMPLING_INTERVAL.TEN),
    ("55aa020b00000000000000", None)
])
def test_notification_sampling_interval(notification, expected):
    device = InkbirdIamT1Device()

    device.update(bytes.fromhex(notification))

    assert device.sampling_interval == expected

@pytest.mark.parametrize("notification, expected", [
    ("55aa050c0000000000000010", TEMPERATURE_UNIT.CELSIUS),
    ("55aa050c0000000000000111", TEMPERATURE_UNIT.FAHRENHEIT),
    ("55aa050c0000000000000000", None)
])
def test_notification_temperature_unit(notification, expected):
    device = InkbirdIamT1Device()

    device.update(bytes.fromhex(notification))

    assert device.temperature_unit == expected