"""Tuya ↔ Sonoff Climate Bridge integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .controller import ClimateBridgeController


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a climate bridge config entry."""
    hass.data.setdefault(DOMAIN, {})

    controller = ClimateBridgeController(hass, entry)
    await controller.async_start()
    hass.data[DOMAIN][entry.entry_id] = controller

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a climate bridge config entry."""
    controller = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if controller is not None:
        await controller.async_stop()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)
