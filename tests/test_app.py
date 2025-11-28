import os
import tempfile
import json
import pytest
from unittest.mock import patch, mock_open
from datetime import datetime, timezone
from threading import Thread
import time
from app import create_app, Storage


@pytest.fixture
def client(tmp_path):
    logs_dir = tmp_path / "logs"
    app = create_app({"TESTING": True, "LOGS_DIR": str(logs_dir)})
    with app.test_client() as c:
        yield c


@pytest.fixture
def storage(tmp_path):
    logs_dir = tmp_path / "logs"
    return Storage(str(logs_dir))


@pytest.fixture
def app_instance(tmp_path):
    logs_dir = tmp_path / "logs"
    return create_app({"TESTING": True, "LOGS_DIR": str(logs_dir)})


def test_post_session_and_get_sessions(client):
    r = client.post("/api/session", json={"event": "started", "meta": {"foo": "bar"}})
    assert r.status_code == 201
    r = client.get("/api/sessions")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert data[-1]["event"] == "started"


def test_invalid_event(client):
    r = client.post("/api/session", json={"event": 123})
    assert r.status_code == 400


def test_status_write_and_read(client):
    r = client.post(
        "/api/session", json={"event": "status", "set_status": {"running": True}}
    )
    assert r.status_code == 201
    r = client.get("/api/status")
    assert r.status_code == 200
    s = r.get_json()
    assert s.get("running") is True


def test_session_with_meta(client):
    r = client.post(
        "/api/session",
        json={
            "event": "completed",
            "meta": {"type": "work", "cycle": 1, "duration": 1500},
        },
    )
    assert r.status_code == 201

    r = client.get("/api/sessions")
    data = r.get_json()
    assert data[-1]["meta"]["type"] == "work"
    assert data[-1]["meta"]["cycle"] == 1


def test_multiple_sessions(client):
    events = ["started", "paused", "started", "completed"]
    for event in events:
        r = client.post("/api/session", json={"event": event})
        assert r.status_code == 201

    r = client.get("/api/sessions")
    data = r.get_json()
    assert len(data) == 4
    assert [s["event"] for s in data] == events


# ==================== Storage Class Tests ====================


