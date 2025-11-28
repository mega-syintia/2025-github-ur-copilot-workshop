# Pomodoro Timer Application Documentation

## Overview

The Pomodoro Timer is a web-based productivity application that implements the Pomodoro Technique for time management. The application follows a client-server architecture with a browser-based frontend and a Flask backend for session tracking and persistence.

## Architecture

### Frontend
- **Technology**: HTML5, CSS3, JavaScript (Vanilla)
- **Responsibility**: Timer logic, UI controls, user settings, session management
- **Components**:
  - Timer display and controls
  - Settings configuration
  - Status display
  - Session history viewer

### Backend
- **Technology**: Flask (Python)
- **Responsibility**: Session logging, data persistence, API endpoints
- **Components**:
  - Storage system for session data
  - REST API endpoints
  - Static file serving

### Data Persistence
- **Sessions Log**: `logs/sessions.jsonl` - Append-only JSONL file for all events
- **Status File**: `logs/status.json` - Current session state (atomic writes)
- **Client Settings**: Browser localStorage for user preferences

## Core Features

### Timer Functionality
- **Work Sessions**: Configurable duration (default: 25 minutes)
- **Short Breaks**: Between work sessions (default: 5 minutes)  
- **Long Breaks**: After completing a cycle (default: 15 minutes)
- **Cycle Management**: Configurable number of work sessions before long break (default: 4)

### Controls
- **Start**: Begin timer countdown
- **Pause**: Pause current session
- **Reset**: Reset timer to initial state
- **Skip**: Skip current session and move to next

### Settings
- Customizable durations for work, short break, and long break
- Configurable cycle count before long break
- Settings persist in browser localStorage

### Logging & Tracking
- All timer events logged to server
- Session history display
- Current status tracking

## User Flow Charts

### Main User Flow

```mermaid
flowchart TD
    A[User opens application] --> B[Load settings from localStorage]
    B --> C[Initialize timer display]
    C --> D[Timer shows: Ready to start]
    
    D --> E{User action}
    
    E -->|Start| F[Start work session]
    E -->|Settings| G[Configure timer settings]
    E -->|View History| H[Display session history]
    
    F --> I[Timer counts down]
    I --> J{Timer reaches 0?}
    J -->|No| K{User pauses?}
    K -->|Yes| L[Pause timer]
    K -->|No| I
    L --> M{User resumes?}
    M -->|Yes| I
    M -->|No| N[Timer remains paused]
    
    J -->|Yes| O[Session complete]
    O --> P{Work session?}
    P -->|Yes| Q{Cycle complete?}
    Q -->|Yes| R[Start long break]
    Q -->|No| S[Start short break]
    P -->|No| T[Start next work session]
    
    R --> I
    S --> I
    T --> I
    
    G --> U[Save settings to localStorage]
    U --> V[Reset timer with new settings]
    V --> D
    
    H --> D
    N --> D
```

### Settings Flow

```mermaid
flowchart TD
    A[User clicks Settings] --> B[Display settings panel]
    B --> C[Show current values]
    C --> D{User modifies values?}
    D -->|Yes| E[Update input fields]
    D -->|No| F[Settings unchanged]
    E --> G[User clicks Save]
    G --> H[Validate input values]
    H --> I{Values valid?}
    I -->|Yes| J[Save to localStorage]
    I -->|No| K[Show error message]
    J --> L[Reset timer with new settings]
    L --> M[Show success message]
    K --> C
    F --> N[Close settings panel]
    M --> N
```

## Sequence Diagrams

### Timer Start Sequence

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Frontend (JS)
    participant Backend as Flask Backend
    participant Storage as File Storage
    
    User->>Frontend: Click Start
    Frontend->>Frontend: Set timer state to running
    Frontend->>Frontend: Start countdown interval
    Frontend->>Backend: POST /api/session (event: started)
    Backend->>Storage: Append to sessions.jsonl
    Backend->>Storage: Update status.json
    Backend->>Frontend: Response: {ok: true}
    Frontend->>Frontend: Update UI (disable start, enable pause)
    Frontend->>User: Show "Work session started!" message
    
    loop Every second
        Frontend->>Frontend: Decrement remaining time
        Frontend->>Frontend: Update display
    end
    
    Frontend->>Frontend: Timer reaches 0
    Frontend->>Backend: POST /api/session (event: completed)
    Backend->>Storage: Append to sessions.jsonl
    Backend->>Storage: Clear status.json
    Backend->>Frontend: Response: {ok: true}
    Frontend->>Frontend: Switch to break mode
    Frontend->>User: Show "Session completed!" message
```

### Settings Update Sequence

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Frontend (JS)
    participant LocalStorage as Browser Storage
    
    User->>Frontend: Modify settings inputs
    User->>Frontend: Click Save Settings
    Frontend->>Frontend: Validate input values
    Frontend->>LocalStorage: Store settings JSON
    Frontend->>Frontend: Update settings object
    Frontend->>Frontend: Reset timer with new durations
    Frontend->>Frontend: Update UI elements
    Frontend->>User: Show "Settings saved!" message
```

### Session History Loading Sequence

