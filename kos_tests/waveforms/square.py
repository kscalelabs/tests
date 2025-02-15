"""Script to stress test the leg motors with a step wave.

This script will configure the leg motors with the appropriate gains and then move them in a step motion
between 0° and 5°.
"""

import argparse
import asyncio
import time
from collections import defaultdict

import pykos
from pykos.services.actuator import ActuatorCommand

from kos_tests.config import MotorGroupConfig, MotorParams, TestConfig, WaveformConfig
from kos_tests.waveforms.plot_utils import create_motor_plots


async def run_step_test(kos: pykos.KOS, test_config: TestConfig) -> tuple:
    """Run step motion test on configured motors."""
    config = test_config.config

    # Get active motors from config or use all motors from all groups
    active_motors = (
        config.active_motors
        if config.active_motors is not None
        else [motor_id for group in test_config.motor_groups.values() for motor_id in group.motor_ids]
    )

    # Data collection dictionaries
    time_points = []
    commanded_positions = defaultdict(list)
    actual_positions = defaultdict(list)
    commanded_velocities: dict[int, list[float]] | None = defaultdict(list) if config.send_velocity else None
    actual_velocities = defaultdict(list)

    try:
        # First disable all motors
        print("Disabling motors...")
        for motor_id in active_motors:
            try:
                await kos.actuator.configure_actuator(actuator_id=motor_id, torque_enabled=False)
            except Exception as e:
                print(f"Failed to disable motor {motor_id}: {e}")

        await asyncio.sleep(1)

        # Configure motors with appropriate gains based on their groups
        print("Configuring motors...")
        for _, group_config in test_config.motor_groups.items():
            for motor_id in group_config.motor_ids:
                if motor_id in active_motors:
                    try:
                        await kos.actuator.configure_actuator(
                            actuator_id=motor_id,
                            kp=group_config.params.kp,
                            kd=group_config.params.kd,
                            max_torque=group_config.params.max_torque,
                            torque_enabled=True,
                        )
                    except Exception as e:
                        print(f"Failed to configure motor {motor_id}: {e}")

        print("Starting step test with:")
        print(f"  Step amplitude: {config.amplitude}°")
        print(f"  Frequency: {config.frequency} Hz")
        print(f"  Duration: {config.duration} s")

        start_time = time.time()
        while time.time() - start_time < config.duration:
            t = time.time() - start_time
            time_points.append(t)

            # Calculate step position
            period = 1.0 / config.frequency
            cycle_position = (t % period) / period

            # Step between 0° and 5°
            position = config.amplitude if cycle_position < 0.5 else 0.0
            velocity = 0.0 if config.send_velocity else None

            # Prepare commands for active motors
            commands = []
            for motor_id in active_motors:
                command: ActuatorCommand = {"actuator_id": motor_id, "position": position}
                if config.send_velocity:
                    assert velocity is not None
                    command["velocity"] = velocity
                commands.append(command)

            # Record commanded values
            for motor_id in active_motors:
                commanded_positions[motor_id].append(position)
                if config.send_velocity:
                    assert velocity is not None
                    assert commanded_velocities is not None
                    commanded_velocities[motor_id].append(velocity)

            # Send commands and get state
            try:
                _, states = await asyncio.gather(
                    kos.actuator.command_actuators(commands),
                    kos.actuator.get_actuators_state(active_motors),
                )

                # Record actual positions and velocities
                for state in states.states:
                    actual_positions[state.actuator_id].append(state.position)
                    actual_velocities[state.actuator_id].append(state.velocity)

                # Print status
                print("\033[K", end="")
                print(f"Time: {t:.2f}s")
                print("\033[K", end="")
                print(f"Command: {position:.2f}°")
                for state in states.states:
                    print("\033[K", end="")
                    print(f"Motor {state.actuator_id}: {state.position:.2f}°")
                print("\033[F" * (len(states.states) + 2), end="")

            except Exception as e:
                print(f"Error during execution: {e}")

            await asyncio.sleep(0.01)  # 100Hz control rate

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nTest interrupted!")
    finally:
        print("\n" * (len(active_motors) + 2))
        return time_points, commanded_positions, actual_positions, commanded_velocities, actual_velocities


async def main(test_config: TestConfig) -> None:
    """Run step test with given configuration."""
    try:
        async with pykos.KOS() as kos:
            collected_data = await run_step_test(kos, test_config)

            if collected_data:
                time_points, commanded_positions, actual_positions, commanded_velocities, actual_velocities = (
                    collected_data
                )

                # Create motor ID to name mapping for plots
                motor_id_to_name = {
                    motor_id: f"{group_name}_{i}"
                    for group_name, group in test_config.motor_groups.items()
                    for i, motor_id in enumerate(group.motor_ids)
                }

                create_motor_plots(
                    time_points,
                    commanded_positions,
                    actual_positions,
                    commanded_velocities,
                    actual_velocities,
                    test_config.config.send_velocity,
                    motor_id_to_name,
                    output_dir="plots",
                    test_name=f"step_vel_{test_config.config.send_velocity}",
                )

        print("\nDisabling motors...")
        async with pykos.KOS() as kos:
            active_motors = (
                test_config.config.active_motors
                if test_config.config.active_motors is not None
                else [motor_id for group in test_config.motor_groups.values() for motor_id in group.motor_ids]
            )
            for motor_id in active_motors:
                try:
                    await kos.actuator.configure_actuator(actuator_id=motor_id, torque_enabled=False)
                except Exception as e:
                    print(f"Failed to disable motor {motor_id}: {e}")
        print("Motors disabled.")
    except Exception as e:
        print(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    # For command line usage, create a basic TestConfig
    parser = argparse.ArgumentParser(description="Run step test on leg motors")
    parser.add_argument("--frequency", type=float, default=0.5)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--send_velocity", action="store_true")
    args = parser.parse_args()

    # Create a basic test config for command-line usage
    config = WaveformConfig(
        amplitude=5.0,  # Fixed at 5 degrees for step test
        frequency=args.frequency,
        duration=args.duration,
        send_velocity=args.send_velocity
    )

    # Use default motor groups from example config
    test_config = TestConfig(
        waveform_type="step",
        config=config,
        motor_groups={
            "strong": MotorGroupConfig(params=MotorParams(kp=250, kd=5, max_torque=80), motor_ids=[31, 34, 41, 44]),
            "medium": MotorGroupConfig(params=MotorParams(kp=150, kd=5, max_torque=60), motor_ids=[32, 33, 42, 43]),
            "weak": MotorGroupConfig(params=MotorParams(kp=40, kd=5, max_torque=17), motor_ids=[35, 45]),
        },
    )

    asyncio.run(main(test_config))



