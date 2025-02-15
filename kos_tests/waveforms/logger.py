"""Data logging utilities for motor tests."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class MotorData:
    """Data container for a single motor's recorded values."""

    motor_id: int
    commanded_positions: list[float] = field(default_factory=list)
    actual_positions: list[float] = field(default_factory=list)
    commanded_velocities: list[float] | None = None
    actual_velocities: list[float] = field(default_factory=list)


@dataclass
class TestData:
    """Container for all test data."""

    time_points: list[float] = field(default_factory=list)
    motors: dict[int, MotorData] = field(default_factory=dict)
    send_velocity: bool = False

    def add_time_point(self, t: float) -> None:
        """Add a time point to the data."""
        self.time_points.append(t)

    def add_motor(self, motor_id: int) -> None:
        """Initialize data storage for a motor if it doesn't exist."""
        if motor_id not in self.motors:
            self.motors[motor_id] = MotorData(
                motor_id=motor_id, commanded_velocities=[] if self.send_velocity else None
            )

    def log_command(self, motor_id: int, position: float, velocity: float | None = None) -> None:
        """Log commanded values for a motor."""
        self.add_motor(motor_id)
        motor = self.motors[motor_id]
        motor.commanded_positions.append(position)
        if velocity is not None and motor.commanded_velocities is not None:
            motor.commanded_velocities.append(velocity)

    def log_state(self, motor_id: int, position: float, velocity: float) -> None:
        """Log actual state values for a motor."""
        self.add_motor(motor_id)
        motor = self.motors[motor_id]
        motor.actual_positions.append(position)
        motor.actual_velocities.append(velocity)

    def validate_data(self) -> list[str]:
        """Validate that all data arrays have consistent lengths."""
        errors = []
        for motor_id, motor in self.motors.items():
            expected_len = len(self.time_points)

            if len(motor.commanded_positions) != expected_len:
                errors.append(
                    f"Motor {motor_id}: commanded positions length mismatch "
                    f"({len(motor.commanded_positions)} != {expected_len})"
                )

            if len(motor.actual_positions) != expected_len:
                errors.append(
                    f"Motor {motor_id}: actual positions length mismatch "
                    f"({len(motor.actual_positions)} != {expected_len})"
                )

            if motor.commanded_velocities is not None:
                if len(motor.commanded_velocities) != expected_len:
                    errors.append(
                        f"Motor {motor_id}: commanded velocities length mismatch "
                        f"({len(motor.commanded_velocities)} != {expected_len})"
                    )

            if len(motor.actual_velocities) != expected_len:
                errors.append(
                    f"Motor {motor_id}: actual velocities length mismatch "
                    f"({len(motor.actual_velocities)} != {expected_len})"
                )

        return errors

    def save(self, path: str | Path) -> None:
        """Save test data to a JSON file.

        Args:
            path: Path to save the data to. Will create directories if they don't exist.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary format
        data_dict = {
            "time_points": self.time_points,
            "send_velocity": self.send_velocity,
            "motors": {str(motor_id): asdict(motor_data) for motor_id, motor_data in self.motors.items()},
        }

        # Save to file
        with open(path, "w") as f:
            json.dump(data_dict, f, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "TestData":
        """Load test data from a JSON file.

        Args:
            path: Path to the JSON file to load.

        Returns:
            TestData object with the loaded data.
        """
        path = Path(path)

        with open(path, "r") as f:
            data_dict = json.load(f)

        # Create new TestData instance
        test_data = cls(time_points=data_dict["time_points"], send_velocity=data_dict["send_velocity"])

        # Reconstruct motor data
        for motor_id_str, motor_dict in data_dict["motors"].items():
            motor_id = int(motor_id_str)
            test_data.motors[motor_id] = MotorData(
                motor_id=motor_id,
                commanded_positions=motor_dict["commanded_positions"],
                actual_positions=motor_dict["actual_positions"],
                commanded_velocities=motor_dict["commanded_velocities"],
                actual_velocities=motor_dict["actual_velocities"],
            )

        return test_data