class TestStorage:
    """Test the Storage class independently"""

    def test_storage_init_creates_directories(self, tmp_path):
        """Test that Storage initialization creates necessary directories and files"""
        logs_dir = tmp_path / "test_logs"
        storage = Storage(str(logs_dir))

        assert logs_dir.exists()
        assert (logs_dir / "sessions.jsonl").exists()
        assert (logs_dir / "status.json").exists()

    def test_storage_init_with_default_directory(self):
        """Test Storage initialization with default directory"""
        storage = Storage()
        assert storage.logs_dir == os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logs"
        )

    def test_append_session(self, storage):
        """Test appending session data"""
        session_data = {
            "timestamp": "2025-11-28T10:00:00Z",
            "event": "start",
            "meta": {"type": "work"},
        }
        storage.append_session(session_data)

        sessions = storage.read_sessions()
        assert len(sessions) == 1
        assert sessions[0] == session_data

    def test_append_multiple_sessions(self, storage):
        """Test appending multiple session entries"""
        sessions_data = [
            {"timestamp": "2025-11-28T10:00:00Z", "event": "start", "meta": {}},
            {"timestamp": "2025-11-28T10:01:00Z", "event": "pause", "meta": {}},
            {"timestamp": "2025-11-28T10:02:00Z", "event": "resume", "meta": {}},
        ]

        for session in sessions_data:
            storage.append_session(session)

        stored_sessions = storage.read_sessions()
        assert len(stored_sessions) == 3
        assert stored_sessions == sessions_data

    def test_read_sessions_empty_file(self, storage):
        """Test reading sessions from empty file"""
        sessions = storage.read_sessions()
        assert sessions == []

    def test_read_sessions_with_invalid_json_lines(self, storage):
        """Test reading sessions with invalid JSON lines (should skip them)"""
        # Write some valid and invalid JSON lines directly to file
        with open(storage.sessions_file, "w") as f:
            f.write('{"event": "valid"}\n')
            f.write("invalid json line\n")
            f.write('{"event": "another_valid"}\n')
            f.write("\n")  # empty line
            f.write('{"incomplete": \n')

        sessions = storage.read_sessions()
        assert len(sessions) == 2
        assert sessions[0]["event"] == "valid"
        assert sessions[1]["event"] == "another_valid"

    def test_write_and_read_status(self, storage):
        """Test writing and reading status"""
        status_data = {
            "running": True,
            "current_mode": "work",
            "start_time": "2025-11-28T10:00:00Z",
        }

        storage.write_status(status_data)
        read_status = storage.read_status()
        assert read_status == status_data

    def test_write_status_atomic(self, storage):
        """Test that write_status is atomic (uses temporary file)"""
        status_data = {"test": "data"}
        storage.write_status(status_data)

        # Check that temp file doesn't exist after write
        temp_file = storage.status_file + ".tmp"
        assert not os.path.exists(temp_file)
        assert storage.read_status() == status_data

    def test_read_status_file_not_exists(self, tmp_path):
        """Test reading status when file doesn't exist"""
        logs_dir = tmp_path / "nonexistent"
        storage = Storage(str(logs_dir))
        # Remove the status file that gets created during init
        os.remove(storage.status_file)

        status = storage.read_status()
        assert status == {}

    def test_read_status_invalid_json(self, storage):
        """Test reading status with invalid JSON"""
        with open(storage.status_file, "w") as f:
            f.write("invalid json")

        status = storage.read_status()
        assert status == {}

    def test_concurrent_access(self, storage):
        """Test concurrent access to storage (thread safety)"""

        def append_sessions(storage, start_num, count):
            for i in range(start_num, start_num + count):
                storage.append_session({"event": f"event_{i}", "thread": start_num})

        # Create multiple threads writing concurrently
        threads = []
        for i in range(5):
            thread = Thread(target=append_sessions, args=(storage, i * 10, 10))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all sessions were written
        sessions = storage.read_sessions()
        assert len(sessions) == 50

        # Verify data integrity (all events are present)
        events = [s["event"] for s in sessions]
        expected_events = [f"event_{i}" for i in range(50)]
        assert sorted(events) == sorted(expected_events)


# ==================== Flask App Tests ====================


class TestFlaskApp:
    """Test Flask application endpoints and functionality"""

    def test_index_route(self, client):
        """Test the index route returns HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert b"html" in response.data.lower()

    def test_post_session_valid_data(self, client):
        """Test posting valid session data"""
        session_data = {
            "event": "start",
            "meta": {"mode": "work", "duration": 1500, "cycle": 1},
        }

        response = client.post("/api/session", json=session_data)
        assert response.status_code == 201
        data = response.get_json()
        assert data["ok"] is True

    def test_post_session_with_status_update(self, client):
        """Test posting session with status update"""
        session_data = {
            "event": "start",
            "set_status": {
                "running": True,
                "mode": "work",
                "start_time": "2025-11-28T10:00:00Z",
            },
        }

        response = client.post("/api/session", json=session_data)
        assert response.status_code == 201

        # Verify status was set
        status_response = client.get("/api/status")
        status_data = status_response.get_json()
        assert status_data["running"] is True
        assert status_data["mode"] == "work"

    def test_post_session_invalid_event_type(self, client):
        """Test posting session with invalid event type"""
        response = client.post("/api/session", json={"event": 123})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_post_session_missing_event(self, client):
        """Test posting session without event"""
        response = client.post("/api/session", json={"meta": {"test": "data"}})
        assert response.status_code == 400

    def test_post_session_empty_event(self, client):
        """Test posting session with empty event"""
        response = client.post("/api/session", json={"event": ""})
        assert response.status_code == 400

    def test_post_session_no_json_body(self, client):
        """Test posting session without JSON body"""
        response = client.post("/api/session")
        assert response.status_code in [400, 415]  # 415 for unsupported media type

    def test_get_sessions_empty(self, client):
        """Test getting sessions when none exist"""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_get_status_empty(self, client):
        """Test getting status when none set"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data == {}

    def test_session_timestamp_format(self, client):
        """Test that session timestamps are in correct ISO format"""
        response = client.post("/api/session", json={"event": "test"})
        assert response.status_code == 201

        sessions_response = client.get("/api/sessions")
        sessions = sessions_response.get_json()

        timestamp = sessions[0]["timestamp"]
        # Verify it's ISO format ending with Z
        assert timestamp.endswith("Z")
        # Verify it can be parsed as datetime
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_session_meta_data_preservation(self, client):
        """Test that meta data is preserved correctly"""
        meta_data = {
            "mode": "break",
            "duration": 300,
            "cycle": 2,
            "settings": {"work_duration": 1500, "break_duration": 300},
        }

        response = client.post(
            "/api/session", json={"event": "complete", "meta": meta_data}
        )
        assert response.status_code == 201

        sessions_response = client.get("/api/sessions")
        sessions = sessions_response.get_json()

        assert sessions[0]["meta"] == meta_data

    def test_clear_status_with_set_status_empty(self, client):
        """Test clearing status by setting empty object"""
        # First set a status
        client.post(
            "/api/session", json={"event": "start", "set_status": {"running": True}}
        )

        # Then clear it
        response = client.post("/api/session", json={"event": "stop", "set_status": {}})
        assert response.status_code == 201

        status_response = client.get("/api/status")
        status_data = status_response.get_json()
        assert status_data == {}

    def test_app_has_storage_attribute(self, app_instance):
        """Test that the app has storage attribute for testing"""
        assert hasattr(app_instance, "storage")
        assert isinstance(app_instance.storage, Storage)


