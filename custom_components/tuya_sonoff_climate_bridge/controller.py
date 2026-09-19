"""Bidirectional state machine for Tuya/Moes ↔ Sonoff TRVZB."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import (
    ATTR_TEMPERATURE,
    CONF_FROST_TEMP,
    CONF_THERMOSTAT,
    CONF_VALVES,
    CONF_ZONE_NAME,
    DEFAULT_FROST_TEMP,
    DOMAIN,
    EXPECTED_TIMEOUT,
    MODE_HEAT,
    MODE_OFF,
    SONOFF_HEAT_CONFIRM_TIMEOUT,
    SONOFF_RESTORE_WAIT_TIMEOUT,
    TARGET_TOLERANCE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class _ExpectedValue:
    value: Any
    expires: float


class ClimateBridgeController:
    """Synchronize one Moes/Tuya thermostat with one or more Sonoff TRVZB valves."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        cfg = {**entry.data, **entry.options}

        self.zone_name: str = cfg.get(CONF_ZONE_NAME, entry.title)
        self.thermostat: str = cfg[CONF_THERMOSTAT]
        self.valves: list[str] = list(cfg[CONF_VALVES])
        self.frost_temp: float = float(cfg.get(CONF_FROST_TEMP, DEFAULT_FROST_TEMP))

        self._working_target: float | None = None
        self._desired_mode: str | None = None

        self._expected_mode: dict[str, _ExpectedValue] = {}
        self._expected_target: dict[str, _ExpectedValue] = {}
        self._bridge_starting: dict[str, int] = {}
        self._start_generation: dict[str, int] = {entity_id: 0 for entity_id in self.valves}
        self._manual_start_tasks: dict[str, asyncio.Task] = {}
        self._start_tasks: dict[str, asyncio.Task] = {}
        self._unsub = None

        self._store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.{entry.entry_id}"
        )

    async def async_start(self) -> None:
        """Start listeners and restore bridge memory."""
        stored = await self._store.async_load() or {}
        stored_target = stored.get("working_target")
        if isinstance(stored_target, (int, float)):
            self._working_target = float(stored_target)

        moes = self.hass.states.get(self.thermostat)
        if moes is not None:
            target = self._target(moes)
            if target is not None:
                # Moes target remains a valid working target even while OFF.
                self._working_target = target
            if moes.state in (MODE_OFF, MODE_HEAT):
                self._desired_mode = moes.state

        entities = [self.thermostat, *self.valves]
        self._unsub = async_track_state_change_event(
            self.hass, entities, self._state_changed
        )

        await self._save_state()
        _LOGGER.warning(
            "[%s] Bridge started: thermostat=%s valves=%s working_target=%s. "
            "No startup command is sent; synchronization begins with the next real change.",
            self.zone_name,
            self.thermostat,
            self.valves,
            self._working_target,
        )

    async def async_stop(self) -> None:
        """Stop listeners and background tasks."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

        for task in [*self._manual_start_tasks.values(), *self._start_tasks.values()]:
            task.cancel()
        self._manual_start_tasks.clear()
        self._start_tasks.clear()
        self._bridge_starting.clear()

    @callback
    def _state_changed(self, event: Event) -> None:
        """Route a state change without blocking Home Assistant's event loop."""
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")
        if new_state is None:
            return

        if new_state.entity_id == self.thermostat:
            self.hass.async_create_task(self._handle_moes(old_state, new_state))
        elif new_state.entity_id in self.valves:
            self.hass.async_create_task(self._handle_sonoff(old_state, new_state))

    async def _handle_moes(self, old: State | None, new: State) -> None:
        """Handle a Moes/Tuya change."""
        old_mode = old.state if old is not None else None
        new_mode = new.state
        old_target = self._target(old)
        new_target = self._target(new)

        mode_changed = old_mode != new_mode
        target_changed = self._different(old_target, new_target)

        internal_mode = False
        internal_target = False
        if mode_changed:
            internal_mode = self._consume_expected(self._expected_mode, new.entity_id, new_mode)
        if target_changed and new_target is not None:
            internal_target = self._consume_expected(
                self._expected_target, new.entity_id, new_target, numeric=True
            )

        # Moes target is always a valid working target, including while OFF.
        if target_changed and new_target is not None:
            self._working_target = new_target
            await self._save_state()

        manual_mode = mode_changed and not internal_mode
        manual_target = target_changed and not internal_target
        if not manual_mode and not manual_target:
            return

        _LOGGER.warning(
            "[%s] Moes change: %s/%s -> %s/%s (manual_mode=%s manual_target=%s)",
            self.zone_name,
            old_mode,
            old_target,
            new_mode,
            new_target,
            manual_mode,
            manual_target,
        )

        if new_mode == MODE_OFF:
            self._desired_mode = MODE_OFF
            await self._save_state()
            # A temperature change while Moes is OFF only updates working_target.
            # All Sonoff valves stay / become OFF. Never send set_temperature in OFF.
            await self._set_all_sonoff_off()
            return

        if new_mode == MODE_HEAT:
            self._desired_mode = MODE_HEAT
            target = new_target if new_target is not None else self._working_target
            if target is None:
                _LOGGER.error("[%s] Moes HEAT has no usable target", self.zone_name)
                return
            self._working_target = target
            await self._save_state()
            await self._set_all_sonoff_heat(target)
            return

        _LOGGER.warning(
            "[%s] Moes mode %s is not handled in test v0.1.0 (only off/heat)",
            self.zone_name,
            new_mode,
        )

    async def _handle_sonoff(self, old: State | None, new: State) -> None:
        """Handle a Sonoff TRVZB change."""
        entity_id = new.entity_id
        old_mode = old.state if old is not None else None
        new_mode = new.state
        old_target = self._target(old)
        new_target = self._target(new)

        mode_changed = old_mode != new_mode
        target_changed = self._different(old_target, new_target)

        internal_mode = False
        internal_target = False
        if mode_changed:
            internal_mode = self._consume_expected(self._expected_mode, entity_id, new_mode)
        if target_changed and new_target is not None:
            internal_target = self._consume_expected(
                self._expected_target, entity_id, new_target, numeric=True
            )

        # During bridge-controlled OFF->HEAT we deliberately ignore the TRV's
        # restored old target (including transient HEAT/7). The bridge will write
        # its own working_target only after HEAT is confirmed.
        if entity_id in self._bridge_starting:
            if new_mode == MODE_OFF and mode_changed and not internal_mode:
                # A real user OFF can still cancel the bridge start.
                self._cancel_bridge_start(entity_id)
            else:
                return

        manual_mode = mode_changed and not internal_mode
        manual_target = target_changed and not internal_target
        if not manual_mode and not manual_target:
            return

        _LOGGER.warning(
            "[%s] Sonoff %s change: %s/%s -> %s/%s (manual_mode=%s manual_target=%s)",
            self.zone_name,
            entity_id,
            old_mode,
            old_target,
            new_mode,
            new_target,
            manual_mode,
            manual_target,
        )

        # OFF is authoritative immediately. Preserve the last valid target but
        # never accept the later OFF/7 frost value as working_target.
        if new_mode == MODE_OFF and manual_mode:
            if self._valid_sonoff_working_target(old_target):
                self._working_target = old_target
            self._desired_mode = MODE_OFF
            await self._save_state()
            await self._set_moes_off()
            await self._set_peer_sonoff_off(entity_id)
            return

        if new_mode != MODE_HEAT:
            return

        # A manual OFF->HEAT can briefly report HEAT/7 for several seconds.
        # Wait for the real restored/new working target before propagating.
        if manual_mode and not self._valid_sonoff_working_target(new_target):
            self._schedule_manual_sonoff_start(entity_id)
            return

        if (manual_mode or manual_target) and self._valid_sonoff_working_target(new_target):
            self._cancel_manual_start(entity_id)
            await self._propagate_sonoff_heat(entity_id, float(new_target))

    async def _propagate_sonoff_heat(self, source: str, target: float) -> None:
        """Make a real Sonoff HEAT/target change authoritative for the zone."""
        self._working_target = target
        self._desired_mode = MODE_HEAT
        await self._save_state()

        # Moes is safe to receive target while OFF, so set target first and then HEAT.
        await self._set_moes_target(target)
        await self._set_moes_mode(MODE_HEAT)

        for valve in self.valves:
            if valve != source:
                await self._ensure_sonoff_heat_target(valve, target)

    def _schedule_manual_sonoff_start(self, entity_id: str) -> None:
        """Wait for a manual Sonoff start to expose a non-frost target."""
        self._cancel_manual_start(entity_id)
        self._manual_start_tasks[entity_id] = self.hass.async_create_task(
            self._wait_manual_sonoff_target(entity_id)
        )

    async def _wait_manual_sonoff_target(self, entity_id: str) -> None:
        """Wait for the real target after manual OFF->HEAT."""
        try:
            deadline = monotonic() + SONOFF_RESTORE_WAIT_TIMEOUT
            while monotonic() < deadline:
                state = self.hass.states.get(entity_id)
                if state is None or state.state != MODE_HEAT:
                    return
                target = self._target(state)
                if self._valid_sonoff_working_target(target):
                    await self._propagate_sonoff_heat(entity_id, float(target))
                    return
                await asyncio.sleep(0.15)

            _LOGGER.warning(
                "[%s] Sonoff %s entered HEAT but no valid target appeared within %.1fs; "
                "nothing was propagated to Moes.",
                self.zone_name,
                entity_id,
                SONOFF_RESTORE_WAIT_TIMEOUT,
            )
        finally:
            self._manual_start_tasks.pop(entity_id, None)

    async def _set_all_sonoff_off(self) -> None:
        for valve in self.valves:
            await self._ensure_sonoff_off(valve)

    async def _set_peer_sonoff_off(self, source: str) -> None:
        for valve in self.valves:
            if valve != source:
                await self._ensure_sonoff_off(valve)

    async def _set_all_sonoff_heat(self, target: float) -> None:
        for valve in self.valves:
            await self._ensure_sonoff_heat_target(valve, target)

    async def _ensure_sonoff_off(self, entity_id: str) -> None:
        """Turn Sonoff OFF. Never send a temperature with this operation."""
        self._cancel_bridge_start(entity_id)
        state = self.hass.states.get(entity_id)
        if state is None or state.state == MODE_OFF:
            return

        self._expect(self._expected_mode, entity_id, MODE_OFF)
        await self._call_climate(
            "set_hvac_mode", entity_id, {"hvac_mode": MODE_OFF}
        )

    async def _ensure_sonoff_heat_target(self, entity_id: str, target: float) -> None:
        """Safely make a Sonoff HEAT and then set its working target."""
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.error("[%s] Sonoff entity missing: %s", self.zone_name, entity_id)
            return

        if state.state == MODE_HEAT:
            await self._set_sonoff_target_if_heat(entity_id, target)
            return

        if state.state != MODE_OFF:
            _LOGGER.warning(
                "[%s] Sonoff %s mode %s not handled in test v0.1.0",
                self.zone_name,
                entity_id,
                state.state,
            )
            return

        # Critical safety rule: OFF -> set_hvac_mode(heat) -> confirmed HEAT -> target.
        self._start_generation[entity_id] += 1
        generation = self._start_generation[entity_id]
        self._bridge_starting[entity_id] = generation

        old_task = self._start_tasks.pop(entity_id, None)
        if old_task is not None:
            old_task.cancel()

        self._expect(self._expected_mode, entity_id, MODE_HEAT)
        await self._call_climate(
            "set_hvac_mode", entity_id, {"hvac_mode": MODE_HEAT}
        )

        self._start_tasks[entity_id] = self.hass.async_create_task(
            self._finish_bridge_sonoff_start(entity_id, target, generation)
        )

    async def _finish_bridge_sonoff_start(
        self, entity_id: str, target: float, generation: int
    ) -> None:
        """Wait for HEAT confirmation and target restoration, then write desired target."""
        try:
            deadline = monotonic() + SONOFF_HEAT_CONFIRM_TIMEOUT
            while monotonic() < deadline:
                if self._start_generation.get(entity_id) != generation:
                    return
                state = self.hass.states.get(entity_id)
                if state is not None and state.state == MODE_HEAT:
                    break
                await asyncio.sleep(0.10)
            else:
                _LOGGER.error(
                    "[%s] Sonoff %s did not confirm HEAT within %.1fs",
                    self.zone_name,
                    entity_id,
                    SONOFF_HEAT_CONFIRM_TIMEOUT,
                )
                return

            # We have confirmed HEAT, so set_temperature is now safe. Wait briefly
            # for the TRV's own remembered target to reappear so it cannot overwrite
            # our desired target a few seconds later.
            restore_deadline = monotonic() + SONOFF_RESTORE_WAIT_TIMEOUT
            while monotonic() < restore_deadline:
                if self._start_generation.get(entity_id) != generation:
                    return
                state = self.hass.states.get(entity_id)
                if state is None or state.state != MODE_HEAT:
                    return
                if self._valid_sonoff_working_target(self._target(state)):
                    break
                await asyncio.sleep(0.15)

            if self._start_generation.get(entity_id) != generation:
                return
            if self._desired_mode != MODE_HEAT:
                return

            state = self.hass.states.get(entity_id)
            if state is None or state.state != MODE_HEAT:
                return

            await self._set_sonoff_target_if_heat(entity_id, target)
        finally:
            if self._bridge_starting.get(entity_id) == generation:
                self._bridge_starting.pop(entity_id, None)
            self._start_tasks.pop(entity_id, None)

    async def _set_sonoff_target_if_heat(self, entity_id: str, target: float) -> None:
        """Set Sonoff target only if its current mode is confirmed HEAT."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state != MODE_HEAT:
            _LOGGER.warning(
                "[%s] SAFETY: blocked set_temperature(%s) to %s because state=%s",
                self.zone_name,
                target,
                entity_id,
                None if state is None else state.state,
            )
            return

        current_target = self._target(state)
        if not self._different(current_target, target):
            return

        self._expect(self._expected_target, entity_id, target)
        await self._call_climate(
            "set_temperature", entity_id, {"temperature": target}
        )

    async def _set_moes_off(self) -> None:
        await self._set_moes_mode(MODE_OFF)

    async def _set_moes_mode(self, mode: str) -> None:
        state = self.hass.states.get(self.thermostat)
        if state is None or state.state == mode:
            return
        self._expect(self._expected_mode, self.thermostat, mode)
        await self._call_climate(
            "set_hvac_mode", self.thermostat, {"hvac_mode": mode}
        )

    async def _set_moes_target(self, target: float) -> None:
        state = self.hass.states.get(self.thermostat)
        if state is None:
            return
        current = self._target(state)
        if not self._different(current, target):
            return
        self._expect(self._expected_target, self.thermostat, target)
        await self._call_climate(
            "set_temperature", self.thermostat, {"temperature": target}
        )

    async def _call_climate(
        self, service: str, entity_id: str, extra: dict[str, Any]
    ) -> None:
        data = {"entity_id": entity_id, **extra}
        _LOGGER.warning(
            "[%s] climate.%s -> %s data=%s",
            self.zone_name,
            service,
            entity_id,
            extra,
        )
        try:
            await self.hass.services.async_call(
                "climate", service, data, blocking=True
            )
        except Exception:
            _LOGGER.exception(
                "[%s] climate.%s failed for %s",
                self.zone_name,
                service,
                entity_id,
            )

    def _cancel_bridge_start(self, entity_id: str) -> None:
        self._start_generation[entity_id] = self._start_generation.get(entity_id, 0) + 1
        self._bridge_starting.pop(entity_id, None)
        task = self._start_tasks.pop(entity_id, None)
        if task is not None:
            task.cancel()

    def _cancel_manual_start(self, entity_id: str) -> None:
        task = self._manual_start_tasks.pop(entity_id, None)
        if task is not None:
            task.cancel()

    def _valid_sonoff_working_target(self, value: float | None) -> bool:
        """Return true only for a Sonoff target that is not the OFF/frost value."""
        return value is not None and abs(float(value) - self.frost_temp) > TARGET_TOLERANCE

    @staticmethod
    def _target(state: State | None) -> float | None:
        if state is None:
            return None
        value = state.attributes.get(ATTR_TEMPERATURE)
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _different(a: float | None, b: float | None) -> bool:
        if a is None and b is None:
            return False
        if a is None or b is None:
            return True
        return abs(float(a) - float(b)) > TARGET_TOLERANCE

    def _expect(
        self, bucket: dict[str, _ExpectedValue], entity_id: str, value: Any
    ) -> None:
        bucket[entity_id] = _ExpectedValue(value=value, expires=monotonic() + EXPECTED_TIMEOUT)

    def _consume_expected(
        self,
        bucket: dict[str, _ExpectedValue],
        entity_id: str,
        value: Any,
        *,
        numeric: bool = False,
    ) -> bool:
        expected = bucket.get(entity_id)
        if expected is None:
            return False
        if monotonic() > expected.expires:
            bucket.pop(entity_id, None)
            return False

        if numeric:
            try:
                matches = abs(float(expected.value) - float(value)) <= TARGET_TOLERANCE
            except (TypeError, ValueError):
                matches = False
        else:
            matches = expected.value == value

        if matches:
            bucket.pop(entity_id, None)
            return True
        return False

    async def _save_state(self) -> None:
        await self._store.async_save(
            {
                "working_target": self._working_target,
                "desired_mode": self._desired_mode,
            }
        )
