# Pomodoro Timer — Architecture

This document captures the conclusion from the design discussion for the Pomodoro web app. It describes the recommended architecture, API, logging format, file layout, concurrency considerations, and next steps.

## Overview
- Frontend: Single-page app (HTML/CSS/JavaScript). All timer logic and UI run in the browser (work/short/long modes, cycle counting, animations).
- Backend: Thin Flask app that serves HTML and static assets and records session events to append-only logs. Exposes a few small REST endpoints for logging and querying events.
- Persistence: Server-side append-only JSONL log file for events and an optional atomic status file to reflect the currently running session.

## Goals / Responsibilities
- Frontend
  - Implement the timer state machine, UI controls (Start, Pause, Reset, Skip, Settings).
  - Persist UI settings to localStorage.
  - Send events to the backend for important lifecycle changes: start, heartbeat, complete, skip, reset, interrupt.
  - Optionally request /api/status at load to recover or show server-side state.
- Backend (Flask)
  - Serve the index page and static files.
  - Provide REST endpoints for recording events and retrieving history/status.
  - Persist events to logs/sessions.jsonl and maintain logs/status.json for the active session (atomic writes).
  - Protect endpoints by validating inputs; consider authentication if multi-user.

## API (suggested)
- POST /api/session
  - Body JSON: { session_id?, event, mode, timestamp?, settings?, payload? }
  - event ∈ { "start", "heartbeat", "complete", "skip", "reset", "interrupt" }
  - Response: { ok: true, session_id }
  - Server actions:
    - Append event to JSONL log.
    - If event == "start": write status.json with current session summary.
    - If event == "heartbeat": update last_heartbeat in status.json.
    - If event in {"complete","skip","interrupt","reset"}: remove/clear status.json.
- GET /api/sessions?limit=100
  - Returns recent event lines from sessions.jsonl in reverse chronological order.
  - Response: { events: [...] }
- GET /api/status
  - Returns current running session or idle
  - Response: { status: "running"|"idle", session: { session_id, mode, started_at, last_heartbeat, settings } | null }

## Log format
- sessions.jsonl: newline-delimited JSON objects (append-only). Each line example:
  {
    "session_id": "uuid",
    "event":"start",
    "mode":"work",
    "timestamp":"2025-11-28T12:34:56Z",
    "settings": { "work":1500, "short":300, "long":1200, "cycles":4 },
    "payload": { … },
    "logged_at": "2025-11-28T12:34:56Z"
  }
- status.json: single JSON object summarizing the active session:
  {
    "session_id": "uuid",
    "mode": "work",
    "started_at": "2025-11-28T12:34:56Z",
    "last_heartbeat": "2025-11-28T12:35:10Z",
    "settings": { ... }
  }
- Use atomic writes for status.json (write to a tmp file then os.replace).

## File layout (recommended)
- app.py — Flask server and API endpoints
- templates/index.html — SPA HTML
- static/css/styles.css — styles
- static/js/timer.js — frontend timer, state machine, and API calls
- logs/sessions.jsonl — append-only event log
- logs/status.json — current active session (optional)
- docs/ARCHITECTURE.md (this file) — architecture notes and API spec

## Concurrency & robustness
- For single-process development (Flask dev server), an in-process threading.Lock around file writes is sufficient.
- For multi-process deployments (gunicorn with multiple workers), either:
  - Use file locks (e.g., portalocker) when writing logs/status, or
  - Migrate to SQLite/Postgres for stronger concurrency and queryability.
- Append-only JSONL simplifies auditing and replay; use rotation/archival strategy when logs grow large.

## Security & validation
- Validate incoming JSON fields and accepted event types.
- If exposed to public or multi-user usage:
  - Add authentication/authorization.
  - Use per-user logs or a database to isolate data.
  - Rate-limit event endpoints (beat heartbeats) if needed.

## UX considerations (frontend)
- Timer runs in the browser to remain responsive and work offline once loaded.
- Send "start" when user starts a session, and optionally heartbeats (e.g., every 30s) to show "ongoing" on the server.
- Decide whether next mode auto-starts after a session completes or waits for user action (both are valid UX choices).
- Implement browser Notifications + sound as optional alerts when a session ends.

## Next steps / improvements
- Build the UI to match the mock: rounded card, circular progress ring, session counter, settings modal.
- Add session history view that reads /api/sessions and displays entries.
- Add unit tests for frontend timer state machine and backend integration tests for the API.
- Add file locking or move to an SQLite-backed events table for production multi-worker safety.
- Add accessibility (ARIA, keyboard controls) and responsive behavior.
- Consider per-user persistence and authentication if the app grows.

## Example event lifecycle
1. User presses "Start":
   - Frontend sets session_id (uuid), starts local timer, sends POST /api/session { event:"start", session_id, mode, settings }.
   - Backend appends start event and writes status.json.
2. Frontend sends periodic POST /api/session { event:"heartbeat" } while running.
   - Backend updates last_heartbeat in status.json.
3. Timer expires or user skips:
   - Frontend sends POST /api/session { event:"complete"|"skip" }.
   - Backend appends event and clears status.json.
4. User inspects history: frontend GET /api/sessions and displays recent entries.

---

This architecture is purposely simple to match the learning goals: keep timer logic on the frontend, use Flask as a thin server for assets and simple persistence, and store events in human-readable JSONL. Move to a real database and add authentication once you outgrow the file-logs approach.