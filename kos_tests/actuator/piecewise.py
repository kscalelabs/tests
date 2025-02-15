"""Script to test the leg motors with piecewise motion.

This script will configure the leg motors with the appropriate gains and then move them through
a sequence of positions.
"""

import argparse
import asyncio
import time

import pykos
from pykos.services.actuator import ActuatorCommand

from kos_tests.actuator.logger import TestData
from kos_tests.actuator.plot_utils import create_motor_plots
from kos_tests.config import ActuatorTest, MotorGroupConfig, MotorParams, PiecewiseConfig


async def run_piecewise_test(kos: pykos.KOS, test_config: ActuatorTest) -> TestData | None:
    """Run piecewise motion test on configured motors."""
    config = test_config.config
    assert isinstance(config, PiecewiseConfig)

    # Get active motors from config or use all motors from all groups
    active_motors = (
        config.active_motors
        if config.active_motors is not None
        else [motor_id for group in test_config.config.motor_groups.values() for motor_id in group.motor_ids]
    )

    print(f"Active motors: {active_motors}")
    print(f"Motor groups: {test_config.config.motor_groups}")

    # Initialize test data
    test_data = TestData(send_velocity=config.send_velocity)

    try:
        # First disable all motors
        print("Disabling motors...")
        for motor_id in active_motors:
            try:
                await kos.actuator.configure_actuator(actuator_id=motor_id, torque_enabled=False)
                print(f"Disabled motor {motor_id}")
            except Exception as e:
                print(f"Failed to disable motor {motor_id}: {e}")

        await asyncio.sleep(1)

        # Configure motors with appropriate gains based on their groups
        print("Configuring motors...")
        for group_name, group_config in test_config.config.motor_groups.items():
            print(f"Configuring group {group_name}: {group_config}")
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
                        print(
                            f"Configured motor {motor_id} with kp={group_config.params.kp}, kd={group_config.params.kd}"
                        )
                    except Exception as e:
                        print(f"Failed to configure motor {motor_id}: {e}")

        print("Starting piecewise motion test with:")
        print(f"  Positions: {config.positions}")
        print(f"  Duration: {config.duration} s")

        # Calculate time points for each position
        time_per_position = config.duration / (len(config.positions) - 1)

        start_time = time.time()
        current_segment = 0

        while time.time() - start_time < config.duration:
            t = time.time() - start_time
            test_data.add_time_point(t)

            # Calculate current segment and interpolation factor
            current_segment = int(t / time_per_position)
            if current_segment >= len(config.positions) - 1:
                current_segment = len(config.positions) - 2

            segment_progress = (t - current_segment * time_per_position) / time_per_position

            # Linear interpolation between positions
            start_pos = config.positions[current_segment]
            end_pos = config.positions[current_segment + 1]
            position = start_pos + (end_pos - start_pos) * segment_progress

            # Calculate velocity if needed
            velocity = (end_pos - start_pos) / time_per_position if config.send_velocity else None

            # Prepare commands and log commanded values
            commands = []
            for motor_id in active_motors:
                command: ActuatorCommand = {"actuator_id": motor_id, "position": position}
                if config.send_velocity:
                    assert velocity is not None
                    command["velocity"] = velocity
                commands.append(command)
                test_data.log_command(motor_id, position, velocity)

            # Send commands and get state
            try:
                _, states = await asyncio.gather(
                    kos.actuator.command_actuators(commands),
                    kos.actuator.get_actuators_state(active_motors),
                )

                # Log actual states
                for state in states.states:
                    test_data.log_state(state.actuator_id, state.position, state.velocity)

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
        return None
    finally:
        print("\n" * (len(active_motors) + 2))

    return test_data


async def main(test_config: ActuatorTest) -> None:
    """Run piecewise test with given configuration."""
    try:
        async with pykos.KOS() as kos:
            test_data = await run_piecewise_test(kos, test_config)

            if test_data is not None:
                # Save the raw data
                test_data.save(f"data/piecewise_vel_{test_config.config.send_velocity}.json")

                # Create motor ID to name mapping for plots
                motor_id_to_name = {
                    motor_id: f"{group_name}_{i}"
                    for group_name, group in test_config.config.motor_groups.items()
                    for i, motor_id in enumerate(group.motor_ids)
                }

                create_motor_plots(
                    test_data,
                    motor_id_to_name,
                    output_dir="plots",
                    test_name=f"piecewise_vel_{test_config.config.send_velocity}",
                )

        print("\nDisabling motors...")
        async with pykos.KOS() as kos:
            active_motors = (
                test_config.config.active_motors
                if test_config.config.active_motors is not None
                else [motor_id for group in test_config.config.motor_groups.values() for motor_id in group.motor_ids]
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
    parser = argparse.ArgumentParser(description="Run piecewise motion test on leg motors")
    parser.add_argument(
        "--positions", type=float, nargs="+", default=[0, 10, 0, -10, 0], help="List of positions to move through"
    )
    parser.add_argument("--duration", type=float, default=5.0, help="Total duration of the motion in seconds")
    parser.add_argument("--send_velocity", action="store_true", help="Include velocity commands")
    args = parser.parse_args()

    motor_groups = {
        "strong": MotorGroupConfig(params=MotorParams(kp=250, kd=5, max_torque=80), motor_ids=[31, 34, 41, 44]),
        "medium": MotorGroupConfig(params=MotorParams(kp=150, kd=5, max_torque=60), motor_ids=[32, 33, 42, 43]),
        "weak": MotorGroupConfig(params=MotorParams(kp=40, kd=5, max_torque=17), motor_ids=[35, 45]),
    }

    config = PiecewiseConfig(
        positions=args.positions,
        duration=args.duration,
        send_velocity=args.send_velocity,
        motor_groups=motor_groups,
    )

    # Use default motor groups from example config
    test_config = ActuatorTest(
        test_type="piecewise",
        config=config,
    )

    asyncio.run(main(test_config))
