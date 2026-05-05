#!/usr/bin/env python3
"""
Weather Station Dashboard (V3 - Commercial LCD Theme)
Receives data from weather station via HTTP POST,
stores in SQLite, and serves a beige/black LCD style web dashboard.
"""

import sqlite3
import re
import os
import requests
from datetime import datetime, timedelta, date
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "weather.db")

_cached_metservice = None
_last_reading_ts = None

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

# ─── Routes ──────────────────────────────────────────────────────────────────

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

@app.route("/api/dashboard")
def api_dashboard():
    global _cached_metservice, _last_reading_ts
    today = get_simulated_today()
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    last3 = days_with_data(3, today)
    last7 = days_with_data(7, today)
    
    latest = latest_reading()
    latest_ts = latest["timestamp"] if latest else None
    is_init = request.args.get("init") == "true"

    if is_init or _cached_metservice is None or latest_ts != _last_reading_ts:
        _cached_metservice = fetch_metservice_current("auckland")
        _last_reading_ts = latest_ts
        
    return jsonify({
        "simulated_today": today,
        "latest": latest,
        "stats_today": stats_for_day(today),
        "stats_yesterday": [{"date": yesterday, "stats": stats_for_day(yesterday)}],
        "stats_3days": [{"date": d, "stats": stats_for_day(d)} for d in last3],
        "stats_week": [{"date": d, "stats": stats_for_day(d)} for d in last7],
        "metservice": _cached_metservice,
        "charts": {
            "today": readings_for_day(today),
            "three_days": readings_for_range(last3[0], last3[-1]),
            "week": readings_for_range(last7[0], last7[-1])
        }
    })

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

