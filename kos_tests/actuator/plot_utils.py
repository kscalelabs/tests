"""Utility functions for plotting motor responses."""

import os
from typing import Dict

import matplotlib.pyplot as plt

from kos_tests.actuator.logger import TestData


def create_motor_plots(
    test_data: TestData,
    motor_id_to_name: Dict[int, str],
    output_dir: str = ".",
    test_name: str = "test",
) -> None:
    """Create and save plots for each motor's performance."""
    print("Creating plots in", output_dir, "...")

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Validate data before plotting
    errors = test_data.validate_data()
    if errors:
        print("Data validation errors:")
        for error in errors:
            print(f"  {error}")
        return

    for motor_id, motor_data in test_data.motors.items():
        motor_name = motor_id_to_name.get(motor_id, f"motor_{motor_id}")

        plt.figure(figsize=(10, 6))

        # Position subplot
        plt.subplot(2, 1, 1)
        plt.plot(test_data.time_points, motor_data.commanded_positions, label="Commanded Position", color="blue")
        plt.plot(test_data.time_points, motor_data.actual_positions, label="Actual Position", color="red")
        plt.title(f"Motor {motor_name} (ID: {motor_id}) Response")
        plt.ylabel("Position (degrees)")
        plt.grid(True)
        plt.legend(loc="upper right")

        # Velocity subplot (if data is present)
        if test_data.send_velocity and motor_data.commanded_velocities is not None:
            plt.subplot(2, 1, 2)
            plt.plot(test_data.time_points, motor_data.commanded_velocities, label="Commanded Velocity", color="green")
            plt.plot(test_data.time_points, motor_data.actual_velocities, label="Actual Velocity", color="orange")
            plt.xlabel("Time (s)")
            plt.ylabel("Velocity (deg/s)")
            plt.grid(True)
            plt.legend(loc="upper right")
        else:
            plt.xlabel("Time (s)")

        plt.tight_layout()
        output_path = os.path.join(output_dir, f"motor_{motor_id}_{motor_name}_{test_name}_response.png")
        plt.savefig(output_path)
        plt.close()

    print("Plots saved.")
