"""The RFM Gateway component."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_GATEWAYS, DOMAIN, MACUFACTURER

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    device_registry = dr.async_get(hass)
    for gateway in entry.data[CONF_GATEWAYS]:
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, gateway["mac"])},
            identifiers={(DOMAIN, gateway["mac"])},
            manufacturer=MACUFACTURER,
            suggested_area="Kitchen",
            name=gateway["name"],
        )

    # Forward the setup to the sensor platform.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


# async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
#     """Set up the custom component from yaml configuration."""
#     hass.data.setdefault(DOMAIN, {})
#     return True
