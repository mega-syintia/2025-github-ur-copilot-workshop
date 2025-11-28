# Pomodoro Timer

A fully-featured Pomodoro Timer web application with customizable settings, session tracking, and persistent storage.

## Features

- ⏱️ **Configurable Timer**: Customizable work sessions (default: 25min), short breaks (5min), and long breaks (15min)
- 🔄 **Automatic Cycles**: Automatic progression through work → break cycles with configurable long break intervals
- 💾 **Persistent Settings**: Settings saved to browser's localStorage
- 📊 **Session Tracking**: Complete history of all timer sessions with timestamps
- 🔗 **Real-time API**: RESTful backend with session logging and status persistence
- ✅ **Full Test Coverage**: Comprehensive test suite with pytest

## Quick Start

1. **Setup environment and install dependencies:**

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. **Run the application:**

```powershell
python .\app.py
```

3. **Open your browser:**
   - Navigate to `http://127.0.0.1:5000/`
   - Configure your preferred durations in the Settings section
   - Click "Save Settings" to persist your configuration
   - Use Start/Pause/Reset/Skip controls to manage your Pomodoro sessions

## Testing

This project includes a comprehensive test suite covering unit tests, integration tests, and edge cases.

### Running Tests

1. **Activate the virtual environment:**
```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows Command Prompt  
.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate
```

2. **Using the test runner (recommended):**
```powershell
# Run all stable tests
python run_tests.py

# Run specific test types
python run_tests.py unit          # Unit tests only
python run_tests.py integration   # Integration tests only  
python run_tests.py coverage      # Tests with coverage report
python run_tests.py quick         # Essential tests only

# Show help
python run_tests.py help
```

3. **Direct pytest commands:**
```powershell
# Basic test run
pytest

# Verbose output with test names
pytest -v

# Quick mode (less verbose)
pytest -q

# Run specific test file
pytest tests/test_app.py

# Run specific test class
pytest tests/test_app.py::TestStorage

# Run specific test function
pytest tests/test_app.py::test_post_session_and_get_sessions
```

3. **Run tests with coverage:**
```powershell
# Coverage report in terminal
pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open coverage report (Windows)
start htmlcov/index.html
```

4. **Run tests with different output formats:**
```powershell
# Stop on first failure
pytest -x

# Run failed tests from last run
pytest --lf

# Run tests in parallel (if pytest-xdist installed)
pytest -n auto
```

### Test Structure

- **`tests/test_app.py`**: Core functionality tests for Storage class and Flask app
- **`tests/test_flask_app.py`**: HTTP endpoint tests, error handling, and security tests  
- **`tests/test_storage.py`**: Advanced Storage class tests including edge cases and performance
- **`tests/test_static_templates.py`**: Template rendering and static file serving tests

### Test Coverage

The current test suite achieves ~68% code coverage including:
- ✅ Storage class (file operations, thread safety, error handling)
- ✅ Flask API endpoints (POST/GET with validation)
- ✅ Session lifecycle management
- ✅ Status tracking and persistence
- ✅ Edge cases (malformed data, concurrent access, file corruption)
- ✅ Integration workflows (complete Pomodoro sessions)

### Testing Dependencies

Required testing packages (already in `requirements.txt`):
- `pytest>=7.0` - Testing framework
- `pytest-cov>=4.0` - Coverage reporting
- `pytest-mock>=3.10` - Mocking utilities  
- `coverage>=7.0` - Coverage measurement

### Continuous Integration

Tests are designed to run in CI/CD environments with temporary directories and isolated test data.

## API Endpoints

- `POST /api/session` - Log session events (started, paused, completed, skipped, reset)
- `GET /api/sessions` - Retrieve session history
- `GET /api/status` - Get current timer status

## Architecture

- **Backend**: Flask with file-based persistence (JSONL for sessions, JSON for status)
- **Frontend**: Vanilla JavaScript SPA with localStorage for settings
- **Storage**: Thread-safe file operations with atomic writes for status updates
- **Testing**: pytest with temporary directories for isolated test runs
# GitHub Copilot Workshop

This is a sample repository for Github Copilot Workshop in Github Universe Recap 2025, Jakarta, Indonesia.

Using the files in this repository, we are going to create a web application for Pomodoro Technique using Python, JavaScript, HTML, and CSS.

## Installation

We need to have `uv` and `venv` installed for this project.

### uv

`uv` is an extremely fast Python package and project manager, written in Rust. Open  [this link](https://docs.astral.sh/uv/#installation) for the installation information.


### venv

`venv` is a module included with Python (version 3.3 and later) used to create isolated Python virtual environments.

After `uv` is available on your system, install `venv` to create a virtual environment for this work project. Go to the root of your project and run this command:
```bash
uv venv
```

Then, activate virtual environment:
```bash
source .venv/bin/activate
```

Note: to deactivate virtual environment:
```bash
deactivate
```