# ─── HTML Template (V3 - Commercial LCD) ───────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WS-2000 Control Panel</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
  :root {
    --bezel: #e4e2d7;
    --lcd-bg: #9eb084;
    --lcd-text: #171b12;
    --lcd-text-dim: #38422a;
    --font-lcd: 'Share Tech Mono', monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  body { 
    background: #1e1e1e; /* Dark desk/wall behind the unit */
    font-family: var(--font-lcd); 
    padding: 40px 20px;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
  }

  .device-bezel {
    background: var(--bezel);
    padding: 30px 40px 40px 40px;
    border-radius: 8px;
    box-shadow: 
      0 20px 50px rgba(0,0,0,0.8), 
      inset 0 4px 10px rgba(255,255,255,0.8), 
      inset 0 -4px 10px rgba(0,0,0,0.15);
    width: 100%;
    max-width: 1000px;
  }

  .device-logo {
    font-family: Arial, sans-serif;
    color: #8a887e;
    font-size: 1.2rem;
    font-style: italic;
    font-weight: 900;
    text-align: left;
    margin-bottom: 20px;
    letter-spacing: 2px;
  }

  .lcd-screen {
    background: var(--lcd-bg);
    border: 10px solid #5a5a5a;
    border-bottom-color: #dcdcdc;
    border-right-color: #dcdcdc;
    border-top-color: #4a4a4a;
    border-left-color: #4a4a4a;
    padding: 20px;
    color: var(--lcd-text);
    box-shadow: inset 0 0 20px rgba(0,0,0,0.15);
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* ─── Header ─── */
  header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid var(--lcd-text); padding-bottom: 12px; flex-wrap: wrap; gap: 10px; }
  .brand { font-size: 2rem; font-weight: bold; letter-spacing: 2px; display: flex; align-items: center; }
  .status-badge { display: flex; align-items: center; gap: 12px; font-size: 1.5rem; }
  
  @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
  .status-dot { width: 16px; height: 16px; background: var(--lcd-text); border-radius: 2px; }
  .status-dot.active { animation: blink 1s infinite steps(2, start); }

  /* ─── Main Readouts ─── */
  .hero { display: flex; gap: 16px; border-bottom: 3px solid var(--lcd-text); padding-bottom: 16px; }
  @media (max-width: 600px) { .hero { flex-direction: column; } }
  
  .lcd-segment { color: var(--lcd-text); opacity: 0.12; line-height: 1.2; pointer-events: none; user-select: none; font-weight: bold; transition: opacity 0.3s; }
  .lcd-segment.active { opacity: 1; }

  .main-temp { flex: 2; border: 3px solid var(--lcd-text); padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .temp-label { font-size: 1.5rem; letter-spacing: 1px; width: 100%; text-align: left; border-bottom: 2px dashed var(--lcd-text-dim); margin-bottom: 10px; padding-bottom: 5px; display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; }
  .temp-val { font-size: 8rem; line-height: 1; }
  .temp-unit { font-size: 4rem; vertical-align: super; }
  .temp-meta { display: flex; gap: 30px; font-size: 1.5rem; margin-top: 10px; width: 100%; justify-content: space-between; border-top: 2px dashed var(--lcd-text-dim); padding-top: 10px;}

  .side-cards { flex: 1; display: flex; flex-direction: column; gap: 16px; }
  .mini-card { border: 3px solid var(--lcd-text); padding: 12px; flex: 1; display: flex; flex-direction: column; justify-content: center; }
  .mc-label { font-size: 1.2rem; border-bottom: 2px solid var(--lcd-text); padding-bottom: 4px; margin-bottom: 8px; }
  .mc-val { font-size: 2.5rem; text-align: right; }

  .bat-bar-bg { width: 100%; height: 16px; border: 2px solid var(--lcd-text); padding: 2px; margin-top: 8px; }
  .bat-bar-fg { height: 100%; background: var(--lcd-text); }

  /* ─── Summary Section ─── */
  .summary-section { padding-top: 16px; border-bottom: 3px solid var(--lcd-text); padding-bottom: 16px; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 10px; }
  .summary-card { border: 3px solid var(--lcd-text); padding: 12px; }
  .sc-label { font-size: 1.2rem; border-bottom: 2px solid var(--lcd-text); padding-bottom: 4px; margin-bottom: 8px; }
  .sc-values { display: flex; justify-content: space-between; text-align: center; }
  .sc-col { flex: 1; display: flex; flex-direction: column; border-right: 2px dashed var(--lcd-text-dim); }
  .sc-col:last-child { border-right: none; }
  .sc-col-title { font-size: 1rem; color: var(--lcd-text-dim); margin-bottom: 4px; }
  .sc-val { font-size: 1.5rem; }

  /* ─── Chart Section ─── */
  .chart-section { padding-top: 10px; }
  .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;}
  
  .controls { display: flex; gap: 16px; flex-wrap: wrap;}
  .pill-group { display: flex; gap: 4px; }
  .pill { 
    background: transparent; 
    color: var(--lcd-text-dim); 
    border: 2px solid var(--lcd-text-dim); 
    padding: 4px 12px; 
    font-family: var(--font-lcd); 
    font-size: 1.2rem; 
    cursor: pointer; 
  }
  .pill:hover { border-color: var(--lcd-text); color: var(--lcd-text); }
  .pill.active { background: var(--lcd-text); color: var(--lcd-bg); border-color: var(--lcd-text); }

  .chart-container { position: relative; height: 300px; width: 100%; border: 3px solid var(--lcd-text); padding: 10px; overflow: hidden; }

  .radar-sweep {
    position: absolute;
    top: 0; bottom: 0; left: 0; width: 4px;
    background: rgba(23, 27, 18, 0.4);
    box-shadow: -15px 0 20px 2px rgba(23, 27, 18, 0.3);
    animation: sweep 3s linear infinite;
    pointer-events: none;
    z-index: 10;
  }
  @keyframes sweep {
    0% { left: -20px; opacity: 0; }
    5% { opacity: 1; }
    95% { opacity: 1; }
    100% { left: 100%; opacity: 0; }
  }

  /* ─── Footer ─── */
  .settings-bar { border-top: 3px dashed var(--lcd-text-dim); padding-top: 16px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 1.2rem; flex-wrap: wrap; gap: 12px;}
  .settings-bar input[type="date"] { background: transparent; border: 2px solid var(--lcd-text); color: var(--lcd-text); font-family: var(--font-lcd); font-size: 1.2rem; padding: 4px 8px; outline: none; }
  .settings-bar button { background: var(--lcd-text); color: var(--lcd-bg); border: 2px solid var(--lcd-text); font-family: var(--font-lcd); font-size: 1.2rem; padding: 4px 16px; cursor: pointer; }
  .settings-bar button:active { background: transparent; color: var(--lcd-text); }

</style>
</head>
<body>

<div class="device-bezel">
  <div class="device-logo">WEATHER STATION</div>
  <div class="lcd-screen">
    
    <!-- Header -->
    <header>
      <div class="brand">WEATHER MONITOR <span id="live-clock" style="font-size: 1.2rem; margin-left: 20px; color: var(--lcd-text-dim);">--:--:--</span></div>
      <div class="status-badge">
        <span id="live-text">RX: WAIT</span>
        <div class="status-dot"></div>
      </div>
    </header>

    <!-- Hero Stats -->
    <div class="hero">
      <div class="main-temp">
        <div class="temp-label">
          <span>TEMPERATURE</span>
          <span id="reading-time" style="font-size: 1.2rem; color: var(--lcd-text-dim);">DATA @ --:--:--</span>
        </div>
        <div style="display: flex; width: 100%; justify-content: space-between; align-items: center; padding: 10px 0;">
          <div><span class="temp-val" id="curr-temp">--</span><span class="temp-unit">°C</span></div>
          <div style="font-size: 1.5rem; text-align: right; line-height: 1.2;">
            <div id="seg-temp-up" class="lcd-segment">▲</div>
            <div id="seg-temp-std" class="lcd-segment">≈</div>
            <div id="seg-temp-dn" class="lcd-segment">▼</div>
          </div>
        </div>
        <div class="temp-meta">
          <div>MIN: <span id="lo-temp">--</span></div>
          <div>MAX: <span id="hi-temp">--</span></div>
        </div>
      </div>

      <div class="side-cards">
        <div class="mini-card">
          <div class="mc-label">REL. HUMIDITY</div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 1.2rem; line-height: 1.2;">
              <div id="seg-hum-dry" class="lcd-segment">DRY</div>
              <div id="seg-hum-comf" class="lcd-segment">COMFORT</div>
              <div id="seg-hum-wet" class="lcd-segment">WET</div>
            </div>
            <div class="mc-val" id="curr-hum">--%</div>
          </div>
        </div>
        <div class="mini-card">
          <div class="mc-label">ABS. PRESSURE</div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 1.2rem; line-height: 1.2;">
              <div id="seg-pres-up" class="lcd-segment">▲</div>
              <div id="seg-pres-std" class="lcd-segment">≈</div>
              <div id="seg-pres-dn" class="lcd-segment">▼</div>
            </div>
            <div class="mc-val" id="curr-pres">-- hPa</div>
          </div>
        </div>
        <div class="mini-card" style="padding-bottom: 8px;">
          <div style="display:flex; justify-content: space-between; align-items: center;">
            <div class="mc-label" style="border:none; margin:0; padding:0;">BATTERY</div>
            <div id="seg-bat-low" class="lcd-segment" style="font-size: 1.2rem; text-align: right; margin-right: 10px; flex-grow: 1;">LOW!</div>
            <div class="mc-val" style="font-size: 1.5rem;" id="curr-bat">--%</div>
          </div>
          <div class="bat-bar-bg"><div class="bat-bar-fg" id="bat-fill" style="width: 0%;"></div></div>
        </div>
      </div>
    </div>

    <!-- Summary Section -->
    <div class="summary-section">
      <div class="chart-header">
        <div>
          <div style="font-size: 1.5rem; font-weight: bold; border-bottom: 2px solid var(--lcd-text);">SUMMARY</div>
          <div id="summary-tagline" style="font-size: 1.2rem; color: var(--lcd-text-dim); margin-top: 8px;">LIVE COMPARISON: LOCAL VS OPEN-METEO</div>
        </div>
        <div class="controls">
          <div class="pill-group" id="summary-toggles">
            <button class="pill active" data-sum="now">NOW</button>
            <button class="pill" data-sum="yesterday">YDAY</button>
            <button class="pill" data-sum="3days">72H</button>
            <button class="pill" data-sum="week">7D</button>
          </div>
        </div>
      </div>
      <div class="summary-grid" id="summary-container">
        <!-- Populated by JS -->
      </div>
    </div>

    <!-- Interactive Chart Area -->
    <div class="chart-section">
      <div class="chart-header">
        <div style="font-size: 1.5rem; font-weight: bold; border-bottom: 2px solid var(--lcd-text);">LOG</div>
        <div class="controls">
          <div class="pill-group" id="metric-toggles">
            <button class="pill active" data-metric="temperature">TEMP</button>
            <button class="pill" data-metric="humidity">HUM</button>
            <button class="pill" data-metric="pressure">PRES</button>
            <button class="pill" data-metric="battery_percent">BATT</button>
          </div>
          <div class="pill-group" id="time-toggles">
            <button class="pill active" data-time="today">24H</button>
            <button class="pill" data-time="three_days">72H</button>
            <button class="pill" data-time="week">7D</button>
          </div>
        </div>
      </div>
      <div class="chart-container">

        <canvas id="mainChart"></canvas>
      </div>
    </div>

    <!-- Footer / Tools -->
    <div class="settings-bar">
      <div style="display: flex; gap: 8px; align-items: center;">
        <span>SIM DATE:</span>
        <input type="date" id="sim-date">
        <button onclick="updateSimDate()">SET</button>
      </div>
      <div id="last-update">LAST SYNC: --</div>
    </div>

  </div>
</div>

<script>
let dashboardData = {};
let mainChartInstance = null;
let currentMetric = 'temperature';
let currentSummary = 'now';
let currentTimeframe = 'today';
let lastDashboardHash = '';

// Shared LCD styling variables
const lcdDark = '#171b12';
const lcdDim = 'rgba(23, 27, 18, 0.2)';
const lcdBg = '#9eb084';

const chartConfigs = {
  temperature: { label: 'TEMP (°C)' },
  humidity: { label: 'HUM (%)' },
  pressure: { label: 'PRES (hPa)' },
  battery_percent: { label: 'BATT (%)' }
};

async function fetchDashboard(isInit = false) {
  try {
    const url = isInit ? '/api/dashboard?init=true' : '/api/dashboard';
    const res = await fetch(url);
    const newData = await res.json();
    
    const newHash = (newData.latest ? newData.latest.timestamp : 'no-live') + newData.simulated_today;
    
    if (newHash !== lastDashboardHash) {
      dashboardData = newData;
      lastDashboardHash = newHash;
      updateUI();
      renderChart();
    }
  } catch (err) {
    console.error("Failed to load dashboard:", err);
    document.getElementById('live-text').textContent = "RX: ERROR";
    document.querySelector('.status-dot').classList.remove('active');
  }
}

function updateUI() {
  const live = dashboardData.latest;
  const stats = dashboardData.stats_today;
  
  document.getElementById('live-text').textContent = live ? "RX: OK" : "RX: WAIT";
  const dot = document.querySelector('.status-dot');
  if (live) dot.classList.add('active'); else dot.classList.remove('active');
  
  if (live) {
    document.getElementById('curr-temp').textContent = live.temperature.toFixed(1);
    document.getElementById('curr-hum').textContent = `${live.humidity.toFixed(1)}%`;
    document.getElementById('curr-pres').textContent = `${Math.round(live.pressure)} hPa`;
    document.getElementById('curr-bat').textContent = `${Math.round(live.battery_percent)}%`;
    document.getElementById('bat-fill').style.width = `${live.battery_percent}%`;
    
    const readingDate = new Date(live.timestamp);
    document.getElementById('reading-time').textContent = `DATA @ ${readingDate.toLocaleTimeString('en-US', {hour12: false})}`;
    renderSummary();
    updateSegments(live, dashboardData.charts.today);
  }

  if (stats && stats.temp_high !== null) {
    document.getElementById('hi-temp').textContent = stats.temp_high.toFixed(1);
    document.getElementById('lo-temp').textContent = stats.temp_low.toFixed(1);
  }

  document.getElementById('sim-date').value = dashboardData.simulated_today;
  
  const now = new Date();
  const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
  document.getElementById('last-update').textContent = `LAST SYNC: ${timeStr}`;
}

function updateSegments(live, readings) {
  if (!live) return;
  
  document.getElementById('seg-hum-dry').classList.toggle('active', live.humidity < 40);
  document.getElementById('seg-hum-comf').classList.toggle('active', live.humidity >= 40 && live.humidity <= 60);
  document.getElementById('seg-hum-wet').classList.toggle('active', live.humidity > 60);

  document.getElementById('seg-bat-low').classList.toggle('active', live.battery_percent < 20);

  let past = live;
  if (readings && readings.length > 0) {
    const oneHourAgo = new Date(live.timestamp).getTime() - 60 * 60 * 1000;
    past = readings.find(r => new Date(r.timestamp).getTime() >= oneHourAgo) || readings[0];
  }

  const tempDiff = live.temperature - past.temperature;
  document.getElementById('seg-temp-up').classList.toggle('active', tempDiff > 0.5);
  document.getElementById('seg-temp-std').classList.toggle('active', tempDiff >= -0.5 && tempDiff <= 0.5);
  document.getElementById('seg-temp-dn').classList.toggle('active', tempDiff < -0.5);

  const presDiff = live.pressure - past.pressure;
  document.getElementById('seg-pres-up').classList.toggle('active', presDiff > 1);
  document.getElementById('seg-pres-std').classList.toggle('active', presDiff >= -1 && presDiff <= 1);
  document.getElementById('seg-pres-dn').classList.toggle('active', presDiff < -1);
}

function renderChart() {
  const ctx = document.getElementById('mainChart');
  if (!ctx) return;

  let rawData = dashboardData.charts[currentTimeframe] || [];
  
  let targetPoints = 150;
  let step = Math.ceil(rawData.length / targetPoints);
  let plotData = rawData.filter((_, i) => i % step === 0);

  const labels = plotData.map(r => {
    let d = new Date(r.timestamp);
    if(currentTimeframe === 'today') return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    return d.toLocaleDateString([], {month:'short', day:'numeric'}) + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  });
  
  const dataPoints = plotData.map(r => r[currentMetric]);
  const config = chartConfigs[currentMetric];

  if (mainChartInstance) {
    mainChartInstance.destroy();
  }

  mainChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: config.label,
        data: dataPoints,
        borderColor: lcdDark,
        backgroundColor: 'transparent',
        borderWidth: 3,
        fill: false,
        tension: 0, /* Straight lines for dot matrix feel */
        pointRadius: 2,
        pointStyle: 'rect', /* Square points */
        pointHoverRadius: 6,
        pointHoverBackgroundColor: lcdBg,
        pointHoverBorderWidth: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: lcdBg, borderColor: lcdDark, borderWidth: 2,
          titleColor: lcdDark, bodyColor: lcdDark,
          titleFont: { family: 'Share Tech Mono', size: 16 }, bodyFont: { family: 'Share Tech Mono', size: 16 },
          padding: 10, cornerRadius: 0, displayColors: false
        }
      },
      scales: {
        x: { 
          grid: { color: lcdDim, lineWidth: 1 }, 
          ticks: { color: lcdDark, font: {family: 'Share Tech Mono', size: 14}, maxTicksLimit: 8 } 
        },
        y: { 
          title: { display: true, text: config.label, color: lcdDark, font: { family: 'Share Tech Mono', size: 14 } },
          grid: { color: lcdDim, lineWidth: 1 }, 
          ticks: { color: lcdDark, font: {family: 'Share Tech Mono', size: 14} } 
        }
      }
    }
  });
}

