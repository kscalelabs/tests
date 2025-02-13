"""Runner script for waveform tests."""

import asyncio
from pathlib import Path

from kos_tests.config import load_config
from kos_tests.waveforms import sine, triangle


async def run_tests(config_path: Path | None = None) -> None:
    """Run all configured waveform tests."""
    configs = load_config(config_path)

    for test_config in configs:
        print(f"\nRunning {test_config.waveform_type} test...")
        if test_config.waveform_type == "sine":
            await sine.main(test_config.config)
        elif test_config.waveform_type == "triangle":
            await triangle.main(test_config.config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run waveform tests")
    parser.add_argument("--config", type=Path, help="Path to test configuration file")
    args = parser.parse_args()

    asyncio.run(run_tests(args.config))
