// Timer state and settings
let timerState = {
  running: false,
  currentType: 'work', // 'work', 'shortBreak', 'longBreak'
  currentCycle: 1,
  remaining: 0,
  intervalId: null
};

let settings = {
  workDuration: 25,
  shortBreak: 5,
  longBreak: 15,
  cyclesUntilLong: 4
};

// Load settings from localStorage
function loadSettings() {
  const saved = localStorage.getItem('pomodoroSettings');
  if (saved) {
    try {
      settings = {...settings, ...JSON.parse(saved)};
    } catch (e) {
      console.warn('Failed to load settings:', e);
    }
  }
  updateSettingsUI();
}

// Save settings to localStorage
function saveSettings() {
  localStorage.setItem('pomodoroSettings', JSON.stringify(settings));
  updateSettingsUI();
  resetTimer();
  showStatusMessage('Settings saved!');
}

// Update settings UI inputs
function updateSettingsUI() {
  document.getElementById('work-duration').value = settings.workDuration;
  document.getElementById('short-break').value = settings.shortBreak;
  document.getElementById('long-break').value = settings.longBreak;
  document.getElementById('cycles-until-long').value = settings.cyclesUntilLong;
}

// Get current session duration in seconds
function getCurrentDuration() {
  switch (timerState.currentType) {
    case 'work':
      return settings.workDuration * 60;
    case 'shortBreak':
      return settings.shortBreak * 60;
    case 'longBreak':
      return settings.longBreak * 60;
    default:
      return settings.workDuration * 60;
  }
}

