"""Support for colecting data from remote nodes through RFM Gateway."""
from __future__ import annotations

import logging

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ELECTRIC_POTENTIAL_VOLT,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    TEMP_CELSIUS,
    UnitOfPressure,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify

from .const import DOMAIN, MACUFACTURER, NODE_TOPIC, STORE

_LOGGER = logging.getLogger(__name__)

store = {}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]

    @callback
    def async_sensor_event_received(msg):
        gateway_id = msg.topic.split("/")[1].replace("_", ":")
        gateway = get_gateway_device(hass, gateway_id)
        data = bytes(msg.payload)

        if not gateway:
            return

        # store = config[STORE]
        sensors = compose_node_entities(gateway_id, data)
        for sensor in sensors:
            unique_id = sensor.unique_id.replace(':', '_')
            if unique_id not in store:
                sensor.hass = hass
                sensor.async_update_value(data)
                store[unique_id] = sensor
                _LOGGER.debug(
                    "Registering sensor %(name)s => %(unique_id)s",
                    {"name": sensor.name, "unique_id": sensor.unique_id},
                )
                async_add_entities((sensor,), True)
            else:
                _LOGGER.debug(
                    "Updating sensor %(name)s => %(unique_id)s",
                    {"name": sensor.name, "unique_id": sensor.unique_id},
                )
                store[unique_id].async_update_value(data)

    await mqtt.async_subscribe(
        hass, NODE_TOPIC, async_sensor_event_received, qos=0, encoding=None
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the RFM Gateway platform."""

    @callback
    def async_sensor_event_received(msg):
        gateway_id = msg.topic.split("/")[1]
        gateway = get_gateway_device(hass, gateway_id)
        data = bytes(msg.payload)

        if not gateway:
            return

        # if (store := hass.data.get(DOMAIN)) is None:
        #     hass.data.setdefault(DOMAIN, {})
        #     store = hass.data.get(DOMAIN)

        sensors = compose_node_entities(gateway, data)
        for sensor in sensors:
            unique_id = sensor.unique_id.replace(':', '_')
            if unique_id not in store:
                sensor.hass = hass
                sensor.async_update_value(data)
                store[unique_id] = sensor
                _LOGGER.debug(
                    "Registering sensor %(name)s => %(unique_id)s",
                    {"name": sensor.name, "unique_id": sensor.unique_id},
                )
                async_add_entities((sensor,), True)
            else:
                _LOGGER.debug(
                    "Updating sensor %(name)s => %(unique_id)s",
                    {"name": sensor.name, "unique_id": sensor.unique_id},
                )
                store[unique_id].async_update_value(data)

    await mqtt.async_subscribe(
        hass, NODE_TOPIC, async_sensor_event_received, qos=0, encoding=None
    )


def compose_node_entities(gateway_id: str, data: bytes) -> list[NodeSensor]:
    """Composes sensors based on payload."""

    node_id = int.from_bytes(data[:2], "little")
    node_type = data[4]
    node = compose_node_device(gateway_id, node_id, node_type)
    sensors = [
        compose_entity(
            gateway_id,
            node,
            node_id,
            node_type,
            SensorDeviceClass.SIGNAL_STRENGTH,
        ),
        compose_entity(
            gateway_id,
            node,
            node_id,
            node_type,
            SensorDeviceClass.VOLTAGE,
        ),
    ]

    if node_type in [2, 3, 4]:
        sensors.append(
            compose_entity(
                gateway_id,
                node,
                node_id,
                node_type,
                SensorDeviceClass.TEMPERATURE,
            ),
        )
    if node_type in [3, 4]:
        sensors.append(
            compose_entity(
                gateway_id,
                node,
                node_id,
                node_type,
                SensorDeviceClass.HUMIDITY,
            ),
        )
    if node_type in [4]:
        sensors.append(
            compose_entity(
                gateway_id,
                node,
                node_id,
                node_type,
                SensorDeviceClass.PRESSURE,
            ),
        )

    return sensors


class NodeSensor(SensorEntity):
    """Representation of a sensor connected to the RFM Gateway."""

    _attr_should_poll = False
    node_type = 0

    def __init__(
        self: NodeSensor,
        node_type: int,
        name: str,
        unique_id: str,
        device_class: str,
        units: str,
        device_info: DeviceInfo,
    ) -> None:
        """Init NodeSensor with required parameters."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = units
        self.node_type = node_type

    def async_update_value(self, data: bytes):
        """Update the sensors value."""

        # match self.device_class:
        if self.device_class == SensorDeviceClass.SIGNAL_STRENGTH:
            int_value = int.from_bytes(data[2:4], "little", signed=True)
            value = str(int_value)
        elif self.device_class == SensorDeviceClass.VOLTAGE:
            if self.node_type == 1:
                int_value = int.from_bytes(data[5:7], "little", signed=True)
            elif self.node_type == 2:
                int_value = int.from_bytes(data[7:9], "little", signed=True)
            elif self.node_type == 3:
                int_value = int.from_bytes(data[9:11], "little", signed=True)
            elif self.node_type == 4:
                int_value = int.from_bytes(data[11:13], "little", signed=True)

            float_value = int_value / 1000.0
            value = f"{float_value:.2f}"
        elif self.device_class == SensorDeviceClass.TEMPERATURE:
            float_value = int.from_bytes(data[5:7], "little", signed=True) / 100.0
            value = f"{float_value:.2f}"
        elif self.device_class == SensorDeviceClass.HUMIDITY:
            float_value = int.from_bytes(data[7:9], "little", signed=True) / 100.0
            value = f"{float_value:.0f}"
        elif self.device_class == SensorDeviceClass.PRESSURE:
            int_value = int.from_bytes(data[9:11], "little", signed=True)
            value = str(int_value)

        if not value:
            return

        self._attr_native_value = value
        self.async_write_ha_state()


def compose_entity(
    gateway_id: str,
    node: DeviceInfo,
    node_id: int,
    node_type: int,
    device_class: str,
):
    """Compose the node sensor."""

    if device_class == SensorDeviceClass.SIGNAL_STRENGTH:
        name = "RSSI"
        units = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    elif device_class == SensorDeviceClass.VOLTAGE:
        name = "Vcc"
        units = ELECTRIC_POTENTIAL_VOLT
    elif device_class == SensorDeviceClass.TEMPERATURE:
        name = "Temperature"
        units = TEMP_CELSIUS
    elif device_class == SensorDeviceClass.HUMIDITY:
        name = "Humidity"
        units = PERCENTAGE
    elif device_class == SensorDeviceClass.PRESSURE:
        name = "Presssure"
        units = UnitOfPressure.MMHG

    sensor = NodeSensor(
        node_type=node_type,
        name=name,
        unique_id=f"{gateway_id}_{node_id}_{name.lower()}",
        device_class=device_class,
        units=units,
        device_info=node,
    )
    sensor.entity_id = f"sensor.rfm_node_{node_id}_{slugify(name)}"
    return sensor


def compose_node_device(gateway_id: str, node_id: int, node_type: int) -> DeviceInfo:
    """Compose device for the node."""

    device = DeviceInfo()
    device["name"] = get_node_name(node_type, node_id)
    device["manufacturer"] = MACUFACTURER
    device["identifiers"] = {(DOMAIN, f"{gateway_id}_{node_id}")}
    device["via_device"] = (DOMAIN, gateway_id)

    return device


def get_gateway_device(hass: HomeAssistant, gateway_id: str) -> DeviceEntry | None:
    """Create or get gateway device."""

    device_registry = dr.async_get(hass)
    return device_registry.async_get_device({(DOMAIN, gateway_id)})


def get_node_name(node_type: int, node_id: int) -> str:
    """Return node name basend on its type."""

    name: str = "Generic Node"
    if node_type in [2, 3, 4]:
        name = "Weather Node"

    return f"{name} #{node_id}"
