"""
Dedicated tests for the Storage class to ensure comprehensive coverage
of file operations, concurrency, and error handling.
"""

import os
import json
import pytest
import tempfile
from unittest.mock import patch, mock_open, MagicMock
from threading import Thread, Barrier
import time
from app import Storage


class TestStorageEdgeCases:
    """Test edge cases and error conditions for Storage class"""

    def test_storage_with_permissions_error(self, tmp_path):
        """Test Storage behavior when directory cannot be created"""
        # Create a read-only parent directory
        readonly_parent = tmp_path / "readonly"
        readonly_parent.mkdir()
        readonly_parent.chmod(0o444)  # Read-only

        logs_dir = readonly_parent / "logs"

        # This should handle the permission error gracefully
        with pytest.raises((OSError, PermissionError)):
            Storage(str(logs_dir))

    def test_sessions_file_corruption_recovery(self, storage):
        """Test recovery from corrupted sessions file"""
        # Corrupt the sessions file
        with open(storage.sessions_file, "w", encoding="utf-8") as f:
            f.write('{"valid": "json"}\n')
            f.write("corrupted line without closing brace {\n")
            f.write('{"another": "valid"}\n')
            f.write("completely invalid\n")
            f.write('{"final": "valid"}\n')

        # Storage should recover and return only valid entries
        sessions = storage.read_sessions()
        assert len(sessions) == 3
        assert sessions[0]["valid"] == "json"
        assert sessions[1]["another"] == "valid"
        assert sessions[2]["final"] == "valid"

    def test_status_file_concurrent_writes(self, storage):
        """Test concurrent writes to status file don't corrupt data"""
        barrier = Barrier(3)
        results = {}

        def write_status(thread_id):
            barrier.wait()  # Synchronize start
            data = {"thread": thread_id, "timestamp": time.time()}
            storage.write_status(data)
            results[thread_id] = data

        threads = []
        for i in range(3):
            thread = Thread(target=write_status, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Final status should be from one of the threads
        final_status = storage.read_status()
        assert "thread" in final_status
        assert final_status["thread"] in [0, 1, 2]

    @patch("builtins.open", side_effect=IOError("Disk full"))
    def test_append_session_io_error(self, mock_open, storage):
        """Test append_session handles I/O errors gracefully"""
        with pytest.raises(IOError):
            storage.append_session({"event": "test"})

    def test_large_session_data(self, storage):
        """Test storage with large session data"""
        # Create a large meta object
        large_meta = {
            "description": "x" * 10000,  # 10KB string
            "data": list(range(1000)),
            "nested": {f"key_{i}": f"value_{i}" for i in range(100)},
        }

        session_data = {"event": "large_test", "meta": large_meta}

        storage.append_session(session_data)
        sessions = storage.read_sessions()

        assert len(sessions) == 1
        assert sessions[0]["meta"]["description"] == "x" * 10000
        assert len(sessions[0]["meta"]["data"]) == 1000

    def test_unicode_handling(self, storage):
        """Test storage handles Unicode characters correctly"""
        unicode_data = {
            "event": "测试事件",
            "meta": {
                "message": "こんにちは世界",
                "emoji": "🍅⏰",
                "special_chars": "àáäâèéëêìíïîòóöôùúüûñç",
            },
        }

        storage.append_session(unicode_data)
        sessions = storage.read_sessions()

        assert len(sessions) == 1
        assert sessions[0]["event"] == "测试事件"
        assert sessions[0]["meta"]["message"] == "こんにちは世界"
        assert sessions[0]["meta"]["emoji"] == "🍅⏰"

    def test_empty_meta_handling(self, storage):
        """Test storage handles empty and None meta data"""
        test_cases = [
            {"event": "empty_meta", "meta": {}},
            {"event": "none_meta", "meta": None},
            {"event": "no_meta"},  # Missing meta key
        ]

        for case in test_cases:
            storage.append_session(case)

        sessions = storage.read_sessions()
        assert len(sessions) == 3

        # Verify the data was stored correctly
        assert sessions[0]["meta"] == {}
        assert sessions[1]["meta"] is None
        assert "meta" not in sessions[2]


class TestStoragePerformance:
    """Performance-related tests for Storage class"""

    def test_many_sessions_performance(self, storage):
        """Test performance with many session entries"""
        num_sessions = 1000

        start_time = time.time()
        for i in range(num_sessions):
            storage.append_session(
                {"event": f"event_{i}", "meta": {"index": i, "batch": i // 100}}
            )
        write_time = time.time() - start_time

        start_time = time.time()
        sessions = storage.read_sessions()
        read_time = time.time() - start_time

        assert len(sessions) == num_sessions
        # Performance should be reasonable (adjust thresholds as needed)
        assert write_time < 5.0  # 5 seconds for 1000 writes
        assert read_time < 2.0  # 2 seconds to read 1000 entries

        # Verify data integrity
        assert sessions[0]["meta"]["index"] == 0
        assert sessions[-1]["meta"]["index"] == num_sessions - 1

    def test_concurrent_read_write(self, storage):
        """Test concurrent reading while writing"""
        write_count = 100
        read_results = []

        def continuous_writer():
            for i in range(write_count):
                storage.append_session({"event": f"write_{i}"})
                time.sleep(0.001)  # Small delay

        def continuous_reader():
            for _ in range(10):
                sessions = storage.read_sessions()
                read_results.append(len(sessions))
                time.sleep(0.01)  # Small delay

        # Start writer and reader concurrently
        writer_thread = Thread(target=continuous_writer)
        reader_thread = Thread(target=continuous_reader)

        writer_thread.start()
        reader_thread.start()

        writer_thread.join()
        reader_thread.join()

        # Verify final state
        final_sessions = storage.read_sessions()
        assert len(final_sessions) == write_count

        # Read results should show increasing counts (eventual consistency)
        assert len(read_results) == 10
        assert read_results[-1] <= write_count


class TestStorageFileOperations:
    """Test file system operations and edge cases"""

    def test_atomic_status_write_failure_recovery(self, storage):
        """Test recovery when atomic write fails partway"""
        initial_status = {"initial": "data"}
        storage.write_status(initial_status)

        # Mock os.replace to fail
        with patch("os.replace", side_effect=OSError("Replace failed")):
            with pytest.raises(OSError):
                storage.write_status({"should": "fail"})

        # Original status should be intact
        current_status = storage.read_status()
        assert current_status == initial_status

    def test_sessions_file_missing_during_read(self, storage):
        """Test behavior when sessions file is deleted during operation"""
        # Add some initial data
        storage.append_session({"event": "test"})

        # Delete the sessions file
        os.remove(storage.sessions_file)

        # Reading should handle the missing file gracefully
        try:
            sessions = storage.read_sessions()
            # If it succeeds, should return empty list
            assert sessions == []
        except FileNotFoundError:
            # If it raises FileNotFoundError, that's also acceptable behavior
            pass

    def test_status_file_missing_during_read(self, storage):
        """Test behavior when status file is deleted during operation"""
        # Set initial status
        storage.write_status({"test": "data"})

        # Delete the status file
        os.remove(storage.status_file)

        # Reading should return empty dict
        status = storage.read_status()
        assert status == {}

    def test_directory_permissions_after_creation(self, tmp_path):
        """Test that directory has correct permissions after creation"""
        logs_dir = tmp_path / "test_perms"
        storage = Storage(str(logs_dir))

        # Directory should exist and be readable/writable
        assert os.path.exists(storage.logs_dir)
        assert os.access(storage.logs_dir, os.R_OK | os.W_OK)

        # Files should be readable/writable
        assert os.access(storage.sessions_file, os.R_OK | os.W_OK)
        assert os.access(storage.status_file, os.R_OK | os.W_OK)


@pytest.fixture
def storage(tmp_path):
    """Fixture providing a Storage instance with temporary directory"""
    logs_dir = tmp_path / "test_logs"
    return Storage(str(logs_dir))
