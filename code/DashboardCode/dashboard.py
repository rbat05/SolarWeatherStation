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
LIVE_DB_PATH = os.path.join(os.path.dirname(__file__), "weather.db")
REPLAY_DB_PATH = os.path.join(os.path.dirname(__file__), "replay.db")

# --- SECURITY ---
INGEST_API_KEY = "my_super_secret_weather_key_123" # Change this to a secure random string!

_cached_metservice = None
_last_reading_ts = None

# ─── Database Setup ──────────────────────────────────────────────────────────

def get_db(mode="live"):
    db_path = LIVE_DB_PATH if mode == "live" else REPLAY_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path):
    with sqlite3.connect(db_path) as conn:
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relay_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_contact TEXT,
                last_payload TEXT,
                last_response_code INTEGER,
                packets_received INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                tracking_start TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE relay_status ADD COLUMN tracking_start TEXT")
        except sqlite3.OperationalError:
            pass

        result = conn.execute("SELECT value FROM settings WHERE key='simulated_today'").fetchone()
        if not result:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('simulated_today', ?)",
                (date.today().isoformat(),)
            )
        conn.execute("INSERT OR IGNORE INTO relay_status (id, packets_received, errors, tracking_start) VALUES (1, 0, 0, ?)", (datetime.now().isoformat(),))
        conn.execute("UPDATE relay_status SET tracking_start = ? WHERE id = 1 AND tracking_start IS NULL", (datetime.now().isoformat(),))
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

def get_simulated_today(mode="live") -> str:
    with get_db(mode) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='simulated_today'").fetchone()
        return row["value"] if row else date.today().isoformat()

def set_simulated_today(day_str: str, mode="live"):
    with get_db(mode) as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('simulated_today', ?)", (day_str,))
        conn.commit()

def get_relay_status(mode="live") -> dict | None:
    with get_db(mode) as conn:
        row = conn.execute("SELECT * FROM relay_status WHERE id = 1").fetchone()
        return dict(row) if row else None

def stats_for_day(day_date: str, mode="live") -> dict:
    with get_db(mode) as conn:
        row = conn.execute("""
            SELECT MIN(temperature) as temp_low, MAX(temperature) as temp_high, AVG(temperature) as temp_avg,
                   MIN(humidity) as hum_low, MAX(humidity) as hum_high, AVG(humidity) as hum_avg,
                   MIN(pressure) as pres_low, MAX(pressure) as pres_high, AVG(pressure) as pres_avg,
                   COUNT(*) as count
            FROM readings WHERE day_date = ?
        """, (day_date,)).fetchone()
        return dict(row) if row and row["count"] > 0 else {}

def readings_for_range(start_date: str, end_date: str, mode="live") -> list:
    with get_db(mode) as conn:
        rows = conn.execute("SELECT * FROM readings WHERE day_date >= ? AND day_date <= ? ORDER BY timestamp ASC", (start_date, end_date)).fetchall()
        return [dict(r) for r in rows]

def latest_reading(mode="live") -> dict | None:
    with get_db(mode) as conn:
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
    # --- API KEY SECURITY CHECK ---
    provided_key = request.headers.get("X-API-Key")
    if provided_key != INGEST_API_KEY:
        print("[!] Unauthorized ingest attempt.")
        return jsonify({"error": "Unauthorized"}), 401
    # ------------------------------

    data = request.get_data(as_text=True).strip()
    contact_ts = datetime.now().isoformat()
    payload_trunc = data[:200]

    reading = parse_reading_line(data, source="live")
    if not reading:
        try:
            reading = request.get_json()
            if reading:
                reading["source"] = "live"
                payload_trunc = "JSON Payload"
        except Exception: 
            pass

    is_error = 1 if not reading else 0
    response_code = 400 if is_error else 201

    with get_db("live") as conn:
        conn.execute("""
            UPDATE relay_status 
            SET last_contact = ?, last_payload = ?, last_response_code = ?, 
                packets_received = packets_received + 1, errors = errors + ?
            WHERE id = 1
        """, (contact_ts, payload_trunc, response_code, is_error))

        if reading:
            conn.execute("""
                INSERT INTO readings (timestamp, day_date, temperature, humidity, pressure, battery_voltage, battery_percent, source)
                VALUES (:timestamp, :day_date, :temperature, :humidity, :pressure, :battery_voltage, :battery_percent, :source)
            """, reading)
            
            # Auto-purge data older than 7 days
            sim_today = get_simulated_today("live")
            cutoff_date = (datetime.strptime(sim_today, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
            conn.execute("DELETE FROM readings WHERE day_date < ?", (cutoff_date,))
            
            # Long-term CSV Logging
            try:
                data_dir = os.path.join(os.path.dirname(__file__), "archive")
                os.makedirs(data_dir, exist_ok=True)
                csv_path = os.path.join(data_dir, f"{reading['day_date']}.csv")
                
                dt_obj = datetime.fromisoformat(reading["timestamp"])
                ts_str = dt_obj.strftime("%a %d/%m/%Y - %H:%M:%S")
                csv_line = f"{ts_str},{reading['temperature']:.2f},{reading['humidity']:.2f},{reading['pressure']:.2f},{reading['battery_voltage']:.2f},{reading['battery_percent']:.2f}\n"
                
                with open(csv_path, "a", encoding="utf-8") as f:
                    f.write(csv_line)
            except Exception as e:
                print(f"[!] Failed to write to CSV archive: {e}")
        conn.commit()
        
    if is_error:
        return jsonify({"error": "Invalid data format"}), 400
    return jsonify({"status": "ok", "timestamp": reading["timestamp"]}), 201

@app.route("/api/set-today", methods=["POST"])
def api_set_today():
    body = request.get_json()
    day_str = body.get("date", "")
    mode = body.get("mode", "live")
    set_simulated_today(day_str, mode)
    return jsonify({"status": "ok", "simulated_today": day_str})

@app.route("/api/settings")
def api_settings():
    mode = request.args.get("mode", "live")
    today = get_simulated_today(mode)
    data_dir = os.path.join(os.path.dirname(__file__), "archive")
    csv_files = []
    if os.path.exists(data_dir):
        csv_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".csv")], reverse=True)
    return jsonify({
        "simulated_today": today,
        "csv_files": csv_files
    })

