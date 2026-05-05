#!/usr/bin/env python3
"""
Weather Station Dashboard (V2 - Intuitive UI)
Receives data from weather station via HTTP POST,
stores in SQLite, and serves a modern unified web dashboard.
"""

import sqlite3
import csv
import json
import os
import re
import threading
import time
import requests
from datetime import datetime, timedelta, date
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from collections import defaultdict

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "weather.db")

# ─── Database Setup ──────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                day_date TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                battery_voltage REAL,
                battery_percent REAL,
                source TEXT DEFAULT 'live'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_day_date ON readings(day_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON readings(timestamp)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        result = conn.execute("SELECT value FROM settings WHERE key='simulated_today'").fetchone()
        if not result:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('simulated_today', ?)",
                (date.today().isoformat(),)
            )
        conn.commit()

# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_reading_line(line: str, source: str = "live") -> dict | None:
    line = line.strip()
    if not line or line.startswith("#"): return None
    parts = line.split(",")
    if len(parts) < 6: return None
    try:
        dt_str = parts[0].strip()
        m = re.match(r'\w+\s+(\d{2}/\d{2}/\d{4})\s+-\s+(\d{2}:\d{2}:\d{2})', dt_str)
        if not m: return None
        date_part, time_part = m.group(1), m.group(2)
        dt = datetime.strptime(f"{date_part} {time_part}", "%d/%m/%Y %H:%M:%S")
        return {
            "timestamp": dt.isoformat(),
            "day_date": dt.strftime("%Y-%m-%d"),
            "temperature": float(parts[1]),
            "humidity": float(parts[2]),
            "pressure": float(parts[3]),
            "battery_voltage": float(parts[4]),
            "battery_percent": float(parts[5]),
            "source": source
        }
    except Exception:
        return None

def get_simulated_today() -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='simulated_today'").fetchone()
        return row["value"] if row else date.today().isoformat()

def set_simulated_today(day_str: str):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('simulated_today', ?)", (day_str,))
        conn.commit()

def stats_for_day(day_date: str) -> dict:
    with get_db() as conn:
        row = conn.execute("""
            SELECT MIN(temperature) as temp_low, MAX(temperature) as temp_high, AVG(temperature) as temp_avg,
                   MIN(humidity) as hum_low, MAX(humidity) as hum_high, AVG(humidity) as hum_avg,
                   MIN(pressure) as pres_low, MAX(pressure) as pres_high, AVG(pressure) as pres_avg,
                   COUNT(*) as count
            FROM readings WHERE day_date = ?
        """, (day_date,)).fetchone()
        return dict(row) if row and row["count"] > 0 else {}

def readings_for_day(day_date: str) -> list:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM readings WHERE day_date = ? ORDER BY timestamp ASC", (day_date,)).fetchall()
        return [dict(r) for r in rows]

def readings_for_range(start_date: str, end_date: str) -> list:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM readings WHERE day_date >= ? AND day_date <= ? ORDER BY timestamp ASC", (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]

def latest_reading() -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1").fetchone()
        return dict(row) if row else None

def days_with_data(n_days: int, today_str: str) -> list[str]:
    today = datetime.strptime(today_str, "%Y-%m-%d").date()
    return [(today - timedelta(days=i)).isoformat() for i in range(n_days - 1, -1, -1)]

# ─── MetService / Open-Meteo Integration ──────────────────────────────────────

def fetch_metservice_current(location: str = "auckland") -> dict | None:
    locations = {"auckland": (-36.8485, 174.7633)}
    lat, lon = locations.get(location.lower(), locations["auckland"])
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m&timezone=Pacific/Auckland")
        resp = requests.get(url, timeout=5)
        cur = resp.json().get("current", {})
        return {
            "temperature": cur.get("temperature_2m"),
            "humidity": cur.get("relative_humidity_2m"),
            "pressure": cur.get("surface_pressure"),
            "fetched_at": datetime.now().isoformat()
        }
    except Exception: return None

# ─── Routes: Data Ingest ──────────────────────────────────────────────────────

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_data(as_text=True).strip()
    reading = parse_reading_line(data, source="live")
    if not reading:
        try:
            reading = request.get_json()
            reading["source"] = "live"
        except Exception: return jsonify({"error": "Invalid data"}), 400

    with get_db() as conn:
        conn.execute("""
            INSERT INTO readings (timestamp, day_date, temperature, humidity, pressure, battery_voltage, battery_percent, source)
            VALUES (:timestamp, :day_date, :temperature, :humidity, :pressure, :battery_voltage, :battery_percent, :source)
        """, reading)
        conn.commit()
    return jsonify({"status": "ok", "timestamp": reading["timestamp"]}), 201

