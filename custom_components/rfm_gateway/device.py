"""Compose gateways, devices."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN, MACUFACTURER


def compose_node_device(gateway_id: str, node_id: int, node_type: int) -> dr.DeviceInfo:
    """Compose device for the node."""

    device = dr.DeviceInfo()
    device["name"] = get_node_name(node_type, node_id)
    device["manufacturer"] = MACUFACTURER
    device["identifiers"] = {(DOMAIN, f"{gateway_id}_{node_id}")}
    device["via_device"] = (DOMAIN, gateway_id)

    return device


def compose_gateway_device(gateway_id: str, name: str) -> dr.DeviceInfo:
    """Compose gateway device to be set as via_device form the nodes."""

    device = dr.DeviceInfo()
    device["name"] = name
    device["manufacturer"] = MACUFACTURER
    device["identifiers"] = {(DOMAIN, gateway_id)}

    return device


def get_node_name(node_type: int, node_id: int) -> str:
    """Return node name basend on its type."""

    name: str = "Generic Node"
    if node_type in [2, 3, 4]:
        name = "Weather Node"

    return f"{name} #{node_id}"


def get_gateway_device(hass: HomeAssistant, gateway_id: str) -> DeviceEntry | None:
    """Create or get gateway device."""

    device_registry = dr.async_get(hass)
    return device_registry.async_get_device(identifiers={(DOMAIN, gateway_id.lower())})