@app.route("/api/load-csv", methods=["POST"])
def load_csv():
    body = request.get_json()
    mode = body.get("mode", "replay")
    filename = body.get("filename", "")
    clear_existing = body.get("clear_existing", True)

    m = re.match(r'(\d{4}-\d{2}-\d{2})\.csv', os.path.basename(filename))
    if not m:
        return jsonify({"error": "Filename must be YYYY-MM-DD.csv"}), 400

    day_date = m.group(1)
    data_dir = os.path.join(os.path.dirname(__file__), "archive")
    filepath = os.path.join(data_dir, os.path.basename(filename))

    if not os.path.exists(filepath):
        return jsonify({"error": f"File not found: {filepath}"}), 404

    inserted, errors = 0, 0
    with get_db(mode) as conn:
        if clear_existing:
            conn.execute("DELETE FROM readings WHERE day_date = ? AND source = 'csv'", (day_date,))
        with open(filepath, "r") as f:
            for line in f:
                reading = parse_reading_line(line, source="csv")
                if reading:
                    conn.execute("INSERT INTO readings (timestamp, day_date, temperature, humidity, pressure, battery_voltage, battery_percent, source) VALUES (:timestamp, :day_date, :temperature, :humidity, :pressure, :battery_voltage, :battery_percent, :source)", reading)
                    inserted += 1
                elif line.strip() and not line.startswith("#"):
                    errors += 1
        conn.commit()
    return jsonify({"status": "ok", "day_date": day_date, "inserted": inserted, "errors": errors})

@app.route("/api/clear-replay", methods=["POST"])
def clear_replay():
    with get_db("replay") as conn:
        conn.execute("DELETE FROM readings")
        conn.commit()
    return jsonify({"status": "ok"})

@app.route("/api/reset-relay-metrics", methods=["POST"])
def reset_relay_metrics():
    mode = request.get_json().get("mode", "live") if request.is_json else "live"
    with get_db(mode) as conn:
        conn.execute("UPDATE relay_status SET packets_received = 0, errors = 0, tracking_start = ? WHERE id = 1", (datetime.now().isoformat(),))
        conn.commit()
    return jsonify({"status": "ok"})

@app.route("/api/dashboard")
def api_dashboard():
    mode = request.args.get("mode", "live")
    global _cached_metservice, _last_reading_ts
    today = get_simulated_today(mode)
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    last3 = days_with_data(3, today)
    last7 = days_with_data(7, today)
    
    latest = latest_reading(mode)
    latest_ts = latest["timestamp"] if latest else None
    is_init = request.args.get("init") == "true"

    if is_init or _cached_metservice is None or latest_ts != _last_reading_ts:
        _cached_metservice = fetch_metservice_current("auckland")
        _last_reading_ts = latest_ts
        
    return jsonify({
        "simulated_today": today,
        "latest": latest,
        "stats_today": stats_for_day(today, mode),
        "stats_yesterday": [{"date": yesterday, "stats": stats_for_day(yesterday, mode)}],
        "stats_3days": [{"date": d, "stats": stats_for_day(d, mode)} for d in last3],
        "stats_week": [{"date": d, "stats": stats_for_day(d, mode)} for d in last7],
        "metservice": _cached_metservice,
        "charts": {
            "week": readings_for_range(last7[0], last7[-1], mode)
        },
        "relay_status": get_relay_status(mode)})


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

