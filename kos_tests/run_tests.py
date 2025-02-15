"""Runner script for actuator tests."""

import asyncio
from pathlib import Path

from kos_tests.actuator.piecewise import main as piecewise_main
from kos_tests.actuator.waveforms import sine, square, triangle
from kos_tests.config import load_config


async def run_tests(config_path: Path | None = None) -> None:
    """Run all configured actuator tests."""
    configs = load_config(config_path)

    for test_config in configs:
        print(f"\nRunning {test_config.test_type} test...")
        if test_config.test_type == "sine":
            await sine.main(test_config)
        elif test_config.test_type == "triangle":
            await triangle.main(test_config)
        elif test_config.test_type == "square":
            await square.main(test_config)
        elif test_config.test_type == "piecewise":
            await piecewise_main(test_config)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run actuator tests")
    parser.add_argument("--config", type=Path, help="Path to test configuration file")
    args = parser.parse_args()

    asyncio.run(run_tests(args.config))