// Format time display
function formatTime(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0');
  const s = (sec % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

// Update all UI elements
function updateUI() {
  document.getElementById('time').textContent = formatTime(timerState.remaining);
  
  // Update session info
  const typeDisplay = timerState.currentType === 'work' ? 'Work Session' : 
                     timerState.currentType === 'shortBreak' ? 'Short Break' : 'Long Break';
  document.getElementById('cycle-type').textContent = typeDisplay;
  document.getElementById('cycle-count').textContent = `${timerState.currentCycle}/${settings.cyclesUntilLong}`;
  
  // Update button states
  const startBtn = document.getElementById('start');
  const pauseBtn = document.getElementById('pause');
  
  if (timerState.running) {
    startBtn.disabled = true;
    pauseBtn.disabled = false;
  } else {
    startBtn.disabled = false;
    pauseBtn.disabled = true;
  }
}

// API call wrapper
async function apiCall(endpoint, data = null) {
  try {
    const options = {
      method: data ? 'POST' : 'GET',
      headers: data ? {'Content-Type': 'application/json'} : {}
    };
    if (data) options.body = JSON.stringify(data);
    
    const response = await fetch(endpoint, options);
    return await response.json();
  } catch (e) {
    console.error(`API call failed to ${endpoint}:`, e);
    return null;
  }
}

// Start timer
function startTimer() {
  if (timerState.running) return;
  
  timerState.running = true;
  timerState.intervalId = setInterval(() => {
    timerState.remaining -= 1;
    updateUI();
    
    if (timerState.remaining <= 0) {
      completeSession();
    }
  }, 1000);
  
  const meta = {
    type: timerState.currentType,
    cycle: timerState.currentCycle,
    duration: getCurrentDuration() - timerState.remaining
  };
  
  apiCall('/api/session', {
    event: 'started',
    meta: meta,
    set_status: { running: true, type: timerState.currentType, cycle: timerState.currentCycle }
  });
  
  showStatusMessage(`${timerState.currentType === 'work' ? 'Work' : 'Break'} session started!`);
  updateUI();
}

// Pause timer
function pauseTimer() {
  if (!timerState.running) return;
  
  clearInterval(timerState.intervalId);
  timerState.running = false;
  
  apiCall('/api/session', {
    event: 'paused',
    meta: { remaining: timerState.remaining, type: timerState.currentType }
  });
  
  showStatusMessage('Timer paused');
  updateUI();
}

// Reset timer
function resetTimer() {
  clearInterval(timerState.intervalId);
  timerState.running = false;
  timerState.currentType = 'work';
  timerState.currentCycle = 1;
  timerState.remaining = getCurrentDuration();
  
  apiCall('/api/session', {
    event: 'reset',
    set_status: { running: false, type: 'work', cycle: 1 }
  });
  
  showStatusMessage('Timer reset');
  updateUI();
}

// Skip current session
function skipTimer() {
  clearInterval(timerState.intervalId);
  timerState.running = false;
  
  apiCall('/api/session', {
    event: 'skipped',
    meta: { type: timerState.currentType, cycle: timerState.currentCycle }
  });
  
  nextSession();
  showStatusMessage('Session skipped');
}

// Complete current session and move to next
function completeSession() {
  clearInterval(timerState.intervalId);
  timerState.running = false;
  
  const completedType = timerState.currentType;
  const completedCycle = timerState.currentCycle;
  
  apiCall('/api/session', {
    event: 'completed',
    meta: { type: completedType, cycle: completedCycle, duration: getCurrentDuration() }
  });
  
  nextSession();
  showStatusMessage(`${completedType === 'work' ? 'Work session' : 'Break'} completed!`);
}

// Move to next session (work -> break -> work, etc.)
function nextSession() {
  if (timerState.currentType === 'work') {
    // Work completed, start break
    if (timerState.currentCycle >= settings.cyclesUntilLong) {
      timerState.currentType = 'longBreak';
      timerState.currentCycle = 1;
    } else {
      timerState.currentType = 'shortBreak';
    }
  } else {
    // Break completed, start work
    timerState.currentType = 'work';
    if (timerState.currentType === 'work' && timerState.currentCycle < settings.cyclesUntilLong) {
      timerState.currentCycle++;
    }
  }
  
  timerState.remaining = getCurrentDuration();
  updateUI();
}

// Show status message
function showStatusMessage(msg) {
  const statusEl = document.getElementById('status');
  statusEl.textContent = msg;
  setTimeout(() => {
    loadCurrentStatus();
  }, 3000);
}

// Load and display current status from API
async function loadCurrentStatus() {
  const status = await apiCall('/api/status');
  if (status) {
    const statusEl = document.getElementById('status');
    if (Object.keys(status).length === 0) {
      statusEl.textContent = 'Ready to start';
    } else {
      statusEl.textContent = `Status: ${status.running ? 'Running' : 'Paused'} - ${status.type || 'work'} (cycle ${status.cycle || 1})`;
    }
  }
}

// Load and display session history
async function loadHistory() {
  const sessions = await apiCall('/api/sessions');
  if (sessions && Array.isArray(sessions)) {
    const historyEl = document.getElementById('history');
    historyEl.innerHTML = '';
    
    if (sessions.length === 0) {
      historyEl.innerHTML = '<div class=\"session-entry\">No sessions yet</div>';
      return;
    }
    
    sessions.slice(-10).reverse().forEach(session => {
      const div = document.createElement('div');
      div.className = 'session-entry';
      
      const time = new Date(session.timestamp).toLocaleTimeString();
      const type = session.meta?.type || 'unknown';
      const cycle = session.meta?.cycle ? ` (cycle ${session.meta.cycle})` : '';
      
      div.textContent = `${time} - ${session.event} ${type}${cycle}`;
      historyEl.appendChild(div);
    });
  }
}

// Save settings from UI
function saveSettingsFromUI() {
  settings.workDuration = parseInt(document.getElementById('work-duration').value) || 25;
  settings.shortBreak = parseInt(document.getElementById('short-break').value) || 5;
  settings.longBreak = parseInt(document.getElementById('long-break').value) || 15;
  settings.cyclesUntilLong = parseInt(document.getElementById('cycles-until-long').value) || 4;
  
  saveSettings();
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  resetTimer();
  
  // Event listeners
  document.getElementById('start').addEventListener('click', startTimer);
  document.getElementById('pause').addEventListener('click', pauseTimer);
  document.getElementById('reset').addEventListener('click', resetTimer);
  document.getElementById('skip').addEventListener('click', skipTimer);
  document.getElementById('save-settings').addEventListener('click', saveSettingsFromUI);
  
  // Initial data load
  loadCurrentStatus();
  loadHistory();
  
  // Periodic updates
  setInterval(loadCurrentStatus, 5000);
  setInterval(loadHistory, 15000);
});