# ─── HTML Template (V3 - Commercial LCD) ───────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1000">
<title>Weather Monitor Dashboard</title>
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
    gap: 20px;
  }

  /* ─── Header ─── */
  header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid var(--lcd-text); padding-bottom: 20px; flex-wrap: wrap; gap: 10px; }
  .brand { font-size: 2rem; font-weight: bold; letter-spacing: 2px; display: flex; align-items: center; }
  .status-badge { display: flex; align-items: center; gap: 12px; font-size: 1.5rem; }
  
  @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
  .status-dot { width: 16px; height: 16px; background: var(--lcd-text); border-radius: 2px; }
  .status-dot.active { animation: blink 1s infinite steps(2, start); }

  /* ─── Main Readouts ─── */
  .hero { display: flex; gap: 16px; border-bottom: 3px solid var(--lcd-text); padding-bottom: 20px; }
  
  @keyframes pulse-segment { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .lcd-segment { color: var(--lcd-text); opacity: 0.12; line-height: 1.2; cursor: help; user-select: none; font-weight: bold; transition: opacity 0.3s; }
  .lcd-segment.active { opacity: 1; animation: pulse-segment 2s infinite ease-in-out; }

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
  .summary-section { border-bottom: 3px solid var(--lcd-text); padding-bottom: 20px; }
  .summary-grid { display: grid; grid-template-columns: 1fr; gap: 16px; margin-top: 10px; }
  .summary-card { border: 3px solid var(--lcd-text); padding: 12px; }
  .sc-label { font-size: 1.2rem; border-bottom: 2px solid var(--lcd-text); padding-bottom: 4px; margin-bottom: 8px; }
  .sc-values { display: flex; justify-content: space-between; text-align: center; }
  .sc-col { flex: 1; display: flex; flex-direction: column; border-right: 2px dashed var(--lcd-text-dim); }
  .sc-col:last-child { border-right: none; }
  .sc-col-title { font-size: 1rem; color: var(--lcd-text-dim); margin-bottom: 4px; }
  .sc-val { font-size: 1.5rem; }

  /* ─── Chart Section ─── */
  .chart-section { border-bottom: 3px solid var(--lcd-text); padding-bottom: 20px; }
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

  .chart-container { 
    position: relative; height: 300px; width: 100%; border: 3px solid var(--lcd-text); padding: 10px; overflow: hidden; display: block; box-sizing: border-box;
  }

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

  /* ─── Replay Section ─── */
  .replay-section { border-bottom: 3px solid var(--lcd-text); padding-bottom: 20px; }
  .replay-section input[type="date"] { background: transparent; border: 2px solid var(--lcd-text); color: var(--lcd-text); font-family: var(--font-lcd); font-size: 1.2rem; padding: 4px 8px; outline: none; }
  .replay-section button { background: var(--lcd-text); color: var(--lcd-bg); border: 2px solid var(--lcd-text); font-family: var(--font-lcd); font-size: 1.2rem; padding: 4px 16px; cursor: pointer; font-weight: bold; }
  .replay-section button:active { background: transparent; color: var(--lcd-text); }
  .replay-section select { background: transparent; border: 2px solid var(--lcd-text); color: var(--lcd-text); font-family: var(--font-lcd); font-size: 1.2rem; padding: 4px 8px; outline: none; cursor: pointer; }

</style>
</head>
<body>

<div class="device-bezel">
  <div class="device-logo">WEATHER MONITOR DASHBOARD</div>
  <div class="lcd-screen">
    
    <!-- Header -->
    <header>
      <div class="brand">
        WEATHER MONITOR <span id="live-clock" style="font-size: 1.2rem; margin-left: 20px; color: var(--lcd-text-dim);">--:--:--</span>
      </div>
      <div class="mode-selector" style="display: flex; gap: 8px;">
        <button id="btn-mode-live" class="pill active" onclick="setMode('live')">LIVE</button>
        <button id="btn-mode-replay" class="pill" onclick="setMode('replay')">REPLAY</button>
      </div>
      <div class="status-badge" id="status-badge-container">
        <span id="live-text">RX: WAIT</span>
        <div class="status-dot"></div>
      </div>
    </header>

    <!-- Hero Stats -->
    <div class="hero" id="hero-section">
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
            <div id="seg-bat-low" class="lcd-segment" style="font-size: 1.2rem; text-align: left; margin-right: 10px; flex-grow: 1; padding-left: 10px;">LOW!</div>
            <div class="mc-val" style="font-size: 1.5rem;" id="curr-bat">--%</div>
          </div>
          <div class="bat-bar-bg"><div class="bat-bar-fg" id="bat-fill" style="width: 0%;"></div></div>
        </div>
      </div>
    </div>

    <!-- Replay Setup Section -->
    <div class="replay-section" id="settings-section" style="display: none;">
      <div class="chart-header">
        <div>
          <div style="font-size: 1.5rem; font-weight: bold; border-bottom: 2px solid var(--lcd-text);">REPLAY SETUP</div>
          <div style="font-size: 1.2rem; color: var(--lcd-text-dim); margin-top: 8px;">CONFIGURE HISTORICAL DATA PLAYBACK</div>
        </div>
      </div>
      <div style="display: flex; gap: 24px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 250px;">
          <div style="font-size: 1rem; color: var(--lcd-text-dim); margin-bottom: 8px;">1. LOAD ARCHIVED CSV</div>
          <div style="display: flex; gap: 8px;">
            <select id="csv-file-select" style="flex: 1; width: 0; min-width: 0;"></select>
            <button onclick="loadSelectedCSV()">LOAD</button>
          </div>
          <div id="csv-status" style="font-size: 1rem; color: var(--lcd-text-dim); margin-top: 4px; min-height: 1.2em;"></div>
        </div>
        <div style="flex: 1; min-width: 200px;">
          <div style="font-size: 1rem; color: var(--lcd-text-dim); margin-bottom: 8px;">2. SET SIMULATED DATE</div>
          <div style="display: flex; gap: 8px;">
            <input type="date" id="sim-date" style="flex: 1; width: 0;">
            <button onclick="updateSimDate()">SET</button>
          </div>
        </div>
        <div style="flex: 1; min-width: 150px;">
          <div style="font-size: 1rem; color: var(--lcd-text-dim); margin-bottom: 8px;">3. RESET DATA</div>
          <button style="width: 100%;" onclick="clearReplayDB()">CLEAR DB</button>
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
            <button class="pill" data-sum="today" style="display: none;">TDAY</button>
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
        <div>
          <div style="font-size: 1.5rem; font-weight: bold; border-bottom: 2px solid var(--lcd-text);">LOGGED DATA</div>
          <div id="chart-tagline" style="font-size: 1.2rem; color: var(--lcd-text-dim); margin-top: 8px;">SELECT METRIC AND TIMEFRAME TO VIEW DATA</div>
        </div>
      </div>
      <div class="chart-container">

        <canvas id="mainChart"></canvas>
      </div>
      <div class="controls" style="justify-content: space-between; margin-top: 12px;">
        <div class="pill-group" id="metric-toggles">
          <button class="pill active" data-metric="temperature">TEMP</button>
          <button class="pill" data-metric="humidity">HUM</button>
          <button class="pill" data-metric="pressure">PRES</button>
          <button class="pill" data-metric="battery_percent">BATT</button>
        </div>
        <div class="pill-group" id="time-toggles">
          <button class="pill live-only-time" data-time="1h">1H</button>
          <button class="pill active live-only-time" data-time="3h">3H</button>
          <button class="pill live-only-time" data-time="12h">12H</button>
          <button class="pill" data-time="today">24H</button>
          <button class="pill" data-time="three_days">72H</button>
          <button class="pill" data-time="week">7D</button>
        </div>
      </div>
      <div id="custom-time-container" style="display: none; flex-direction: column; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 2px dashed var(--lcd-text-dim);">
        <div style="font-size: 1.2rem; font-weight: bold; color: var(--lcd-text);">CUSTOM TIME RANGE FILTER</div>
        <div style="font-size: 1rem; color: var(--lcd-text-dim);">ENTER START AND END TIMES TO ISOLATE A SPECIFIC PORTION OF THE SIMULATED DAY.</div>
        <div style="display: flex; gap: 12px; align-items: center; margin-top: 8px; flex-wrap: wrap;">
          <span style="color: var(--lcd-text-dim); font-size: 1.2rem;">START TIME:</span>
          <input type="time" id="custom-start" value="06:00" style="background: transparent; border: 2px solid var(--lcd-text); color: var(--lcd-text); font-family: var(--font-lcd); font-size: 1.2rem; padding: 4px 8px; outline: none; cursor: pointer;">
          <span style="color: var(--lcd-text-dim); font-size: 1.2rem; margin-left: 12px;">END TIME:</span>
          <input type="time" id="custom-end" value="18:00" style="background: transparent; border: 2px solid var(--lcd-text); color: var(--lcd-text); font-family: var(--font-lcd); font-size: 1.2rem; padding: 4px 8px; outline: none; cursor: pointer;">
          <button class="pill" style="font-weight: bold; margin-left: 12px;" onclick="applyCustomRange()">PLOT RANGE</button>
        </div>
      </div>
    </div>

    <!-- Relay Status Section -->
    <div id="diagnostics-btn-container">
      <button class="pill" style="width: 100%; border: 3px solid var(--lcd-text); font-weight: bold; cursor: pointer; text-align: center; padding: 12px; transition: all 0.2s;" onclick="const p = document.getElementById('diagnostics-panel'); p.style.display = p.style.display === 'none' ? 'block' : 'none'; this.classList.toggle('active');">
        [ SYS DIAGNOSTICS & RELAY STATUS ]
      </button>
    </div>
    
    <div id="diagnostics-panel" style="display: none; border: 3px solid var(--lcd-text); padding: 16px; background: rgba(0,0,0,0.05);">
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; font-size: 1.2rem;">
        <div>LAST CONTACT: <br><span id="diag-contact" style="color: var(--lcd-text-dim);">--</span></div>
        <div>RELAY HEALTH: <br><span id="diag-health" style="color: var(--lcd-text-dim);">--</span></div>
        <div>PACKETS RX: <br><span id="diag-rx" style="color: var(--lcd-text-dim);">--</span></div>
        <div>PACKET LOSS: <br><span id="diag-loss" style="color: var(--lcd-text-dim);">--</span></div>
        <div style="grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center; border-top: 2px dashed var(--lcd-text-dim); padding-top: 12px;">
          <div>LAST PAYLOAD: <br><span id="diag-payload" style="color: var(--lcd-text-dim); word-break: break-all;">--</span></div>
          <button class="pill" style="border: 2px solid var(--lcd-text); font-weight: bold; color: var(--lcd-text); padding: 8px 16px; white-space: nowrap;" onclick="resetRelayMetrics()">RESET RX STATS</button>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
let dashboardData = {};
let appMode = 'live';
let mainChartInstance = null;
let currentMetric = 'temperature';
let currentSummary = 'now';
let currentTimeframe = '3h';
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

function setMode(mode) {
  appMode = mode;
  document.getElementById('btn-mode-live').classList.toggle('active', mode === 'live');
  document.getElementById('btn-mode-replay').classList.toggle('active', mode === 'replay');
  
  document.getElementById('hero-section').style.display = mode === 'live' ? 'flex' : 'none';
  document.getElementById('settings-section').style.display = mode === 'replay' ? 'block' : 'none';
  document.getElementById('status-badge-container').style.display = mode === 'live' ? 'flex' : 'none';
  document.getElementById('diagnostics-btn-container').style.display = mode === 'live' ? 'block' : 'none';
  document.getElementById('diagnostics-panel').style.display = 'none';
  
  // Forcefully destroy the chart on mode switch to guarantee a clean slate
  if (mainChartInstance) {
    mainChartInstance.destroy();
    mainChartInstance = null;
  }

  document.querySelectorAll('.live-only-time').forEach(el => el.style.display = mode === 'live' ? 'inline-block' : 'none');
  document.getElementById('custom-time-container').style.display = mode === 'replay' ? 'flex' : 'none';

  if (mode === 'replay' && ['1h', '3h', '12h'].includes(currentTimeframe)) {
    currentTimeframe = 'today';
    document.querySelectorAll('#time-toggles button').forEach(b => b.classList.remove('active'));
    document.querySelector('button[data-time="today"]').classList.add('active');
  }
  if (mode === 'live' && currentTimeframe === 'custom') {
    currentTimeframe = '3h';
    document.querySelectorAll('#time-toggles button').forEach(b => b.classList.remove('active'));
    document.querySelector('button[data-time="3h"]').classList.add('active');
  }

  const btnNow = document.querySelector('button[data-sum="now"]');
  const btnToday = document.querySelector('button[data-sum="today"]');
  if (mode === 'replay') {
    btnNow.style.display = 'none';
    btnToday.style.display = 'inline-block';
    if (currentSummary === 'now') {
      currentSummary = 'today';
      document.querySelectorAll('#summary-toggles button').forEach(b => b.classList.remove('active'));
      btnToday.classList.add('active');
    }
  } else {
    btnNow.style.display = 'inline-block';
    btnToday.style.display = 'none';
    if (currentSummary === 'today') {
      currentSummary = 'now';
      document.querySelectorAll('#summary-toggles button').forEach(b => b.classList.remove('active'));
      btnNow.classList.add('active');
    }
  }

  lastDashboardHash = '';
  loadSettings();
  fetchDashboard(true);
}

async function fetchDashboard(isInit = false) {
  try {
    const url = '/api/dashboard?mode=' + appMode + '&_t=' + Date.now() + (isInit ? '&init=true' : '');
    const res = await fetch(url);
    const newData = await res.json();
    
    const newHash = appMode + (newData.latest ? newData.latest.timestamp : 'no-live') + newData.simulated_today + 
                    (newData.relay_status ? newData.relay_status.packets_received + '-' + newData.relay_status.errors : '');
    
    if (newHash !== lastDashboardHash) {
      dashboardData = newData;
      lastDashboardHash = newHash;
      updateUI();
      renderChart();
      
      // Force layout resolution on first load to prevent 0x0 invisible canvas bug
      if (isInit) {
        setTimeout(() => { if (mainChartInstance) mainChartInstance.resize(); }, 150);
      }
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
  
  if (live) {
    document.getElementById('curr-temp').textContent = live.temperature.toFixed(1);
    document.getElementById('curr-hum').textContent = `${live.humidity.toFixed(1)}%`;
    document.getElementById('curr-pres').textContent = `${Math.round(live.pressure)} hPa`;
    document.getElementById('curr-bat').textContent = `${Math.round(live.battery_percent)}%`;
    document.getElementById('bat-fill').style.width = `${live.battery_percent}%`;
    
    const readingDate = new Date(live.timestamp);
    document.getElementById('reading-time').textContent = `DATA @ ${readingDate.toLocaleTimeString('en-US', {hour12: false})}`;
    updateSegments(live, dashboardData.charts.week);
  } else {
    document.getElementById('curr-temp').textContent = '--';
    document.getElementById('curr-hum').textContent = '--%';
    document.getElementById('curr-pres').textContent = '-- hPa';
    document.getElementById('curr-bat').textContent = '--%';
    document.getElementById('bat-fill').style.width = '0%';
    document.getElementById('reading-time').textContent = 'DATA @ --:--:--';
    document.querySelectorAll('.lcd-segment').forEach(el => el.classList.remove('active'));
  }

  renderSummary();

  if (stats && stats.temp_high !== undefined && stats.temp_high !== null) {
    document.getElementById('hi-temp').textContent = stats.temp_high.toFixed(1);
    document.getElementById('lo-temp').textContent = stats.temp_low.toFixed(1);
  } else {
    document.getElementById('hi-temp').textContent = '--';
    document.getElementById('lo-temp').textContent = '--';
  }

  if (dashboardData.relay_status) {
    const rs = dashboardData.relay_status;
    document.getElementById('diag-contact').textContent = rs.last_contact ? new Date(rs.last_contact).toLocaleTimeString('en-US', {hour12: false}) : 'NEVER';
    
    let healthText = '--';
    if (rs.last_response_code === 200 || rs.last_response_code === 201) {
      healthText = 'HEALTHY';
    } else if (rs.last_response_code) {
      healthText = 'FAULT (CODE ' + rs.last_response_code + ')';
    }
    document.getElementById('diag-health').textContent = healthText;

    document.getElementById('diag-rx').textContent = rs.packets_received || '0';
    document.getElementById('diag-payload').textContent = rs.last_payload || 'NONE';
  }

  document.getElementById('sim-date').value = dashboardData.simulated_today;
}

function updateSegments(live, readings) {
  if (!live) return;
  
  const setSegment = (id, isActive, criteria) => {
    const el = document.getElementById(id);
    if (el) {
      el.classList.toggle('active', isActive);
      el.title = isActive ? `Active: ${criteria}` : `Condition: ${criteria}`;
    }
  };
  
  setSegment('seg-hum-dry', live.humidity < 40, 'Humidity < 40%');
  setSegment('seg-hum-comf', live.humidity >= 40 && live.humidity <= 60, 'Humidity 40% to 60%');
  setSegment('seg-hum-wet', live.humidity > 60, 'Humidity > 60%');

  setSegment('seg-bat-low', live.battery_percent < 20, 'Battery < 20%');

  let past = live;
  if (readings && readings.length > 0) {
    const oneHourAgo = new Date(live.timestamp).getTime() - 60 * 60 * 1000;
    past = readings.find(r => new Date(r.timestamp).getTime() >= oneHourAgo) || readings[0];
  }

  const tempDiff = live.temperature - past.temperature;
  setSegment('seg-temp-up', tempDiff > 0.5, 'Temp increased > +0.5°C/hr');
  setSegment('seg-temp-std', tempDiff >= -0.5 && tempDiff <= 0.5, 'Temp changed ≤ 0.5°C/hr');
  setSegment('seg-temp-dn', tempDiff < -0.5, 'Temp decreased < -0.5°C/hr');

  const presDiff = live.pressure - past.pressure;
  setSegment('seg-pres-up', presDiff > 1, 'Pressure increased > +1.0 hPa/hr');
  setSegment('seg-pres-std', presDiff >= -1 && presDiff <= 1, 'Pressure changed ≤ 1.0 hPa/hr');
  setSegment('seg-pres-dn', presDiff < -1, 'Pressure decreased < -1.0 hPa/hr');
}

function renderChart() {
  const ctx = document.getElementById('mainChart');
  if (!ctx) return;

  // 1. Establish the exact start and end times for the X-axis
  let startMs, endMs;
  let hours = 24;

  if (currentTimeframe === 'custom') {
    const startVal = document.getElementById('custom-start').value || '00:00';
    const endVal = document.getElementById('custom-end').value || '23:59';
    startMs = new Date(dashboardData.simulated_today + 'T' + startVal + ':00').getTime();
    endMs = new Date(dashboardData.simulated_today + 'T' + endVal + ':59').getTime();
    hours = (endMs - startMs) / (1000 * 60 * 60);
  } else if (appMode === 'replay' && currentTimeframe === 'today') {
    startMs = new Date(dashboardData.simulated_today + 'T00:00:00').getTime();
    endMs = new Date(dashboardData.simulated_today + 'T23:59:59').getTime();
    hours = 24;
  } else {
    let nowMs = Date.now();
    if (dashboardData.latest && appMode === 'live') {
      nowMs = new Date(dashboardData.latest.timestamp).getTime();
    } else if (dashboardData.simulated_today) {
      nowMs = new Date(dashboardData.simulated_today + 'T23:59:59').getTime();
    }
    if (currentTimeframe === '1h') hours = 1;
    else if (currentTimeframe === '3h') hours = 3;
    else if (currentTimeframe === '12h') hours = 12;
    else if (currentTimeframe === 'three_days') hours = 72;
    else if (currentTimeframe === 'week') hours = 24 * 7;
    startMs = nowMs - (hours * 60 * 60 * 1000);
    endMs = nowMs;
  }

  // 2. Fetch the largest possible dataset and map timestamps for speed
  let rawData = [];
  if (dashboardData.charts && dashboardData.charts.week) {
    for (let i = 0; i < dashboardData.charts.week.length; i++) {
      let r = dashboardData.charts.week[i];
      let t = new Date(r.timestamp).getTime();
      if (t >= startMs && t <= endMs) {
        rawData.push({ val: r[currentMetric], t: t });
      }
    }
  }
  
  let targetPoints = 150;
  let stepMs = Math.max(1, (endMs - startMs) / targetPoints);
  let labels = [];
  let dataPoints = [];
  let maxAllowedDistance = Math.max(5 * 60 * 1000, stepMs);

  // 3. Create time buckets and inject `null` if no data exists nearby
  for (let i = 0; i <= targetPoints; i++) {
    let bucketTime = startMs + (i * stepMs);
    
    let closestReading = null;
    let minDiff = Infinity;
    for (let j = 0; j < rawData.length; j++) {
      let diff = Math.abs(rawData[j].t - bucketTime);
      if (diff < minDiff) {
        minDiff = diff;
        closestReading = rawData[j];
      }
    }
    
    if (closestReading && minDiff <= maxAllowedDistance) {
      dataPoints.push(closestReading.val);
    } else {
      dataPoints.push(null);
    }

    let d = new Date(bucketTime);
    if (hours <= 24) {
      labels.push(d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));
    } else {
      labels.push([
        d.toLocaleDateString([], {month:'short', day:'numeric'}), 
        d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
      ]);
    }
  }

  const config = chartConfigs[currentMetric];

  if (mainChartInstance) {
    mainChartInstance.data.labels = labels;
    mainChartInstance.data.datasets[0].label = config.label;
    mainChartInstance.data.datasets[0].data = dataPoints;
    mainChartInstance.options.scales.y.title.text = config.label;
    mainChartInstance.update();
    return;
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
          border: { display: true, color: lcdDark, width: 3 },
          grid: { color: lcdDark, drawOnChartArea: false, lineWidth: 2 }, 
          ticks: { color: lcdDark, font: {family: 'Share Tech Mono', size: 14}, maxTicksLimit: 8 } 
        },
        y: { 
          border: { display: true, color: lcdDark, width: 3 },
          title: { display: true, text: config.label, color: lcdDark, font: { family: 'Share Tech Mono', size: 14 } },
          grid: { color: lcdDark, drawOnChartArea: false, lineWidth: 2 }, 
          ticks: { color: lcdDark, font: {family: 'Share Tech Mono', size: 14} } 
        }
      }
    },
    plugins: [{
      id: 'matrixGrid',
      beforeDraw: (chart) => {
        const { ctx, chartArea } = chart;
        if (!chartArea) return;
        ctx.save();
        ctx.beginPath();
        ctx.rect(chartArea.left, chartArea.top, chartArea.width, chartArea.height);
        ctx.clip();
        ctx.strokeStyle = 'rgba(23, 27, 18, 0.15)';
        ctx.lineWidth = 1;
        for (let x = chartArea.left; x <= chartArea.right; x += 20) {
          ctx.beginPath(); ctx.moveTo(x, chartArea.top); ctx.lineTo(x, chartArea.bottom); ctx.stroke();
        }
        for (let y = chartArea.top; y <= chartArea.bottom; y += 20) {
          ctx.beginPath(); ctx.moveTo(chartArea.left, y); ctx.lineTo(chartArea.right, y); ctx.stroke();
        }
        ctx.restore();
      }
    }]
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
  if (currentSummary === 'today') {
    daysData = [{ date: dashboardData.simulated_today, stats: dashboardData.stats_today }];
    tagline.textContent = 'FULL DAY AGGREGATE: TODAY';
  } else if (currentSummary === 'yesterday') {
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
    container.style.gridTemplateColumns = 'repeat(3, 1fr)';
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

function applyCustomRange() {
  const startVal = document.getElementById('custom-start').value;
  const endVal = document.getElementById('custom-end').value;
  
  if (!startVal || !endVal) {
    alert("PLEASE SELECT BOTH START AND END TIMES.");
    return;
  }
  if (startVal >= endVal) {
    alert("START TIME MUST BE BEFORE END TIME.");
    return;
  }
  
  document.querySelectorAll('#time-toggles button').forEach(b => b.classList.remove('active'));
  currentTimeframe = 'custom';
  renderChart();
}

async function updateSimDate() {
  const date = document.getElementById('sim-date').value;
  await fetch('/api/set-today', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date, mode: appMode })
  });
  lastDashboardHash = '';
  fetchDashboard(true);
}