# ==================== Integration Tests ====================


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_complete_pomodoro_workflow(self, client):
        """Test a complete Pomodoro session workflow"""
        # Start work session
        response = client.post(
            "/api/session",
            json={
                "event": "start",
                "meta": {"mode": "work", "duration": 1500, "cycle": 1},
                "set_status": {"running": True, "mode": "work"},
            },
        )
        assert response.status_code == 201

        # Pause session
        response = client.post(
            "/api/session",
            json={
                "event": "pause",
                "meta": {"mode": "work"},
                "set_status": {"running": False, "paused": True},
            },
        )
        assert response.status_code == 201

        # Resume session
        response = client.post(
            "/api/session",
            json={
                "event": "resume",
                "meta": {"mode": "work"},
                "set_status": {"running": True, "paused": False},
            },
        )
        assert response.status_code == 201

        # Complete session
        response = client.post(
            "/api/session",
            json={
                "event": "complete",
                "meta": {"mode": "work", "completed": True},
                "set_status": {},
            },
        )
        assert response.status_code == 201

        # Verify session history
        sessions_response = client.get("/api/sessions")
        sessions = sessions_response.get_json()
        assert len(sessions) == 4
        events = [s["event"] for s in sessions]
        assert events == ["start", "pause", "resume", "complete"]

        # Verify status is cleared
        status_response = client.get("/api/status")
        status = status_response.get_json()
        assert status == {}

    def test_multiple_cycles_workflow(self, client):
        """Test multiple Pomodoro cycles"""
        cycles = [
            ("work", 1),
            ("break", 1),
            ("work", 2),
            ("break", 2),
            ("work", 3),
            ("long_break", 3),
        ]

        for mode, cycle in cycles:
            # Start
            client.post(
                "/api/session",
                json={"event": "start", "meta": {"mode": mode, "cycle": cycle}},
            )

            # Complete
            client.post(
                "/api/session",
                json={"event": "complete", "meta": {"mode": mode, "cycle": cycle}},
            )

        # Verify all sessions recorded
        sessions_response = client.get("/api/sessions")
        sessions = sessions_response.get_json()
        assert len(sessions) == 12  # 6 starts + 6 completes

        # Verify cycle progression
        start_sessions = [s for s in sessions if s["event"] == "start"]
        modes = [s["meta"]["mode"] for s in start_sessions]
        assert modes == ["work", "break", "work", "break", "work", "long_break"]
