import os
import matplotlib.pyplot as plt
from typing import List, Dict, Optional

def create_motor_plots(
    time_points: List[float],
    commanded_positions: Dict[int, List[float]],
    actual_positions: Dict[int, List[float]],
    commanded_velocities: Optional[Dict[int, List[float]]],
    actual_velocities: Dict[int, List[float]],
    use_velocity: bool,
    motor_id_to_name: Dict[int, str],
    output_dir: str = ".",
    test_name: str = "test"
) -> None:
    """Create and save plots for each motor's performance."""
    print("Creating plots in", output_dir, "...")
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    for motor_id, motor_name in motor_id_to_name.items():
        # Check that there is data for this motor
        if motor_id not in commanded_positions or len(commanded_positions[motor_id]) == 0:
            print(f"Skipping motor {motor_id} ({motor_name}) because no commanded position data was collected.")
            continue

        if len(time_points) != len(commanded_positions[motor_id]):
            print(
                f"Skipping motor {motor_id} ({motor_name}) because the number of time points ({len(time_points)}) "
                f"does not match the number of commanded position points ({len(commanded_positions[motor_id])})."
            )
            continue

        plt.figure(figsize=(10, 6))

        # Position subplot
        plt.subplot(2, 1, 1)
        plt.plot(time_points, commanded_positions[motor_id], label="Commanded Position", color="blue")
        plt.plot(time_points, actual_positions[motor_id], label="Actual Position", color="red")
        plt.title(f"Motor {motor_name} (ID: {motor_id}) Response")
        plt.ylabel("Position (degrees)")
        plt.grid(True)
        plt.legend(loc="upper right")

        # Velocity subplot (if requested and data is present)
        if use_velocity and commanded_velocities is not None:
            if motor_id not in commanded_velocities or len(commanded_velocities[motor_id]) == 0:
                print(f"Skipping velocity plot for motor {motor_id} ({motor_name}) because no velocity data was collected.")
            elif len(time_points) != len(commanded_velocities[motor_id]):
                print(f"Skipping velocity plot for motor {motor_id} ({motor_name}) due to mismatched data lengths.")
            else:
                plt.subplot(2, 1, 2)
                plt.plot(time_points, commanded_velocities[motor_id], label="Commanded Velocity", color="green")
                plt.plot(time_points, actual_velocities[motor_id], label="Actual Velocity", color="orange")
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