async function loadSettings() {
  try {
    const res = await fetch('/api/settings?mode=' + appMode + '&_t=' + Date.now());
    const data = await res.json();
    const select = document.getElementById('csv-file-select');
    if (data.csv_files && data.csv_files.length) {
      select.innerHTML = data.csv_files.map(f => `<option value="${f}">${f}</option>`).join('');
    } else {
      select.innerHTML = '<option value="">NO CSV FILES</option>';
    }
  } catch (e) {}
}

async function loadSelectedCSV() {
  const filename = document.getElementById('csv-file-select').value;
  const statusEl = document.getElementById('csv-status');
  if (!filename || filename === 'NO CSV FILES') return;
  statusEl.textContent = "LOADING...";
  try {
    const res = await fetch('/api/load-csv', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({filename, clear_existing: true, mode: 'replay'}) });
    const data = await res.json();
    if (data.error) statusEl.textContent = `ERR: ${data.error}`;
    else { statusEl.textContent = `OK: ${data.inserted} ROWS`; lastDashboardHash = ''; fetchDashboard(true); }
  } catch (e) { statusEl.textContent = "ERR: NETWORK"; }
  setTimeout(() => statusEl.textContent = "", 5000);
}

async function resetRelayMetrics() {
  await fetch('/api/reset-relay-metrics', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({mode: appMode}) });
  lastDashboardHash = '';
  fetchDashboard(true);
}