@app.route("/api/set-today", methods=["POST"])
def api_set_today():
    day_str = request.get_json().get("date", "")
    set_simulated_today(day_str)
    return jsonify({"status": "ok", "simulated_today": day_str})

# ─── Routes: API Data ─────────────────────────────────────────────────────────

@app.route("/api/dashboard")
def api_dashboard():
    """Unified endpoint returning everything needed for the single-page dashboard."""
    today = get_simulated_today()
    last3 = days_with_data(3, today)
    last7 = days_with_data(7, today)
    
    return jsonify({
        "simulated_today": today,
        "latest": latest_reading(),
        "stats_today": stats_for_day(today),
        "metservice": fetch_metservice_current("auckland"),
        "charts": {
            "today": readings_for_day(today),
            "three_days": readings_for_range(last3[0], last3[-1]),
            "week": readings_for_range(last7[0], last7[-1])
        }
    })

# ─── Frontend ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

# ─── HTML Template (V2 - Modern Intuitive UI) ──────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ACTION NEWS: Local Forecast</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #000000;
    --surface: #0000AA; /* Classic Broadcast Blue */
    --surface-hover: #0000FF;
    --border: #FFFFFF;
    --text: #FFFFFF;
    --text-dim: #FFFF00; /* Bright Yellow */
    --brand: #FF0000; /* Action News Red */
    --brand-glow: #FF0000;
    --temp-color: #FFCC00;
    --hum-color: #00FFFF;
    --pres-color: #00FF00;
    --bat-color: #FF00FF;
    --radius-lg: 0px;
    --radius-md: 0px;
    --radius-sm: 0px;
    --font-sans: 'VT323', monospace;
    --font-mono: 'VT323', monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { 
    background: var(--bg); 
    color: var(--text); 
    font-family: var(--font-sans); 
    -webkit-font-smoothing: none; 
    padding: 20px; 
    font-size: 22px;
    text-shadow: 2px 2px 0px #000000;
    letter-spacing: 1px;
  }

  .container { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }

  /* ─── Header ─── */
  header { display: flex; justify-content: space-between; align-items: center; background: var(--brand); padding: 10px 20px; border: 4px solid var(--border); }
  .brand { display: flex; align-items: center; gap: 12px; font-weight: 400; font-size: 2rem; text-transform: uppercase; }
  .brand-icon { font-size: 2rem; color: var(--text-dim); }
  .status-badge { display: flex; align-items: center; gap: 8px; background: #000000; color: var(--pres-color); padding: 6px 12px; border: 2px solid var(--border); font-size: 1.2rem; }
  .status-dot { width: 12px; height: 12px; background: var(--pres-color); }

  /* ─── Hero Section ─── */
  .hero { display: flex; flex-direction: column; gap: 20px; }
  
  .main-temp { background: var(--surface); padding: 30px; border: 4px solid var(--border); display: flex; flex-direction: row; justify-content: space-between; align-items: center; }
  @media (max-width: 600px) { .main-temp { flex-direction: column; gap: 20px; text-align: center; } }
  .temp-left { display: flex; flex-direction: column; }
  .temp-val { font-size: 8rem; color: var(--text-dim); line-height: 1; margin: 10px 0; }
  .temp-unit { font-size: 4rem; color: var(--text); vertical-align: top; }
  .temp-meta { font-size: 2rem; color: var(--text); display: flex; flex-direction: column; gap: 12px; text-transform: uppercase; background: #000000; padding: 16px; border: 2px solid var(--border); }
  .meta-item span { color: var(--temp-color); }

  .side-cards { display: flex; flex-direction: row; gap: 20px; flex-wrap: wrap; }
  .mini-card { flex: 1; min-width: 200px; background: var(--surface); border: 4px solid var(--border); padding: 16px; display: flex; flex-direction: column; }
  .mc-info { text-align: left; width: 100%; }
  .mc-label { font-size: 1.5rem; color: var(--text-dim); text-transform: uppercase; margin-bottom: 12px; border-bottom: 2px solid var(--border); padding-bottom: 4px; display: block; }
  .mc-icon { font-size: 1.5rem; background: #000000; padding: 4px 8px; border: 2px solid var(--border); color: var(--text); }
  .mc-val { font-size: 2.5rem; color: var(--text); line-height: 1; }

  .bat-bar-bg { width: 100%; height: 16px; border: 2px solid var(--border); background: #000000; margin-top: 12px; }
  .bat-bar-fg { height: 100%; }

  /* ─── Unified Chart Section ─── */
  .chart-section { background: var(--surface); border: 4px solid var(--border); padding: 24px; }
  .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px; }
  
  /* Toggle Pills */
  .controls { display: flex; gap: 12px; flex-wrap: wrap; }
  .pill-group { display: flex; gap: 4px; }
  
  /* 90s OS Bevel Buttons */
  .pill, .settings-bar button { 
    background: #CCCCCC; 
    color: #000000; 
    border: 3px solid;
    border-color: #FFFFFF #555555 #555555 #FFFFFF;
    padding: 6px 16px; 
    font-family: var(--font-sans); 
    font-size: 1.2rem; 
    text-transform: uppercase;
    cursor: pointer; 
    text-shadow: none;
  }
  .pill:active, .settings-bar button:active {
    border-color: #555555 #FFFFFF #FFFFFF #555555;
    background: #AAAAAA;
  }
  .pill.active { 
    background: #AAAAAA; 
    border-color: #555555 #FFFFFF #FFFFFF #555555;
  }

  .chart-container { position: relative; height: 350px; width: 100%; background: #000000; border: 2px solid var(--border); padding: 10px; }

  /* ─── Settings Section ─── */
  .settings-bar { background: var(--surface); border: 4px solid var(--border); padding: 16px 24px; display: flex; align-items: center; gap: 16px; font-size: 1.2rem; color: var(--text-dim); text-transform: uppercase; }
  .settings-bar input[type="date"] { background: #000000; border: 2px solid var(--border); color: var(--text-dim); padding: 6px 12px; font-family: var(--font-mono); font-size: 1.2rem; outline: none; text-shadow: 2px 2px 0px #000000; }
  .update-time { margin-left: auto; color: var(--text); }

</style>
</head>
<body>

<div class="container">
  <!-- Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">[///]</div>
      <div>LOCAL FORECAST</div>
    </div>
    <div class="status-badge" id="live-indicator">
      <div class="status-dot"></div>
      <span id="live-text">RCV DATA</span>
    </div>
  </header>

  <!-- Hero Stats -->
  <div class="hero">
    <div class="main-temp">
      <div class="temp-left">
        <div style="color:var(--text); font-size:1.5rem; text-transform: uppercase;">CURRENT TEMP</div>
        <div class="temp-val" id="curr-temp">--<span class="temp-unit">°C</span></div>
      </div>
      <div class="temp-meta">
        <div class="meta-item">HI <span id="hi-temp">--</span>°C</div>
        <div class="meta-item">LO <span id="lo-temp">--</span>°C</div>
      </div>
    </div>

    <div class="side-cards">
      <div class="mini-card">
        <div class="mc-info">
          <div class="mc-label">HUMIDITY</div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="mc-val" style="color:var(--hum-color);" id="curr-hum">--%</div>
          </div>
        </div>
      </div>
      <div class="mini-card">
        <div class="mc-info">
          <div class="mc-label">PRESSURE</div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="mc-val" style="color:var(--pres-color);" id="curr-pres">--hPa</div>
          </div>
        </div>
      </div>
      <div class="mini-card">
        <div class="mc-info">
          <div class="mc-label">BATTERY</div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="mc-val" style="color:var(--bat-color);" id="curr-bat">--%</div>
          </div>
          
        </div>
      </div>
    </div>
  </div>

  <!-- Interactive Chart Area -->
  <div class="chart-section">
    <div class="chart-header">
      <h2 style="font-size:1.8rem; font-weight:400; text-transform: uppercase;">7-DAY TREND</h2>
      <div class="controls">
        <!-- Metric Toggle -->
        <div class="pill-group" id="metric-toggles">
          <button class="pill active" data-metric="temperature">Temp</button>
          <button class="pill" data-metric="humidity">Hum</button>
          <button class="pill" data-metric="pressure">Pres</button>
        </div>
        <!-- Timeframe Toggle -->
        <div class="pill-group" id="time-toggles">
          <button class="pill active" data-time="today">Today</button>
          <button class="pill" data-time="three_days">3 Days</button>
          <button class="pill" data-time="week">Week</button>
        </div>
      </div>
    </div>
    <div class="chart-container">
      <canvas id="mainChart"></canvas>
    </div>
  </div>

  <!-- Footer / Tools -->
  <div class="settings-bar">
    <span>SIM DATE:</span>
    <input type="date" id="sim-date">
    <button onclick="updateSimDate()">EXECUTE</button>
    <div class="update-time" id="last-update">UPDATED: --</div>
  </div>
</div>

<script>
let dashboardData = {};
let mainChartInstance = null;
let currentMetric = 'temperature';
let currentTimeframe = 'today';

// Chart Colors Config
const chartStyles = {
  temperature: { label: 'TEMP (°C)', color: '#FFCC00', bg: 'transparent' },
  humidity: { label: 'HUM (%)', color: '#00FFFF', bg: 'transparent' },
  pressure: { label: 'PRES (hPa)', color: '#00FF00', bg: 'transparent' }
};

async function fetchDashboard() {
  try {
    const res = await fetch('/api/dashboard');
    dashboardData = await res.json();
    updateUI();
    renderChart();
  } catch (err) {
    console.error("Failed to load dashboard:", err);
    document.getElementById('live-text').textContent = "LINK LOST";
    document.getElementById('live-indicator').style.color = "#FF0000";
    document.querySelector('.status-dot').style.background = "#FF0000";
  }
}

function updateUI() {
  const live = dashboardData.latest;
  const stats = dashboardData.stats_today;
  
  // Update Status
  document.getElementById('live-text').textContent = live ? "SYSTEM ONLINE" : "WAITING FOR DATA";
  
  if (live) {
    document.getElementById('curr-temp').innerHTML = `${live.temperature.toFixed(1)}<span class="temp-unit">°C</span>`;
    document.getElementById('curr-hum').textContent = `${live.humidity.toFixed(1)}%`;
    document.getElementById('curr-pres').innerHTML = `${Math.round(live.pressure)} <span style="font-size:0.8rem;">hPa</span>`;
    document.getElementById('curr-bat').textContent = `${Math.round(live.battery_percent)}%`;
    document.getElementById('bat-fill').style.width = `${live.battery_percent}%`;
    
    // Set Battery color based on %
    let batCol = '#00FF00';
    if(live.battery_percent < 20) batCol = '#FF0000';
    else if (live.battery_percent < 50) batCol = '#FFFF00';
    document.getElementById('bat-fill').style.background = batCol;
    document.getElementById('curr-bat').previousElementSibling.style.color = batCol;
  }

  if (stats && stats.temp_high !== null) {
    document.getElementById('hi-temp').textContent = stats.temp_high.toFixed(1);
    document.getElementById('lo-temp').textContent = stats.temp_low.toFixed(1);
  }

  document.getElementById('sim-date').value = dashboardData.simulated_today;
  document.getElementById('last-update').textContent = `UPDATED: ${new Date().toLocaleTimeString('en-US', {hour12: false})}`;
}

function renderChart() {
  const ctx = document.getElementById('mainChart');
  if (!ctx) return;

  // Get raw data for timeframe
  let rawData = dashboardData.charts[currentTimeframe] || [];
  
  // Decimate data if it's too dense to prevent lag (max ~150 points)
  let targetPoints = 150;
  let step = Math.ceil(rawData.length / targetPoints);
  let plotData = rawData.filter((_, i) => i % step === 0);

  const labels = plotData.map(r => {
    let d = new Date(r.timestamp);
    if(currentTimeframe === 'today') return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    return d.toLocaleDateString([], {month:'short', day:'numeric'}) + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  });
  
  const dataPoints = plotData.map(r => r[currentMetric]);
  const style = chartStyles[currentMetric];

  if (mainChartInstance) {
    mainChartInstance.destroy();
  }

  mainChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: style.label,
        data: dataPoints,
        borderColor: style.color,
        backgroundColor: style.bg,
        borderWidth: 4,
        fill: false,
        tension: 0, /* 90s jagged rigid lines */
        pointRadius: 4,
        pointStyle: 'rect', /* Square points */
        pointHoverRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0000AA', borderColor: '#FFFFFF', borderWidth: 2,
          titleFont: { family: 'VT323', size: 18 }, bodyFont: { family: 'VT323', size: 18 },
          padding: 12
        }
      },
      scales: {
        x: { grid: { color: '#FFFFFF', lineWidth: 1 }, ticks: { color: '#FFFF00', font: {family: 'VT323', size: 16}, maxTicksLimit: 8 } },
        y: { grid: { color: '#FFFFFF', lineWidth: 1 }, ticks: { color: '#FFFF00', font: {family: 'VT323', size: 16} } }
      }
    }
  });
}

// Toggle Listeners
document.getElementById('metric-toggles').addEventListener('click', (e) => {
  if(e.target.tagName === 'BUTTON') {
    document.querySelectorAll('#metric-toggles button').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    currentMetric = e.target.dataset.metric;
    renderChart();
  }
});

document.getElementById('time-toggles').addEventListener('click', (e) => {
  if(e.target.tagName === 'BUTTON') {
    document.querySelectorAll('#time-toggles button').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    currentTimeframe = e.target.dataset.time;
    renderChart();
  }
});

async function updateSimDate() {
  const date = document.getElementById('sim-date').value;
  await fetch('/api/set-today', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date })
  });
  fetchDashboard();
}

// Boot up
fetchDashboard();
setInterval(fetchDashboard, 30000); // Auto-refresh every 30s

</script>
</body>
</html>
"""

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    print("=" * 60)
    print("  Weather Station Dashboard (V2)")
    print("  http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)