```mermaid
sequenceDiagram
    participant Frontend as Frontend (JS)
    participant Backend as Flask Backend
    participant Storage as File Storage
    
    Note over Frontend: Page load or periodic refresh
    
    Frontend->>Backend: GET /api/sessions
    Backend->>Storage: Read sessions.jsonl
    Backend->>Backend: Parse JSONL lines
    Backend->>Backend: Return last 10 sessions
    Backend->>Frontend: Response: [session objects]
    Frontend->>Frontend: Update history display
    Frontend->>Frontend: Format timestamps and events
    
    Frontend->>Backend: GET /api/status
    Backend->>Storage: Read status.json
    Backend->>Frontend: Response: current status
    Frontend->>Frontend: Update status display
```

### Pause/Resume Sequence

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Frontend (JS)
    participant Backend as Flask Backend
    participant Storage as File Storage
    
    Note over Frontend: Timer is running
    
    User->>Frontend: Click Pause
    Frontend->>Frontend: Clear countdown interval
    Frontend->>Frontend: Set running state to false
    Frontend->>Backend: POST /api/session (event: paused)
    Backend->>Storage: Append to sessions.jsonl
    Backend->>Frontend: Response: {ok: true}
    Frontend->>Frontend: Update UI (enable start, disable pause)
    Frontend->>User: Show "Timer paused" message
    
    Note over Frontend: Timer is paused
    
    User->>Frontend: Click Start (Resume)
    Frontend->>Frontend: Set running state to true
    Frontend->>Frontend: Start countdown interval
    Frontend->>Backend: POST /api/session (event: started)
    Backend->>Storage: Append to sessions.jsonl
    Backend->>Storage: Update status.json
    Backend->>Frontend: Response: {ok: true}
    Frontend->>Frontend: Update UI (disable start, enable pause)
```

## API Documentation

### Endpoints

#### `GET /`
- **Description**: Serves the main application page
- **Response**: HTML page with timer interface

#### `POST /api/session`
- **Description**: Log a timer event
- **Request Body**:
  ```json
  {
    "event": "started|paused|completed|skipped|reset",
    "meta": {
      "type": "work|shortBreak|longBreak",
      "cycle": 1,
      "duration": 1500,
      "remaining": 900
    },
    "set_status": {
      "running": true,
      "type": "work",
      "cycle": 1
    }
  }
  ```
- **Response**: `{"ok": true}` (201 status)
- **Actions**: 
  - Appends event to sessions.jsonl
  - Updates status.json if `set_status` provided

#### `GET /api/sessions`
- **Description**: Retrieve session history
- **Response**: Array of session objects
- **Example**:
  ```json
  [
    {
      "timestamp": "2025-11-28T12:34:56Z",
      "event": "started",
      "meta": {
        "type": "work",
        "cycle": 1,
        "duration": 0
      }
    }
  ]
  ```

#### `GET /api/status`
- **Description**: Get current timer status
- **Response**: Current status object or empty object
- **Example**:
  ```json
  {
    "running": true,
    "type": "work",
    "cycle": 1
  }
  ```

## Data Models

### Session Event Structure
```json
{
  "timestamp": "2025-11-28T12:34:56Z",
  "event": "started|paused|completed|skipped|reset",
  "meta": {
    "type": "work|shortBreak|longBreak",
    "cycle": 1,
    "duration": 1500,
    "remaining": 900
  }
}
```

### Status Structure
```json
{
  "running": true,
  "type": "work|shortBreak|longBreak", 
  "cycle": 1
}
```

### Settings Structure (localStorage)
```json
{
  "workDuration": 25,
  "shortBreak": 5,
  "longBreak": 15,
  "cyclesUntilLong": 4
}
```

## File Structure

```
├── app.py                 # Flask application and API endpoints
├── requirements.txt       # Python dependencies
├── logs/
│   ├── sessions.jsonl    # Append-only session events log
│   └── status.json       # Current session status
├── static/
│   ├── css/
│   │   └── styles.css    # Application styling
│   └── js/
│       └── timer.js      # Frontend timer logic
├── templates/
│   └── index.html        # Main application template
└── tests/
    └── test_app.py       # Unit tests
```

## State Management

### Frontend Timer State
- `running`: Boolean indicating if timer is active
- `currentType`: Current session type (work/shortBreak/longBreak)
- `currentCycle`: Current cycle number within the set
- `remaining`: Remaining seconds in current session
- `intervalId`: JavaScript interval ID for countdown

### Backend Storage
- **Thread-safe**: Uses file locking for concurrent access
- **Atomic writes**: Status updates use temporary file + rename
- **Append-only logs**: Sessions logged to JSONL for durability

## Error Handling

### Frontend
- API call failures logged to console
- Graceful degradation when backend unavailable
- Input validation for settings
- localStorage fallback handling

### Backend
- JSON parsing error handling
- File I/O error recovery
- Invalid request validation
- Thread-safe file operations

## Browser Compatibility

- Modern browsers supporting ES6+
- localStorage API required
- Fetch API for HTTP requests
- No external JavaScript dependencies

## Development Notes

### Testing
- Unit tests for Flask API endpoints
- Test coverage for storage operations
- Mock localStorage for testing

### Deployment Considerations
- Ensure logs directory is writable
- Consider log rotation for long-term usage
- Static file serving can be handled by web server
- Thread-safe storage implementation handles concurrent users

### Future Enhancements
- User authentication and multi-user support
- Statistics and analytics dashboard
- Audio notifications
- Mobile app version
- Data export functionality