"""Support for RFM Gateway sensors."""
from __future__ import annotations

import logging

from homeassistant.components import mqtt
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricPotential,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import CONF_GATEWAYS, DOMAIN, NODE_TOPIC
from .data_parser import get_sensor_value
from .device import compose_gateway_device, compose_node_device

_LOGGER = logging.getLogger(__name__)


class NodeSensorEntityDescription(SensorEntityDescription):
    """A class that describes RFM Gateway sensor entities."""


class NodeSensor(SensorEntity):
    """Representation of a sensor connected to the RFM Gateway."""

    TYPE = DOMAIN
    entity_description: NodeSensorEntityDescription
    node_type = 0
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self: NodeSensor,
        node_type: int,
        unique_id: str,
        entity_description: NodeSensorEntityDescription,
        device_info: dr.DeviceInfo,
    ) -> None:
        """Init NodeSensor with required parameters."""
        device = device_info["name"]
        self._attr_name = f"{device} {entity_description.name}"
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info
        self.node_type = node_type
        self.entity_description: NodeSensorEntityDescription = entity_description

    def async_update_value(self, data: bytes):
        """Update the sensor value."""

        device_class = self.entity_description.device_class
        value = get_sensor_value(data, device_class)

        if not value:
            return

        self._attr_native_value = value
        self.async_write_ha_state()


NODE_SENSORS = {
    1: [SensorDeviceClass.SIGNAL_STRENGTH, SensorDeviceClass.VOLTAGE],
    2: [
        SensorDeviceClass.SIGNAL_STRENGTH,
        SensorDeviceClass.VOLTAGE,
        SensorDeviceClass.TEMPERATURE,
    ],
    3: [
        SensorDeviceClass.SIGNAL_STRENGTH,
        SensorDeviceClass.VOLTAGE,
        SensorDeviceClass.TEMPERATURE,
        SensorDeviceClass.HUMIDITY,
    ],
    4: [
        SensorDeviceClass.SIGNAL_STRENGTH,
        SensorDeviceClass.VOLTAGE,
        SensorDeviceClass.TEMPERATURE,
        SensorDeviceClass.HUMIDITY,
        SensorDeviceClass.PRESSURE,
    ],
    11: [
        SensorDeviceClass.SIGNAL_STRENGTH,
        SensorDeviceClass.VOLTAGE,
        SensorDeviceClass.GAS,
    ],
    12: [
        SensorDeviceClass.SIGNAL_STRENGTH,
        SensorDeviceClass.VOLTAGE,
        SensorDeviceClass.WATER,
    ],
}
SENSOR_DESCRIPTIONS = {
    SensorDeviceClass.SIGNAL_STRENGTH: NodeSensorEntityDescription(
        key="RSSI",
        name="RSSI",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        suggested_display_precision=0,
    ),
    SensorDeviceClass.VOLTAGE: NodeSensorEntityDescription(
        key="Vcc",
        name="Vcc",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=2,
    ),
    SensorDeviceClass.TEMPERATURE: NodeSensorEntityDescription(
        key="Temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorDeviceClass.HUMIDITY: NodeSensorEntityDescription(
        key="Humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    SensorDeviceClass.PRESSURE: NodeSensorEntityDescription(
        key="Presssure",
        name="Presssure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MMHG,
        suggested_display_precision=0,
    ),
    SensorDeviceClass.GAS: NodeSensorEntityDescription(
        key="Gas consumption",
        name="Gas consumption",
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=2,
    ),
    SensorDeviceClass.WATER: NodeSensorEntityDescription(
        key="Water consumption",
        name="Water consumption",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=2,
    ),
}

store: dict[str, NodeSensor] = {}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""

    gateways = {}
    for config in hass.data[DOMAIN][entry.entry_id][CONF_GATEWAYS]:
        gateways[config["mac"]] = compose_gateway_device(
            config["mac"].lower(), config["name"]
        )

    @callback
    def async_sensor_event_received(msg):
        gateway_id = msg.topic.split("/")[1].replace("_", ":").lower()
        gateway = gateways[gateway_id]
        data = bytes(msg.payload)

        if not gateway:
            _LOGGER.debug(
                "No gateway with MAC %(gateway_id)s",
                {"gateway_id": gateway_id},
            )
            return

        sensors = compose_node_entities(gateway_id, data)
        for sensor in sensors:
            unique_id = sensor.unique_id.replace(":", "_")
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

    node_id, node_type = int.from_bytes(data[:2], "little"), data[4]
    if node_type not in NODE_SENSORS:
        return []

    node = compose_node_device(gateway_id, node_id, node_type)
    return [
        compose_entity(gateway_id, node, node_id, node_type, device_class)
        for device_class in NODE_SENSORS[node_type]
    ]


def compose_entity(
    gateway_id: str,
    node: dr.DeviceInfo,
    node_id: int,
    node_type: int,
    device_class: SensorDeviceClass,
) -> NodeSensor:
    """Compose the node sensor."""

    entity_description = SENSOR_DESCRIPTIONS[device_class]
    name = entity_description.key.lower()

    sensor = NodeSensor(
        node_type=node_type,
        unique_id=f"{gateway_id}_{node_id}_{name}",
        entity_description=entity_description,
        device_info=node,
    )
    sensor.entity_id = f"sensor.rfm_node_{node_id}_{slugify(name)}"
    return sensor