function renderSummary() {
  const container = document.getElementById('summary-container');
  const tagline = document.getElementById('summary-tagline');

  if (currentSummary === 'now') {
    tagline.textContent = 'LIVE COMPARISON: LOCAL VS OPEN-METEO';
    const met = dashboardData.metservice;
    const live = dashboardData.latest;

    if (!met || !live) {
      container.innerHTML = '<div style="font-size: 1.2rem; color: var(--lcd-text-dim);">NO LIVE OR API DATA AVAILABLE</div>';
      return;
    }

    container.style.gridTemplateColumns = '1fr';

    const tDiff = live.temperature - met.temperature;
    const hDiff = live.humidity - met.humidity;
    const pDiff = live.pressure - met.pressure;

    const formatDiff = (val, dec) => {
      if (val > 0) return '+' + val.toFixed(dec);
      if (val < 0) return val.toFixed(dec);
      return (0).toFixed(dec);
    };

    container.innerHTML = `
      <div class="summary-card" style="display: flex; flex-wrap: wrap; gap: 16px; align-items: center;">
        <div class="sc-label" style="border: none; margin: 0; padding: 0; min-width: 120px;">AKL METRO</div>
        <div style="flex: 1; min-width: 200px;">
          <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">TEMP (°C)</div>
          <div class="sc-values">
            <div class="sc-col"><div class="sc-col-title">LOCAL</div><div class="sc-val">${live.temperature.toFixed(1)}</div></div>
            <div class="sc-col"><div class="sc-col-title">API</div><div class="sc-val">${met.temperature.toFixed(1)}</div></div>
            <div class="sc-col"><div class="sc-col-title">DIFF</div><div class="sc-val">${formatDiff(tDiff, 1)}</div></div>
          </div>
        </div>
        <div style="flex: 1; min-width: 200px;">
          <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">HUM (%)</div>
          <div class="sc-values">
            <div class="sc-col"><div class="sc-col-title">LOCAL</div><div class="sc-val">${live.humidity.toFixed(0)}</div></div>
            <div class="sc-col"><div class="sc-col-title">API</div><div class="sc-val">${met.humidity.toFixed(0)}</div></div>
            <div class="sc-col"><div class="sc-col-title">DIFF</div><div class="sc-val">${formatDiff(hDiff, 0)}</div></div>
          </div>
        </div>
        <div style="flex: 1; min-width: 200px;">
          <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">PRES (hPa)</div>
          <div class="sc-values">
            <div class="sc-col"><div class="sc-col-title">LOCAL</div><div class="sc-val">${live.pressure.toFixed(0)}</div></div>
            <div class="sc-col"><div class="sc-col-title">API</div><div class="sc-val">${met.pressure.toFixed(0)}</div></div>
            <div class="sc-col"><div class="sc-col-title">DIFF</div><div class="sc-val">${formatDiff(pDiff, 0)}</div></div>
          </div>
        </div>
      </div>
    `;
    return;
  }

  let daysData = [];
  if (currentSummary === 'yesterday') {
    daysData = dashboardData.stats_yesterday;
    tagline.textContent = 'FULL DAY AGGREGATE: YESTERDAY';
  } else if (currentSummary === '3days') {
    daysData = dashboardData.stats_3days;
    tagline.textContent = 'DAILY BREAKDOWN: PAST 72 HOURS';
  } else if (currentSummary === 'week') {
    daysData = dashboardData.stats_week;
    tagline.textContent = 'DAILY BREAKDOWN: PAST 7 DAYS';
  }

  if (!daysData || daysData.length === 0) {
    container.innerHTML = '<div style="font-size: 1.2rem; color: var(--lcd-text-dim);">NO DATA AVAILABLE</div>';
    return;
  }

  if (currentSummary === '3days') {
    container.style.gridTemplateColumns = 'repeat(auto-fit, minmax(220px, 1fr))';
  } else {
    container.style.gridTemplateColumns = '1fr';
  }

  let html = '';
  for (let day of daysData) {
    const stats = day.stats;
    const dt = new Date(day.date + 'T00:00:00');
    const dateLabel = dt.toLocaleDateString('en-US', { weekday: 'short', month: 'numeric', day: 'numeric' }).toUpperCase();

    if (!stats || stats.count == null) {
      if (currentSummary === '3days') {
        html += `
          <div class="summary-card">
            <div class="sc-label">${dateLabel}</div>
            <div style="font-size: 1.2rem; color: var(--lcd-text-dim); text-align: center; padding: 20px;">NO DATA</div>
          </div>
        `;
      } else {
        html += `
          <div class="summary-card" style="display: flex; flex-wrap: wrap; gap: 16px; align-items: center;">
            <div class="sc-label" style="border: none; margin: 0; padding: 0; min-width: 120px;">${dateLabel}</div>
            <div style="flex: 1; font-size: 1.2rem; color: var(--lcd-text-dim); text-align: center; padding: 10px;">NO DATA</div>
          </div>
        `;
      }
      continue;
    }

    if (currentSummary === '3days') {
      html += `
        <div class="summary-card">
          <div class="sc-label">${dateLabel}</div>
          
          <div style="margin-bottom: 12px;">
            <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">TEMP (°C)</div>
            <div class="sc-values">
              <div class="sc-col"><div class="sc-col-title">MAX</div><div class="sc-val">${stats.temp_high != null ? stats.temp_high.toFixed(1) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">AVG</div><div class="sc-val">${stats.temp_avg != null ? stats.temp_avg.toFixed(1) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">MIN</div><div class="sc-val">${stats.temp_low != null ? stats.temp_low.toFixed(1) : '--'}</div></div>
            </div>
          </div>
          <div style="margin-bottom: 12px;">
            <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">HUM (%)</div>
            <div class="sc-values">
              <div class="sc-col"><div class="sc-col-title">MAX</div><div class="sc-val">${stats.hum_high != null ? stats.hum_high.toFixed(0) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">AVG</div><div class="sc-val">${stats.hum_avg != null ? stats.hum_avg.toFixed(0) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">MIN</div><div class="sc-val">${stats.hum_low != null ? stats.hum_low.toFixed(0) : '--'}</div></div>
            </div>
          </div>
          <div>
            <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">PRES (hPa)</div>
            <div class="sc-values">
              <div class="sc-col"><div class="sc-col-title">MAX</div><div class="sc-val">${stats.pres_high != null ? stats.pres_high.toFixed(0) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">AVG</div><div class="sc-val">${stats.pres_avg != null ? stats.pres_avg.toFixed(0) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">MIN</div><div class="sc-val">${stats.pres_low != null ? stats.pres_low.toFixed(0) : '--'}</div></div>
            </div>
          </div>
        </div>
      `;
    } else {
      html += `
        <div class="summary-card" style="display: flex; flex-wrap: wrap; gap: 16px; align-items: center;">
          <div class="sc-label" style="border: none; margin: 0; padding: 0; min-width: 120px;">${dateLabel}</div>
          
          <div style="flex: 1; min-width: 200px;">
            <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">TEMP (°C)</div>
            <div class="sc-values">
              <div class="sc-col"><div class="sc-col-title">MAX</div><div class="sc-val">${stats.temp_high != null ? stats.temp_high.toFixed(1) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">AVG</div><div class="sc-val">${stats.temp_avg != null ? stats.temp_avg.toFixed(1) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">MIN</div><div class="sc-val">${stats.temp_low != null ? stats.temp_low.toFixed(1) : '--'}</div></div>
            </div>
          </div>
          <div style="flex: 1; min-width: 200px;">
            <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">HUM (%)</div>
            <div class="sc-values">
              <div class="sc-col"><div class="sc-col-title">MAX</div><div class="sc-val">${stats.hum_high != null ? stats.hum_high.toFixed(0) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">AVG</div><div class="sc-val">${stats.hum_avg != null ? stats.hum_avg.toFixed(0) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">MIN</div><div class="sc-val">${stats.hum_low != null ? stats.hum_low.toFixed(0) : '--'}</div></div>
            </div>
          </div>
          <div style="flex: 1; min-width: 200px;">
            <div class="sc-col-title" style="color: var(--lcd-text); margin-bottom: 4px; border-bottom: 1px dashed var(--lcd-text-dim); text-align: center;">PRES (hPa)</div>
            <div class="sc-values">
              <div class="sc-col"><div class="sc-col-title">MAX</div><div class="sc-val">${stats.pres_high != null ? stats.pres_high.toFixed(0) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">AVG</div><div class="sc-val">${stats.pres_avg != null ? stats.pres_avg.toFixed(0) : '--'}</div></div>
              <div class="sc-col"><div class="sc-col-title">MIN</div><div class="sc-val">${stats.pres_low != null ? stats.pres_low.toFixed(0) : '--'}</div></div>
            </div>
          </div>
        </div>
      `;
    }
  }
  container.innerHTML = html;
}

document.getElementById('summary-toggles').addEventListener('click', (e) => {
  if(e.target.tagName === 'BUTTON') {
    document.querySelectorAll('#summary-toggles button').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    currentSummary = e.target.dataset.sum;
    renderSummary();
  }
});

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
  lastDashboardHash = '';
  fetchDashboard(true);
}

// Live Clock Update
function updateLiveClock() {
  const now = new Date();
  document.getElementById('live-clock').textContent = now.toLocaleTimeString('en-US', {hour12: false});
}
setInterval(updateLiveClock, 1000);
updateLiveClock();

// Boot up
fetchDashboard(true);
setInterval(() => fetchDashboard(false), 30000); 

</script>
</body>
</html>
"""

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    print("=" * 60)
    print("  Weather Station Dashboard (V3 - LCD Theme)")
    print("  http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)