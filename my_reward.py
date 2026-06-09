# -*- coding: utf-8 -*-
"""Minimal student reward template.

Edit this file when you want to change what the agent learns.

Required contract:
  - MY_REWARD_CONFIG must be a dict.
  - compute_reward(...) must return (total_reward: float, components: dict).
  - Each item in components is recorded as ep_reward_<name> by the callbacks.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dogfight.sim.state_schema import StateIndex


MY_REWARD_CONFIG = {
    "step_penalty": -0.01,
    "pursuit_scale": 0.5,
    "pursuit_half_angle_deg": 30.0,
    "pursuit_range_m": 3000.0,
    "damage_scale": 20.0,
    "low_altitude_penalty": 0.1,
    "win_reward": 100.0,
    "loss_reward": -100.0,
    "draw_reward": -10.0,
}


def compute_reward(
    ownship_state,
    target_state,
    ownship_damage: float,
    target_damage: float,
    geo_info,
    wez_config: dict,
    reward_config: dict,
    terminated: bool,
    truncated: bool,
    end_condition: str,
) -> tuple[float, dict]:
    """Return a small runnable reward example.

    The arguments expose aircraft state, damage, geometry, WEZ settings, and
    termination status. Add your own tactical components here.
    """
    components: dict[str, float] = {
        "step": float(reward_config.get("step_penalty", -0.01)),
    }

    # Pursuit shaping: ATA × range gradient
    distance = geo_info._get_distance(ownship_state, target_state)
    ata = abs(geo_info._get_antenna_train_angle(ownship_state, target_state, False))
    half_angle = float(reward_config.get("pursuit_half_angle_deg", 30.0))
    pursuit_range = float(reward_config.get("pursuit_range_m", 3000.0))
    ata_factor = max(0.0, 1.0 - ata / half_angle)
    range_factor = max(0.0, 1.0 - distance / pursuit_range)
    components["pursuit"] = float(reward_config.get("pursuit_scale", 0.5)) * ata_factor * range_factor

    components["damage"] = float(reward_config.get("damage_scale", 20.0)) * (target_damage - ownship_damage)

    r_safety = 0.0
    if float(ownship_state[StateIndex.ALT]) < 600.0:
        r_safety = -float(reward_config.get("low_altitude_penalty", 0.1))
    components["safety"] = r_safety

    terminal_reward = 0.0
    if terminated or truncated:
        ownship_health = float(ownship_state[StateIndex.HEALTH])
        target_health = float(target_state[StateIndex.HEALTH])
        if target_health <= 0.0 < ownship_health:
            terminal_reward = float(reward_config.get("win_reward", 100.0))
        elif ownship_health <= 0.0 < target_health:
            terminal_reward = float(reward_config.get("loss_reward", -100.0))
        else:
            terminal_reward = float(reward_config.get("draw_reward", -10.0))
    components["terminal"] = terminal_reward

    return float(sum(components.values())), components


__all__ = ["MY_REWARD_CONFIG", "compute_reward"]