async function clearReplayDB() {
  if(!confirm("Clear all data in REPLAY database?")) return;
  await fetch('/api/clear-replay', { method: 'POST' });
  lastDashboardHash = '';
  fetchDashboard(true);
}

// Live Clock Update
function updateLiveClock() {
  const now = new Date();
  document.getElementById('live-clock').textContent = now.toLocaleTimeString('en-US', {hour12: false});
  
  const dot = document.querySelector('.status-dot');
  const liveText = document.getElementById('live-text');
  
  if (dashboardData.relay_status && dashboardData.relay_status.last_contact) {
    const lastContactMs = new Date(dashboardData.relay_status.last_contact).getTime();
    const diffSeconds = (now.getTime() - lastContactMs) / 1000;
    
    if (diffSeconds > 60) {
      liveText.textContent = "RX: WAIT";
      if (dot) dot.classList.remove('active');
    } else {
      liveText.textContent = "RX: OK";
      if (dot) dot.classList.add('active');
    }
  } else {
    liveText.textContent = "RX: WAIT";
    if (dot) dot.classList.remove('active');
  }

  if (dashboardData.relay_status && dashboardData.relay_status.tracking_start) {
    const startMs = new Date(dashboardData.relay_status.tracking_start).getTime();
    const elapsedSec = (now.getTime() - startMs) / 1000;
    const expected = Math.max(1, Math.floor(elapsedSec / 30));
    const received = dashboardData.relay_status.packets_received || 0;
    let loss = ((expected - received) / expected) * 100;
    if (loss < 0) loss = 0;
    if (loss > 100) loss = 100;
    document.getElementById('diag-loss').textContent = loss.toFixed(1) + '%';
  }
}
setInterval(updateLiveClock, 1000);
updateLiveClock();

// Boot up
const bootApp = () => {
  loadSettings();
  fetchDashboard(true);
  setInterval(() => fetchDashboard(false), 5000); 
};

if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(bootApp);
} else {
  window.addEventListener('load', bootApp);
}

</script>
</body>
</html>
"""

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db(LIVE_DB_PATH)
    if os.path.exists(REPLAY_DB_PATH):
        os.remove(REPLAY_DB_PATH)
    init_db(REPLAY_DB_PATH)
    os.makedirs(os.path.join(os.path.dirname(__file__), "archive"), exist_ok=True)
    print("=" * 60)
    print("  Weather Station Dashboard (V3 - LCD Theme)")
    print("  http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)