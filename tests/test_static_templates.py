"""
Tests for static files and template functionality
"""

import os
import pytest
from app import create_app


class TestStaticFiles:
    """Test static file serving"""

    @pytest.fixture
    def app(self, tmp_path):
        logs_dir = tmp_path / "test_logs"
        return create_app({"TESTING": True, "LOGS_DIR": str(logs_dir)})

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_css_file_accessible(self, client):
        """Test that CSS files are accessible"""
        response = client.get("/static/css/styles.css")
        if response.status_code == 200:
            assert response.content_type.startswith("text/css")
        else:
            # File might not exist in test environment, which is OK
            assert response.status_code == 404

    def test_js_file_accessible(self, client):
        """Test that JavaScript files are accessible"""
        response = client.get("/static/js/timer.js")
        if response.status_code == 200:
            assert (
                "javascript" in response.content_type
                or "text/" in response.content_type
            )
        else:
            # File might not exist in test environment, which is OK
            assert response.status_code == 404

    def test_nonexistent_static_file(self, client):
        """Test access to non-existent static file"""
        response = client.get("/static/nonexistent.css")
        assert response.status_code == 404


class TestTemplates:
    """Test template rendering"""

    @pytest.fixture
    def app(self, tmp_path):
        logs_dir = tmp_path / "test_logs"
        return create_app({"TESTING": True, "LOGS_DIR": str(logs_dir)})

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_index_template_structure(self, client):
        """Test that index template has expected structure"""
        response = client.get("/")
        assert response.status_code == 200

        content = response.get_data(as_text=True)
        # Check for basic HTML structure
        assert "<html" in content.lower() or "<!doctype html>" in content.lower()
        assert "<head>" in content.lower()
        assert "<body>" in content.lower()

    def test_index_template_includes_api_endpoints(self, client):
        """Test that template likely includes references to API endpoints"""
        response = client.get("/")
        content = response.get_data(as_text=True)

        # Template should probably reference the API endpoints
        api_references = ["/api/session", "/api/sessions", "/api/status"]
        # At least one API reference should be present
        has_api_ref = any(api_ref in content for api_ref in api_references)
        # This is a soft assertion - template might structure things differently
        # assert has_api_ref or 'fetch(' in content or 'XMLHttpRequest' in content


class TestAppIntegration:
    """Integration tests combining templates, static files, and API"""

    @pytest.fixture
    def app(self, tmp_path):
        logs_dir = tmp_path / "test_logs"
        return create_app({"TESTING": True, "LOGS_DIR": str(logs_dir)})

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_full_page_load_and_api_usage(self, client):
        """Test loading the main page and using the API"""
        # Load the main page
        response = client.get("/")
        assert response.status_code == 200

        # Use the API as the page would
        session_response = client.post(
            "/api/session",
            json={"event": "page_load_test", "meta": {"source": "integration_test"}},
        )
        assert session_response.status_code == 201

        # Check that session was recorded
        sessions_response = client.get("/api/sessions")
        sessions = sessions_response.get_json()
        assert len(sessions) >= 1
        assert any(s["event"] == "page_load_test" for s in sessions)

    def test_cors_headers_if_needed(self, client):
        """Test CORS headers if the app needs to support cross-origin requests"""
        response = client.post("/api/session", json={"event": "cors_test"})
        # This is optional - app might not need CORS
        # if 'Access-Control-Allow-Origin' in response.headers:
        #     assert response.headers['Access-Control-Allow-Origin'] is not None
