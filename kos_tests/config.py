#!/usr/bin/env python3
"""Configuration management for KOS tests."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

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
    motor_ids: list[int]


@dataclass
class BaseTestConfig:
    """Base configuration for all tests."""

    motor_groups: dict[str, MotorGroupConfig]
    send_velocity: bool = False
    active_motors: list[int] | None = None  # If None, use all motors
    duration: float = 10.0


@dataclass
class WaveformConfig(BaseTestConfig):
    """Configuration for waveform tests."""

    amplitude: float = 20.0
    frequency: float = 0.5


@dataclass
class PiecewiseConfig(BaseTestConfig):
    """Configuration for a piecewise motion test."""

    positions: list[float] = field(default_factory=list)


@dataclass
class ActuatorTest:
    """Configuration for an actuator test."""

    test_type: Literal["sine", "triangle", "square", "piecewise"]
    config: BaseTestConfig


def load_config(config_path: Path | None = None) -> list[ActuatorTest]:
    """Load test configurations from a YAML file."""
    if config_path is None:
        return []  # Require an explicit config file

    with open(config_path) as f:
        data = yaml.safe_load(f)

    # First, load the global motor groups definition
    global_motor_groups = data.get("motor_groups", {})

    configs: list[ActuatorTest] = []

    # Load waveform tests
    for test in data.get("waveform_tests", []):
        # Load basic waveform configuration
        wave_config = WaveformConfig(
            amplitude=test.get("amplitude", 20.0),
            frequency=test.get("frequency", 0.5),
            duration=test.get("duration", 10.0),
            send_velocity=test.get("send_velocity", False),
            active_motors=test.get("active_motors", None),
            motor_groups=_load_motor_groups(test, global_motor_groups),
        )

        configs.append(ActuatorTest(test_type=test["type"], config=wave_config))

    # Load piecewise tests
    for test in data.get("piecewise_tests", []):
        # Load piecewise configuration
        piecewise_config = PiecewiseConfig(
            positions=test["positions"],
            duration=test.get("duration", 5.0),
            send_velocity=test.get("send_velocity", False),
            active_motors=test.get("active_motors", None),
            motor_groups=_load_motor_groups(test, global_motor_groups),
        )

        configs.append(ActuatorTest(test_type="piecewise", config=piecewise_config))

    return configs


def _load_motor_groups(test: dict, global_motor_groups: dict) -> dict[str, MotorGroupConfig]:
    """Helper function to load motor group configurations."""
    motor_groups = {}
    for group_name, group_def in global_motor_groups.items():
        # Get default parameters from global definition
        default_params = group_def.get("default_params", {})
        motor_ids = group_def.get("motor_ids", [])

        # Get test-specific overrides if they exist
        test_group_config = test.get("motor_groups", {}).get(group_name, {})

        motor_groups[group_name] = MotorGroupConfig(
            params=MotorParams(
                kp=test_group_config.get("kp", default_params.get("kp", 0)),
                kd=test_group_config.get("kd", default_params.get("kd", 0)),
                max_torque=test_group_config.get("max_torque", default_params.get("max_torque", 0)),
            ),
            motor_ids=motor_ids,
        )
    return motor_groups
