"""Config flow for Tuya ↔ Sonoff Climate Bridge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_FROST_TEMP,
    CONF_MIRROR_FROST_TO_MOES,
    CONF_THERMOSTAT,
    CONF_VALVES,
    CONF_ZONE_NAME,
    DEFAULT_FROST_TEMP,
    DEFAULT_MIRROR_FROST_TO_MOES,
    DOMAIN,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}

    thermostat_key = (
        vol.Required(CONF_THERMOSTAT, default=defaults[CONF_THERMOSTAT])
        if defaults.get(CONF_THERMOSTAT)
        else vol.Required(CONF_THERMOSTAT)
    )
    valves_key = (
        vol.Required(CONF_VALVES, default=defaults[CONF_VALVES])
        if defaults.get(CONF_VALVES)
        else vol.Required(CONF_VALVES)
    )

    return vol.Schema(
        {
            vol.Required(
                CONF_ZONE_NAME,
                default=defaults.get(CONF_ZONE_NAME, "Dormitor"),
            ): selector.TextSelector(),
            thermostat_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate", multiple=False)
            ),
            valves_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate", multiple=True)
            ),
            vol.Optional(
                CONF_MIRROR_FROST_TO_MOES,
                default=defaults.get(
                    CONF_MIRROR_FROST_TO_MOES,
                    DEFAULT_MIRROR_FROST_TO_MOES,
                ),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_FROST_TEMP,
                default=defaults.get(CONF_FROST_TEMP, DEFAULT_FROST_TEMP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=4.0,
                    max=15.0,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
        }
    )


class ClimateBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Create one zone association."""
        errors: dict[str, str] = {}

        if user_input is not None:
            thermostat = user_input[CONF_THERMOSTAT]
            valves = list(user_input[CONF_VALVES])

            if thermostat in valves:
                errors["base"] = "same_entity"
            elif not valves:
                errors["base"] = "no_valves"
            else:
                await self.async_set_unique_id(thermostat)
                self._abort_if_unique_id_configured()

                title = user_input[CONF_ZONE_NAME].strip() or thermostat
                data = dict(user_input)
                data[CONF_VALVES] = valves
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return options flow."""
        return ClimateBridgeOptionsFlow(config_entry)


class ClimateBridgeOptionsFlow(config_entries.OptionsFlow):
    """Edit an existing zone association."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Edit zone options."""
        current = {**self._config_entry.data, **self._config_entry.options}
        errors: dict[str, str] = {}

        if user_input is not None:
            thermostat = user_input[CONF_THERMOSTAT]
            valves = list(user_input[CONF_VALVES])
            if thermostat in valves:
                errors["base"] = "same_entity"
            elif not valves:
                errors["base"] = "no_valves"
            else:
                data = dict(user_input)
                data[CONF_VALVES] = valves
                return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current),
            errors=errors,
        )
