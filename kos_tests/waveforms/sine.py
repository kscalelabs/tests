"""Script to stress test the leg motors with a sinusoidal wave.

This script will configure the leg motors with the appropriate gains and then move them in a sinusoidal motion.
"""

import argparse
import asyncio
import math
import time
from collections import defaultdict

import matplotlib.pyplot as plt
import pykos
from pykos.services.actuator import ActuatorCommand

# Define leg motor IDs and their names for reference
LEG_MOTORS = {
    # Left leg
    "left_hip_pitch": 31,
    "left_hip_roll": 32,
    "left_hip_yaw": 33,
    "left_knee": 34,
    "left_ankle": 35,
    # Right leg
    "right_hip_pitch": 41,
    "right_hip_roll": 42,
    "right_hip_yaw": 43,
    "right_knee": 44,
    "right_ankle": 45,
}

# Motor type groupings for different gains
R04_IDS = [31, 34, 41, 44]  # Stronger motors
R03_IDS = [32, 33, 42, 43]  # Medium motors
R02_IDS = [35, 45]  # Smaller motors


def create_motor_plots(
    time_points: list[float],
    commanded_positions: dict[int, list[float]],
    actual_positions: dict[int, list[float]],
    commanded_velocities: dict[int, list[float]],
    actual_velocities: dict[int, list[float]],
    use_velocity: bool,
) -> None:
    """Create and save plots for each motor's performance."""
    print("Creating plots...")
    for motor_name, motor_id in LEG_MOTORS.items():
        plt.figure(figsize=(10, 6))

        # Position subplot
        plt.subplot(2, 1, 1)
        plt.plot(time_points, commanded_positions[motor_id], label="Commanded Position", color="blue")
        plt.plot(time_points, actual_positions[motor_id], label="Actual Position", color="red")
        plt.title(f"Motor {motor_name} (ID: {motor_id}) Response")
        plt.ylabel("Position (degrees)")
        plt.grid(True)
        plt.legend(loc="upper right")

        # Velocity subplot
        if use_velocity:
            plt.subplot(2, 1, 2)
            plt.plot(time_points, commanded_velocities[motor_id], label="Commanded Velocity", color="green")
            plt.plot(time_points, actual_velocities[motor_id], label="Actual Velocity", color="orange")
            plt.xlabel("Time (s)")
            plt.ylabel("Velocity (deg/s)")
            plt.grid(True)
            plt.legend(loc="upper right")

        plt.tight_layout()
        # Save plot
        plt.savefig(f"motor_{motor_id}_{motor_name}_response.png")
        plt.close()
    print("Plots saved.")


