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
    "pursuit_half_angle_deg": 10.0,
    "pursuit_range_m": 1500.0,
    # 중간행동: ATA < aim_threshold_deg 일 때 조준 보상
    "aim_threshold_deg": 5.0,
    "aim_bonus": 0.3,
    # P1: WEZ 기하학적 조건(ATA+거리)으로 직접 보상
    "in_wez_bonus": 3.0,
    "damage_scale": 20.0,
    # 고도 그래디언트: 3000m 이하부터 비례 패널티 (binary → gradient)
    "low_altitude_m": 3000.0,
    "low_altitude_penalty": 1.0,
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

    # Pursuit shaping: ATA x range gradient
    distance = geo_info._get_distance(ownship_state, target_state)
    ata = abs(geo_info._get_antenna_train_angle(ownship_state, target_state, False))
    half_angle = float(reward_config.get("pursuit_half_angle_deg", 10.0))
    pursuit_range = float(reward_config.get("pursuit_range_m", 1500.0))
    ata_factor = max(0.0, 1.0 - ata / half_angle)
    range_factor = max(0.0, 1.0 - distance / pursuit_range)
    components["pursuit"] = float(reward_config.get("pursuit_scale", 0.5)) * ata_factor * range_factor

    # 중간행동: 조준 보상 — ATA < aim_threshold_deg 일 때 소량 보상
    aim_threshold = float(reward_config.get("aim_threshold_deg", 5.0))
    components["aim"] = (
        float(reward_config.get("aim_bonus", 0.3))
        if ata <= aim_threshold
        else 0.0
    )

    components["damage"] = float(reward_config.get("damage_scale", 20.0)) * (target_damage - ownship_damage)

    # WEZ 기하학적 조건: ATA <= wez_angle AND min_range <= distance <= max_range
    wez_angle = float(wez_config.get("angle_deg", 2.0))
    wez_min = float(wez_config.get("min_range_m", 152.0))
    wez_max = float(wez_config.get("max_range_m", 914.0))
    in_wez_geom = (ata <= wez_angle and wez_min <= distance <= wez_max)
    components["in_wez"] = (
        float(reward_config.get("in_wez_bonus", 3.0))
        if in_wez_geom
        else 0.0
    )

    # 고도 그래디언트: low_altitude_m 이하부터 비례 패널티
    r_safety = 0.0
    alt = float(ownship_state[StateIndex.ALT])
    alt_threshold = float(reward_config.get("low_altitude_m", 3000.0))
    if alt < alt_threshold:
        alt_factor = (alt_threshold - alt) / alt_threshold
        r_safety = -float(reward_config.get("low_altitude_penalty", 1.0)) * alt_factor
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
