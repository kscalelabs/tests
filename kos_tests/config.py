#!/usr/bin/env python3
"""Configuration management for KOS tests."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional

import yaml


@dataclass
class MotorParams:
    """Control parameters for a motor group."""

    kp: float
    kd: float
    max_torque: float


@dataclass
class MotorGroupConfig:
    """Configuration for a group of motors."""

    params: MotorParams
    motor_ids: List[int]


@dataclass
class WaveformConfig:
    """Base configuration for waveform tests."""

    amplitude: float = 20.0
    frequency: float = 0.5
    duration: float = 10.0
    send_velocity: bool = False
    active_motors: Optional[List[int]] = None  # If None, use all motors


@dataclass
class TestConfig:
    """Configuration for all waveform tests."""

    waveform_type: Literal["sine", "triangle"]
    config: WaveformConfig
    motor_groups: Dict[str, MotorGroupConfig]


def load_config(config_path: Optional[Path] = None) -> List[TestConfig]:
    """Load test configurations from a YAML file."""
    if config_path is None:
        return []  # Require an explicit config file

    with open(config_path) as f:
        data = yaml.safe_load(f)

    # First, load the global motor groups definition
    global_motor_groups = data.get("motor_groups", {})

    configs = []
    for test in data.get("waveform_tests", []):
        # Load basic waveform configuration
        config = WaveformConfig(
            amplitude=test.get("amplitude", 20.0),
            frequency=test.get("frequency", 0.5),
            duration=test.get("duration", 10.0),
            send_velocity=test.get("send_velocity", False),
            active_motors=test.get("active_motors", None),
        )

        # Load motor group configurations
        motor_groups = {}
        for group_name, group_config in test.get("motor_groups", {}).items():
            # Get motor IDs and default parameters from the global definition
            group_def = global_motor_groups.get(group_name, {})
            motor_ids = group_def.get("motor_ids", [])
            default_params = group_def.get("default_params", {})

            motor_groups[group_name] = MotorGroupConfig(
                params=MotorParams(
                    kp=group_config.get("kp", default_params.get("kp", 0)),
                    kd=group_config.get("kd", default_params.get("kd", 0)),
                    max_torque=group_config.get("max_torque", default_params.get("max_torque", 0)),
                ),
                motor_ids=motor_ids,
            )

        configs.append(TestConfig(waveform_type=test["type"], config=config, motor_groups=motor_groups))

    return configs