async def run_sine_test(
    kos: pykos.KOS, amplitude: float, frequency: float, duration: float, use_velocity: bool
) -> tuple:
    """Run sine wave motion test on all leg motors.

    Returns collected data for plotting.
    """
    # Data collection dictionaries
    time_points = []
    commanded_positions = defaultdict(list)
    actual_positions = defaultdict(list)
    commanded_velocities: dict[int, list[float]] | None = defaultdict(list) if use_velocity else None
    actual_velocities = defaultdict(list)

    try:
        # First disable all motors
        print("Disabling motors...")
        for motor_id in LEG_MOTORS.values():
            try:
                await kos.actuator.configure_actuator(actuator_id=motor_id, torque_enabled=False)
            except Exception as e:
                print(f"Failed to disable motor {motor_id}: {e}")

        await asyncio.sleep(1)

        # Configure motors with appropriate gains based on type
        print("Configuring motors...")
        for motor_id in LEG_MOTORS.values():
            try:
                if motor_id in R04_IDS:
                    await kos.actuator.configure_actuator(
                        actuator_id=motor_id, kp=250, kd=5, max_torque=80, torque_enabled=True
                    )
                elif motor_id in R03_IDS:
                    await kos.actuator.configure_actuator(
                        actuator_id=motor_id, kp=150, kd=5, max_torque=60, torque_enabled=True
                    )
                else:  # R02_IDS
                    await kos.actuator.configure_actuator(
                        actuator_id=motor_id, kp=40, kd=5, max_torque=17, torque_enabled=True
                    )
            except Exception as e:
                print(f"Failed to configure motor {motor_id}: {e}")

        print("Starting sine wave test with:")
        print(f"  Amplitude: ±{amplitude}°")
        print(f"  Frequency: {frequency} Hz")
        print(f"  Duration: {duration} s")

        start_time = time.time()
        while time.time() - start_time < duration:
            t = time.time() - start_time
            time_points.append(t)

            # Calculate sine wave position and velocity
            angular_freq = 2 * math.pi * frequency
            position = amplitude * math.sin(angular_freq * t)
            # Velocity is the derivative: d/dt(A*sin(ωt)) = A*ω*cos(ωt)
            velocity = amplitude * angular_freq * math.cos(angular_freq * t) if use_velocity else None

            # Prepare commands for all motors
            commands = []
            for motor_id in LEG_MOTORS.values():
                command: ActuatorCommand = {"actuator_id": motor_id, "position": position}
                if use_velocity:
                    assert velocity is not None
                    command["velocity"] = velocity
                commands.append(command)

            # Record commanded values
            for motor_id in LEG_MOTORS.values():
                commanded_positions[motor_id].append(position)
                if use_velocity:
                    assert velocity is not None
                    assert commanded_velocities is not None
                    commanded_velocities[motor_id].append(velocity)

            # Send commands and get state
            try:
                _, states = await asyncio.gather(
                    kos.actuator.command_actuators(commands),
                    kos.actuator.get_actuators_state(list(LEG_MOTORS.values())),
                )

                # Record actual positions and velocities
                for state in states.states:
                    actual_positions[state.actuator_id].append(state.position)
                    actual_velocities[state.actuator_id].append(state.velocity)

                # Print status (clear line and move cursor up for clean output)
                print("\033[K", end="")  # Clear line
                print(f"Time: {t:.2f}s")
                print("\033[K", end="")  # Clear line
                print(f"Command: {position:.2f}°")
                for state in states.states:
                    print("\033[K", end="")  # Clear line
                    print(f"Motor {state.actuator_id}: {state.position:.2f}°")
                print("\033[F" * (len(states.states) + 2), end="")  # Move cursor up

            except Exception as e:
                print(f"Error during execution: {e}")

            await asyncio.sleep(0.01)  # 100Hz control rate

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nTest interrupted in run_sine_test!")
    finally:
        print("\n" * (len(LEG_MOTORS) + 2))  # Clear status display
        return time_points, commanded_positions, actual_positions, commanded_velocities, actual_velocities


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run sinusoidal test on leg motors")
    parser.add_argument("--amplitude", type=float, default=20.0, help="Sine wave amplitude in degrees (default: 20.0)")
    parser.add_argument("--frequency", type=float, default=0.5, help="Sine wave frequency in Hz (default: 0.5)")
    parser.add_argument("--duration", type=float, default=10.0, help="Test duration in seconds (default: 10.0)")
    parser.add_argument("--send_velocity", action="store_true", help="Include velocity commands")
    args = parser.parse_args()

    collected_data = None
    try:
        async with pykos.KOS() as kos:
            collected_data = await run_sine_test(kos, args.amplitude, args.frequency, args.duration, args.send_velocity)

            if collected_data:
                time_points, commanded_positions, actual_positions, commanded_velocities, actual_velocities = (
                    collected_data
                )
                create_motor_plots(
                    time_points,
                    commanded_positions,
                    actual_positions,
                    commanded_velocities,
                    actual_velocities,
                    args.send_velocity,
                )

        print("\nDisabling motors...")
        async with pykos.KOS() as kos:
            for motor_id in LEG_MOTORS.values():
                try:
                    await kos.actuator.configure_actuator(actuator_id=motor_id, torque_enabled=False)
                except Exception as e:
                    print(f"Failed to disable motor {motor_id}: {e}")
        print("Motors disabled.")
    except Exception as e:
        print(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
