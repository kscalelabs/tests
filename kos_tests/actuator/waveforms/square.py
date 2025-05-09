"""Script to stress test the leg motors with a step wave.

This script will configure the leg motors with the appropriate gains and then move them in a step motion
between 0° and 5°.
"""

import argparse
import asyncio
import time

import pykos
from pykos.services.actuator import ActuatorCommand

from kos_tests.actuator.logger import TestData
from kos_tests.actuator.plot_utils import create_motor_plots
from kos_tests.config import ActuatorTest, MotorGroupConfig, MotorParams, WaveformConfig


async def run_step_test(kos: pykos.KOS, test_config: ActuatorTest) -> TestData | None:
    """Run step motion test on configured motors."""
    config = test_config.config

    if not isinstance(config, WaveformConfig):
        raise ValueError("Config must be a WaveformConfig")

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

        print("Starting step test with:")
        print(f"  Step amplitude: {config.amplitude}°")
        print(f"  Frequency: {config.frequency} Hz")
        print(f"  Duration: {config.duration} s")

        start_time = time.time()
        while time.time() - start_time < config.duration:
            t = time.time() - start_time
            test_data.add_time_point(t)

            # Calculate step position
            period = 1.0 / config.frequency
            cycle_position = (t % period) / period

            # Step between 0° and amplitude
            position = config.amplitude if cycle_position < 0.5 else 0.0
            velocity = 0.0 if config.send_velocity else None

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
    """Run step test with given configuration."""
    try:
        async with pykos.KOS() as kos:
            test_data = await run_step_test(kos, test_config)

            if test_data is not None:
                test_data.save(f"square_vel_{test_config.config.send_velocity}.json")

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
                    test_name=f"step_vel_{test_config.config.send_velocity}",
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
    # For command line usage, create a basic TestConfig
    parser = argparse.ArgumentParser(description="Run step test on leg motors")
    parser.add_argument("--frequency", type=float, default=0.5)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--send_velocity", action="store_true")
    args = parser.parse_args()

    motor_groups = {
        "strong": MotorGroupConfig(params=MotorParams(kp=250, kd=5, max_torque=80), motor_ids=[31, 34, 41, 44]),
        "medium": MotorGroupConfig(params=MotorParams(kp=150, kd=5, max_torque=60), motor_ids=[32, 33, 42, 43]),
        "weak": MotorGroupConfig(params=MotorParams(kp=40, kd=5, max_torque=17), motor_ids=[35, 45]),
    }

    # Create a basic test config for command-line usage
    config = WaveformConfig(
        amplitude=5.0,  # Fixed at 5 degrees for step test
        frequency=args.frequency,
        duration=args.duration,
        send_velocity=args.send_velocity,
        motor_groups=motor_groups,
    )

    # Use default motor groups from example config
    test_config = ActuatorTest(
        test_type="square",
        config=config,
    )

    asyncio.run(main(test_config))
