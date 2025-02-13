"""Utility functions for plotting motor test results."""

import os
from pathlib import Path

import matplotlib.pyplot as plt


def create_motor_plots(
    time_points: list[float],
    commanded_positions: dict[int, list[float]],
    actual_positions: dict[int, list[float]],
    commanded_velocities: dict[int, list[float]],
    actual_velocities: dict[int, list[float]],
    use_velocity: bool,
    motor_id_to_name: dict[int, str],
    output_dir: Path | str = Path("plots"),
) -> None:
    """Create and save plots for each motor's performance.

    Args:
        time_points: List of time points
        commanded_positions: Dictionary of commanded positions for each motor
        actual_positions: Dictionary of actual positions for each motor
        commanded_velocities: Dictionary of commanded velocities for each motor
        actual_velocities: Dictionary of actual velocities for each motor
        use_velocity: Whether to plot velocity data
        motor_id_to_name: Dictionary mapping motor IDs to names
        output_dir: Directory to save plots in (default: "plots")
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"Creating plots in {output_dir}...")
    for motor_id, motor_name in motor_id_to_name.items():
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
        plt.savefig(output_dir / f"motor_{motor_id}_{motor_name}_response.png")
        plt.close()
    print(f"Plots saved in {output_dir}/")
