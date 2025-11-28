from flask import Flask, jsonify, request, render_template
import os
import json
from datetime import datetime, timezone
from threading import Lock

DEFAULT_LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


class Storage:
    def __init__(self, logs_dir=None):
        self.logs_dir = logs_dir or DEFAULT_LOGS_DIR
        self.sessions_file = os.path.join(self.logs_dir, "sessions.jsonl")
        self.status_file = os.path.join(self.logs_dir, "status.json")
        self._lock = Lock()
        os.makedirs(self.logs_dir, exist_ok=True)
        if not os.path.exists(self.sessions_file):
            open(self.sessions_file, "a").close()
        if not os.path.exists(self.status_file):
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def append_session(self, obj):
        line = json.dumps(obj, ensure_ascii=False)
        with self._lock:
            with open(self.sessions_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def read_sessions(self):
        with self._lock:
            out = []
            with open(self.sessions_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        continue
            return out

    def write_status(self, obj):
        tmp = self.status_file + ".tmp"
        with self._lock:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(obj, f)
            os.replace(tmp, self.status_file)

    def read_status(self):
        with self._lock:
            try:
                with open(self.status_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}


def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    if test_config:
        app.config.update(test_config)

    storage = Storage(app.config.get("LOGS_DIR"))

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/session", methods=["POST"])
    def api_session():
        data = request.get_json() or {}
        event = data.get("event")
        if not event or not isinstance(event, str):
            return jsonify({"error": "invalid event"}), 400
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": event,
            "meta": data.get("meta", {}),
        }
        storage.append_session(entry)
        if "set_status" in data:
            storage.write_status(data.get("set_status") or {})
        return jsonify({"ok": True}), 201

    @app.route("/api/sessions", methods=["GET"])
    def api_sessions():
        return jsonify(storage.read_sessions())

    @app.route("/api/status", methods=["GET"])
    def api_status():
        return jsonify(storage.read_status())

    app.storage = storage
    return app


if __name__ == "__main__":
    a = create_app()
    a.run(debug=True)
from flask import Flask, send_from_directory, jsonify, request, render_template
import os
import json
from datetime import datetime
from threading import Lock

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
SESSIONS_FILE = os.path.join(LOGS_DIR, "sessions.jsonl")
STATUS_FILE = os.path.join(LOGS_DIR, "status.json")

app = Flask(__name__, static_folder="static", template_folder="templates")
file_lock = Lock()


def ensure_logs():
    os.makedirs(LOGS_DIR, exist_ok=True)
    if not os.path.exists(SESSIONS_FILE):
        open(SESSIONS_FILE, "a").close()
    if not os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def append_session(session_obj):
    ensure_logs()
    line = json.dumps(session_obj, ensure_ascii=False)
    with file_lock:
        with open(SESSIONS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def write_status(status_obj):
    ensure_logs()
    with file_lock:
        tmp = STATUS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(status_obj, f)
        os.replace(tmp, STATUS_FILE)


def read_status():
    ensure_logs()
    with file_lock:
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/session", methods=["POST"])
def api_session():
    data = request.get_json() or {}
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": data.get("event", "unknown"),
        "meta": data.get("meta", {}),
    }
    append_session(entry)
    if data.get("set_status"):
        write_status(data.get("set_status"))
    return jsonify({"ok": True}), 201


@app.route("/api/sessions", methods=["GET"])
def api_sessions():
    ensure_logs()
    with file_lock:
        sessions = []
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sessions.append(json.loads(line))
                except Exception:
                    continue
    return jsonify(sessions)


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(read_status())


if __name__ == "__main__":
    app.run(debug=True)
