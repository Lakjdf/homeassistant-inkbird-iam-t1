# Device config and sensor data are notified to this characteristic.
CHAR_NOTIFY_UUID    = "0000ffe4-0000-1000-8000-00805f9b34fb"
# Characteristic used to write configurations to. Also used to inform about connection.
CHAR_WRITE_UUID     = "0000ffe9-0000-1000-8000-00805f9b34fb"
# Signal to device to enter the "connected" state.
CONNECT_WRITE_DATA  = b"\x55\xaa\x09\x06\x01\x0f"
