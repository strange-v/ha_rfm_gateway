"""Parse data and retrieve sensors values."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass


def get_value(data: bytes, divisor: float = 0, num_digits: int = 0) -> str:
    """Retrieve value and format it."""

    value = int.from_bytes(data, "little", signed=True)
    if divisor > 0:
        float_value = value / divisor
        return f"{float_value:.{num_digits}f}"

    return str(value)


def get_voltage(data: bytes) -> str:
    """Retrieve voltage."""

    return get_value(data, 1000.0, 2)


def get_temperature(data: bytes) -> str:
    """Retrieve temperature."""

    return get_value(data, 100.0, 2)


SENSOR_PARSERS = {
    SensorDeviceClass.SIGNAL_STRENGTH: {
        1: lambda data: get_value(data[2:4]),
        2: lambda data: get_value(data[2:4]),
        3: lambda data: get_value(data[2::4]),
        4: lambda data: get_value(data[2:4]),
        11: lambda data: get_value(data[2:4]),
        12: lambda data: get_value(data[2:4]),
        21: lambda data: get_value(data[2:4]),
    },
    SensorDeviceClass.VOLTAGE: {
        1: lambda data: get_voltage(data[5:7]),
        2: lambda data: get_voltage(data[7:9]),
        3: lambda data: get_voltage(data[9:11]),
        4: lambda data: get_voltage(data[11:13]),
        11: lambda data: get_voltage(data[9:11]),
        12: lambda data: get_voltage(data[9:11]),
        21: lambda data: get_voltage(data[6:8]),
    },
    SensorDeviceClass.TEMPERATURE: {
        2: lambda data: get_temperature(data[5:7]),
        3: lambda data: get_temperature(data[5:7]),
        4: lambda data: get_temperature(data[5:7]),
    },
    SensorDeviceClass.HUMIDITY: {
        3: lambda data: get_value(data[7:9], 100, 0),
        4: lambda data: get_value(data[7:9], 100, 0),
    },
    SensorDeviceClass.PRESSURE: {
        4: lambda data: get_value(data[9:11]),
    },
    SensorDeviceClass.GAS: {
        11: lambda data: get_value(data[5:9], 100, 2),
    },
    SensorDeviceClass.WATER: {
        12: lambda data: get_value(data[5:9], 100, 2),
    },
}

BINARY_SENSOR_PARSERS = {
    BinarySensorDeviceClass.DOOR: {
        21: lambda data: bool(data[5]),
    },
}


def get_sensor_value(data: bytes, device_class: SensorDeviceClass | None) -> str | None:
    """Retrieve sensor value based on device_class and node type."""

    node_type = data[4]

    if not device_class or node_type not in SENSOR_PARSERS[device_class]:
        return None

    return SENSOR_PARSERS[device_class][node_type](data)


def get_binary_sensor_value(
    data: bytes, device_class: BinarySensorDeviceClass | None
) -> bool | None:
    """Retrieve binary sensor value based on device_class and node type."""

    node_type = data[4]

    if not device_class or node_type not in BINARY_SENSOR_PARSERS[device_class]:
        return None

    return BINARY_SENSOR_PARSERS[device_class][node_type](data)
