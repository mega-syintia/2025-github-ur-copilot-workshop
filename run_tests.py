#!/usr/bin/env python
"""
Test runner for the Pomodoro Timer application.
This script provides different options for running tests.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and display its output"""
    print(f"\n{'=' * 60}")
    print(f"📋 {description}")
    print(f"{'=' * 60}")
    print(f"Running: {' '.join(command)}")
    print()

    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        print(f"\n✅ {description} completed successfully!")
    else:
        print(f"\n❌ {description} failed with exit code {result.returncode}")

    return result.returncode


def main():
    """Main test runner function"""
    # Change to the project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Determine the Python executable path
    if sys.platform == "win32":
        python_exe = ".venv/Scripts/python.exe"
        if not os.path.exists(python_exe):
            python_exe = "python"
    else:
        python_exe = ".venv/bin/python"
        if not os.path.exists(python_exe):
            python_exe = "python"

    print("🍅 Pomodoro Timer - Test Runner")
    print(f"Using Python: {python_exe}")

    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        test_type = "all"

    exit_code = 0

    if test_type in ["all", "unit"]:
        # Run core unit tests
        exit_code |= run_command(
            [python_exe, "-m", "pytest", "tests/test_app.py", "-v", "--tb=short"],
            "Core Unit Tests",
        )

    if test_type in ["all", "integration"]:
        # Run integration tests
        exit_code |= run_command(
            [
                python_exe,
                "-m",
                "pytest",
                "tests/test_flask_app.py::TestFlaskRoutes",
                "tests/test_flask_app.py::TestFlaskConfiguration",
                "tests/test_static_templates.py",
                "-v",
                "--tb=short",
            ],
            "Integration Tests",
        )

    if test_type in ["all", "coverage"]:
        # Run with coverage
        exit_code |= run_command(
            [
                python_exe,
                "-m",
                "pytest",
                "tests/test_app.py",
                "tests/test_static_templates.py",
                "--cov=app",
                "--cov-report=term-missing",
            ],
            "Coverage Report",
        )

    if test_type == "quick":
        # Quick test run
        exit_code |= run_command(
            [
                python_exe,
                "-m",
                "pytest",
                "tests/test_app.py::TestStorage",
                "tests/test_app.py::TestFlaskApp",
                "-q",
            ],
            "Quick Tests",
        )

    if test_type == "help":
        print("""
Usage: python run_tests.py [option]

Options:
  all        - Run all stable tests with coverage (default)
  unit       - Run only unit tests
  integration- Run only integration tests  
  coverage   - Run tests with coverage report
  quick      - Run essential tests only
  help       - Show this help message

Examples:
  python run_tests.py            # Run all tests
  python run_tests.py unit       # Run only unit tests
  python run_tests.py coverage   # Run with coverage
        """)
        return 0

    print(f"\n{'=' * 60}")
    if exit_code == 0:
        print("🎉 All tests completed successfully!")
    else:
        print("⚠️  Some tests failed. Check output above for details.")
    print(f"{'=' * 60}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
