#!/usr/bin/env python3
"""
Weather Station Dashboard
Receives data from weather station via HTTP POST,
stores in SQLite, and serves a web dashboard.
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
                day_date TEXT NOT NULL,  -- YYYY-MM-DD for easy grouping
                temperature REAL,
                humidity REAL,
                pressure REAL,
                battery_voltage REAL,
                battery_percent REAL,
                source TEXT DEFAULT 'live'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_day_date ON readings(day_date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON readings(timestamp)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Default: today is actual today
        result = conn.execute("SELECT value FROM settings WHERE key='simulated_today'").fetchone()
        if not result:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('simulated_today', ?)",
                (date.today().isoformat(),)
            )
        conn.commit()

# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_reading_line(line: str, source: str = "live") -> dict | None:
    """Parse a CSV line in format: Day DD/MM/YYYY - HH:MM:SS,temp,hum,pres,volt,pct"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split(",")
    if len(parts) < 6:
        return None
    try:
        # Parse datetime: "Mon 10/02/2025 - 13:38:57"
        dt_str = parts[0].strip()
        # Remove day-of-week prefix
        # Format: "Mon 10/02/2025 - 13:38:57"
        m = re.match(r'\w+\s+(\d{2}/\d{2}/\d{4})\s+-\s+(\d{2}:\d{2}:\d{2})', dt_str)
        if not m:
            return None
        date_part = m.group(1)  # DD/MM/YYYY
        time_part = m.group(2)  # HH:MM:SS
        dt = datetime.strptime(f"{date_part} {time_part}", "%d/%m/%Y %H:%M:%S")
        day_date = dt.strftime("%Y-%m-%d")

        return {
            "timestamp": dt.isoformat(),
            "day_date": day_date,
            "temperature": float(parts[1]),
            "humidity": float(parts[2]),
            "pressure": float(parts[3]),
            "battery_voltage": float(parts[4]),
            "battery_percent": float(parts[5]),
            "source": source
        }
    except (ValueError, IndexError):
        return None

def get_simulated_today() -> str:
    """Returns the 'today' date string (YYYY-MM-DD) used for simulation."""
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='simulated_today'").fetchone()
        return row["value"] if row else date.today().isoformat()

def set_simulated_today(day_str: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('simulated_today', ?)",
            (day_str,)
        )
        conn.commit()

def stats_for_day(day_date: str) -> dict:
    """Returns hi/low/avg/count for a given YYYY-MM-DD."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                MIN(temperature) as temp_low,
                MAX(temperature) as temp_high,
                AVG(temperature) as temp_avg,
                MIN(humidity) as hum_low,
                MAX(humidity) as hum_high,
                AVG(humidity) as hum_avg,
                MIN(pressure) as pres_low,
                MAX(pressure) as pres_high,
                AVG(pressure) as pres_avg,
                COUNT(*) as count
            FROM readings WHERE day_date = ?
        """, (day_date,)).fetchone()
        if row and row["count"] > 0:
            return dict(row)
        return {}

def readings_for_day(day_date: str) -> list:
    """Returns all readings for a given YYYY-MM-DD as list of dicts."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM readings WHERE day_date = ? ORDER BY timestamp ASC",
            (day_date,)
        ).fetchall()
        return [dict(r) for r in rows]

def readings_for_range(start_date: str, end_date: str) -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM readings WHERE day_date >= ? AND day_date <= ? ORDER BY timestamp ASC",
            (start_date, end_date)
        ).fetchall()
        return [dict(r) for r in rows]

def latest_reading() -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

def days_with_data(n_days: int, today_str: str) -> list[str]:
    """Return list of YYYY-MM-DD strings for the last n_days ending at today."""
    today = datetime.strptime(today_str, "%Y-%m-%d").date()
    return [(today - timedelta(days=i)).isoformat() for i in range(n_days - 1, -1, -1)]

# ─── MetService Integration ───────────────────────────────────────────────────

def fetch_metservice_current(location: str = "auckland") -> dict | None:
    """
    Attempts to fetch current conditions from Open-Meteo (free, no key needed).
    Defaults to Auckland, NZ.
    """
    # Location coords mapping
    locations = {
        "wellington": (-41.2865, 174.7762),
        "auckland": (-36.8485, 174.7633),
        "christchurch": (-43.5321, 172.6362),
        "hamilton": (-37.7870, 175.2793),
    }
    lat, lon = locations.get(location.lower(), locations["auckland"])
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m"
            f"&timezone=Pacific/Auckland"
        )
        resp = requests.get(url, timeout=5)
        data = resp.json()
        cur = data.get("current", {})
        return {
            "temperature": cur.get("temperature_2m"),
            "humidity": cur.get("relative_humidity_2m"),
            "pressure": cur.get("surface_pressure"),
            "wind_speed": cur.get("wind_speed_10m"),
            "location": location.title(),
            "fetched_at": datetime.now().isoformat()
        }
    except Exception:
        return None

# ─── Routes: Data Ingest ──────────────────────────────────────────────────────

@app.route("/ingest", methods=["POST"])
def ingest():
    """Receives a single reading from the weather station."""
    data = request.get_data(as_text=True).strip()
    reading = parse_reading_line(data, source="live")
    if not reading:
        # Try JSON
        try:
            reading = request.get_json()
            reading["source"] = "live"
        except Exception:
            return jsonify({"error": "Invalid data format"}), 400

    if not reading:
        return jsonify({"error": "Could not parse reading"}), 400

    with get_db() as conn:
        conn.execute("""
            INSERT INTO readings (timestamp, day_date, temperature, humidity, pressure, battery_voltage, battery_percent, source)
            VALUES (:timestamp, :day_date, :temperature, :humidity, :pressure, :battery_voltage, :battery_percent, :source)
        """, reading)
        conn.commit()

    return jsonify({"status": "ok", "timestamp": reading["timestamp"]}), 201


@app.route("/api/load-csv", methods=["POST"])
def load_csv():
    """
    Loads a CSV file for a given date. Expects JSON: {filename: 'YYYY-MM-DD.csv', clear_existing: bool}
    The file should be in the data/ directory relative to app.py.
    """
    body = request.get_json()
    filename = body.get("filename", "")
    clear_existing = body.get("clear_existing", True)

    # Extract date from filename
    m = re.match(r'(\d{4}-\d{2}-\d{2})\.csv', os.path.basename(filename))
    if not m:
        return jsonify({"error": "Filename must be YYYY-MM-DD.csv"}), 400

    day_date = m.group(1)

    # Look for the file in data/ directory
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    filepath = os.path.join(data_dir, os.path.basename(filename))

    if not os.path.exists(filepath):
        return jsonify({"error": f"File not found: {filepath}"}), 404

    inserted = 0
    errors = 0

    with get_db() as conn:
        if clear_existing:
            conn.execute("DELETE FROM readings WHERE day_date = ? AND source = 'csv'", (day_date,))

        with open(filepath, "r") as f:
            for line in f:
                reading = parse_reading_line(line, source="csv")
                if reading:
                    conn.execute("""
                        INSERT INTO readings (timestamp, day_date, temperature, humidity, pressure, battery_voltage, battery_percent, source)
                        VALUES (:timestamp, :day_date, :temperature, :humidity, :pressure, :battery_voltage, :battery_percent, :source)
                    """, reading)
                    inserted += 1
                else:
                    if line.strip() and not line.startswith("#"):
                        errors += 1

        conn.commit()

    return jsonify({"status": "ok", "day_date": day_date, "inserted": inserted, "errors": errors})


@app.route("/api/set-today", methods=["POST"])
def api_set_today():
    body = request.get_json()
    day_str = body.get("date", "")
    try:
        datetime.strptime(day_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format, use YYYY-MM-DD"}), 400
    set_simulated_today(day_str)
    return jsonify({"status": "ok", "simulated_today": day_str})


# ─── Routes: API Data ─────────────────────────────────────────────────────────

@app.route("/api/today")
def api_today():
    today = get_simulated_today()
    readings = readings_for_day(today)
    stats = stats_for_day(today)
    latest = latest_reading()
    metservice = fetch_metservice_current("auckland")
    return jsonify({
        "date": today,
        "latest": latest,
        "stats": stats,
        "readings": readings,
        "metservice": metservice
    })

@app.route("/api/yesterday")
def api_yesterday():
    today = get_simulated_today()
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify({
        "date": yesterday,
        "stats": stats_for_day(yesterday),
        "readings": readings_for_day(yesterday)
    })

@app.route("/api/last3days")
def api_last3days():
    today = get_simulated_today()
    days = days_with_data(3, today)
    return jsonify({
        "dates": days,
        "days": {d: {"stats": stats_for_day(d), "readings": readings_for_day(d)} for d in days}
    })

@app.route("/api/lastweek")
def api_lastweek():
    today = get_simulated_today()
    days = days_with_data(7, today)
    return jsonify({
        "dates": days,
        "days": {d: {"stats": stats_for_day(d)} for d in days},
        "readings": readings_for_range(days[0], days[-1])
    })

@app.route("/api/settings")
def api_settings():
    today = get_simulated_today()
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    csv_files = []
    if os.path.exists(data_dir):
        csv_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".csv")], reverse=True)
    return jsonify({
        "simulated_today": today,
        "csv_files": csv_files
    })

@app.route("/api/generate-dummy-data", methods=["POST"])
def generate_dummy_data():
    """Generates dummy CSV files for testing."""
    import random
    import math

    body = request.get_json() or {}
    num_days = body.get("days", 7)
    end_date = date.today()

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)

    files_created = []

    for day_offset in range(num_days - 1, -1, -1):
        target_date = end_date - timedelta(days=day_offset)
        filename = f"{target_date.strftime('%Y-%m-%d')}.csv"
        filepath = os.path.join(data_dir, filename)

        # Base conditions with some daily variation
        base_temp = 18 + 5 * math.sin(day_offset * 0.5) + random.uniform(-2, 2)
        base_hum = 65 + 10 * math.cos(day_offset * 0.3) + random.uniform(-5, 5)
        base_pres = 1013 + 5 * math.sin(day_offset * 0.2) + random.uniform(-3, 3)

        with open(filepath, "w") as f:
            f.write("# Weather Station Data - Dummy\n")
            # Reading every 30 seconds from 6:00 AM to 11:00 PM
            start = datetime.combine(target_date, datetime.min.time()).replace(hour=6, minute=0, second=0)
            end_time = datetime.combine(target_date, datetime.min.time()).replace(hour=23, minute=0, second=0)
            current = start
            temp = base_temp
            hum = base_hum
            pres = base_pres
            voltage = 4.1 + random.uniform(-0.1, 0.1)

            while current <= end_time:
                # Simulate diurnal temperature variation
                hour_factor = math.sin((current.hour - 6) * math.pi / 12)
                temp = base_temp + 4 * hour_factor + random.gauss(0, 0.3)
                hum = max(20, min(100, base_hum - 15 * hour_factor + random.gauss(0, 1)))
                pres = base_pres + random.gauss(0, 0.5)
                voltage = max(3.0, voltage + random.uniform(-0.01, 0.005))
                bat_pct = max(0, min(100, (voltage - 3.0) / (4.2 - 3.0) * 100))

                day_str = current.strftime("%a %d/%m/%Y - %H:%M:%S")
                f.write(f"{day_str},{temp:.2f},{hum:.2f},{pres:.2f},{voltage:.2f},{bat_pct:.2f}\n")
                current += timedelta(seconds=30)

        files_created.append(filename)

    return jsonify({"status": "ok", "files_created": files_created, "data_dir": data_dir})


# ─── Frontend ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


# ─── HTML Template ────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weather Station</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0e17;
    --surface: #111827;
    --surface2: #1a2235;
    --border: #1e2d45;
    --accent: #00d4ff;
    --accent2: #ff6b35;
    --accent3: #7fff6e;
    --text: #e2e8f0;
    --text-dim: #64748b;
    --text-muted: #334155;
    --danger: #ff4757;
    --warn: #ffa502;
    --radius: 10px;
    --mono: 'Share Tech Mono', monospace;
    --sans: 'Syne', sans-serif;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Subtle grid background */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(var(--border) 1px, transparent 1px),
      linear-gradient(90deg, var(--border) 1px, transparent 1px);
    background-size: 40px 40px;
    opacity: 0.3;
    pointer-events: none;
    z-index: 0;
  }

  #app { position: relative; z-index: 1; max-width: 1400px; margin: 0 auto; padding: 24px; }

  /* Header */
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }
  .header-left { display: flex; align-items: center; gap: 16px; }
  .station-icon {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
  }
  .station-title { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
  .station-subtitle { font-size: 11px; color: var(--text-dim); font-family: var(--mono); text-transform: uppercase; letter-spacing: 2px; }
  .header-right { display: flex; align-items: center; gap: 12px; }
  .live-badge {
    display: flex; align-items: center; gap: 6px;
    background: rgba(0, 212, 255, 0.1);
    border: 1px solid var(--accent);
    padding: 4px 10px; border-radius: 20px;
    font-size: 11px; font-family: var(--mono); color: var(--accent);
  }
  .live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--accent);
    animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
  .current-time { font-family: var(--mono); font-size: 13px; color: var(--text-dim); }

  /* Tabs */
  .tabs {
    display: flex; gap: 4px; margin-bottom: 24px;
    background: var(--surface); border-radius: 12px; padding: 4px;
    border: 1px solid var(--border);
  }
  .tab {
    flex: 1; padding: 8px 16px; border-radius: 8px;
    background: none; border: none; color: var(--text-dim);
    font-family: var(--sans); font-size: 13px; font-weight: 600;
    cursor: pointer; transition: all 0.2s; white-space: nowrap;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .tab:hover { color: var(--text); background: var(--surface2); }
  .tab.active { background: var(--accent); color: var(--bg); }
  .tab.settings-tab { background: none; border: 1px solid var(--border); }
  .tab.settings-tab.active { background: var(--accent2); border-color: var(--accent2); color: white; }

  /* Tab panels */
  .panel { display: none; }
  .panel.active { display: block; animation: fadeIn 0.3s ease; }
  @keyframes fadeIn { from{opacity:0;transform:translateY(8px);} to{opacity:1;transform:none;} }

  /* Grid layouts */
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
  .grid-auto { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }

  /* Cards */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
  }
  .card-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 12px;
  }
  .card-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 2px; color: var(--text-dim);
    font-family: var(--mono);
  }

  /* Stat cards */
  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    position: relative;
    overflow: hidden;
  }
  .stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
  }
  .stat-card.temp::before { background: linear-gradient(90deg, var(--accent2), #ff8c69); }
  .stat-card.hum::before { background: linear-gradient(90deg, var(--accent), #0099bb); }
  .stat-card.pres::before { background: linear-gradient(90deg, var(--accent3), #44cc33); }
  .stat-card.bat::before { background: linear-gradient(90deg, var(--warn), #ffd43b); }

  .stat-label { font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1.5px; font-family: var(--mono); margin-bottom: 6px; }
  .stat-value { font-size: 32px; font-weight: 800; line-height: 1; font-family: var(--mono); }
  .stat-unit { font-size: 13px; color: var(--text-dim); margin-left: 4px; }
  .stat-meta { margin-top: 8px; font-size: 11px; color: var(--text-dim); font-family: var(--mono); }
  .stat-meta span { color: var(--text); }

  .stat-card.temp .stat-value { color: var(--accent2); }
  .stat-card.hum .stat-value { color: var(--accent); }
  .stat-card.pres .stat-value { color: var(--accent3); }
  .stat-card.bat .stat-value { color: var(--warn); }

  /* Hi/Low/Avg row */
  .hla-row {
    display: grid; grid-template-columns: 1fr 1fr 1fr;
    gap: 8px; margin-bottom: 16px;
  }
  .hla-card {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 12px;
  }
  .hla-label { font-size: 9px; text-transform: uppercase; letter-spacing: 2px; color: var(--text-dim); font-family: var(--mono); margin-bottom: 4px; }
  .hla-value { font-size: 20px; font-weight: 700; font-family: var(--mono); }
  .hla-high { color: var(--accent2); }
  .hla-low { color: var(--accent); }
  .hla-avg { color: var(--accent3); }

  /* Charts */
  .chart-container { position: relative; height: 200px; }
  .chart-container.tall { height: 280px; }

  /* MetService comparison */
  .compare-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 0; border: 1px solid var(--border); border-radius: var(--radius);
    overflow: hidden;
  }
  .compare-col {
    padding: 16px;
    background: var(--surface);
  }
  .compare-col:first-child { border-right: 1px solid var(--border); }
  .compare-title { font-size: 10px; text-transform: uppercase; letter-spacing: 2px; color: var(--text-dim); font-family: var(--mono); margin-bottom: 12px; }
  .compare-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border); }
  .compare-row:last-child { border-bottom: none; }
  .compare-key { font-size: 12px; color: var(--text-dim); }
  .compare-val { font-size: 14px; font-weight: 700; font-family: var(--mono); }
  .delta { font-size: 11px; padding: 2px 6px; border-radius: 4px; font-family: var(--mono); }
  .delta.pos { background: rgba(255,107,53,0.2); color: var(--accent2); }
  .delta.neg { background: rgba(0,212,255,0.2); color: var(--accent); }
  .delta.zero { background: rgba(127,255,110,0.2); color: var(--accent3); }

  /* Day summary cards */
  .day-summary {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
  }
  .day-date-label { font-size: 16px; font-weight: 700; margin-bottom: 12px; }
  .day-stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .day-stat { text-align: center; }
  .day-stat-name { font-size: 9px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-dim); font-family: var(--mono); }
  .day-stat-vals { margin-top: 4px; }
  .day-stat-val { font-size: 13px; font-family: var(--mono); font-weight: 600; }

  /* Settings panel */
  .settings-section { margin-bottom: 24px; }
  .settings-title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-dim); font-family: var(--mono); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
  .form-row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
  .form-label { font-size: 12px; color: var(--text-dim); min-width: 120px; }
  input[type="text"], input[type="date"], select {
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--text); padding: 8px 12px; border-radius: 6px;
    font-family: var(--mono); font-size: 13px; outline: none;
  }
  input[type="text"]:focus, input[type="date"]:focus, select:focus { border-color: var(--accent); }
  .btn {
    padding: 8px 16px; border-radius: 6px; border: none;
    font-family: var(--sans); font-size: 12px; font-weight: 700;
    cursor: pointer; transition: all 0.2s; text-transform: uppercase; letter-spacing: 0.5px;
  }
  .btn-primary { background: var(--accent); color: var(--bg); }
  .btn-primary:hover { opacity: 0.85; }
  .btn-secondary { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
  .btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
  .btn-warning { background: var(--accent2); color: white; }
  .btn-warning:hover { opacity: 0.85; }
  .btn-success { background: var(--accent3); color: var(--bg); }

  /* File list */
  .file-list { display: flex; flex-direction: column; gap: 6px; }
  .file-item {
    display: flex; align-items: center; justify-content: space-between;
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 6px; padding: 8px 12px;
  }
  .file-name { font-family: var(--mono); font-size: 13px; }
  .file-date { font-size: 11px; color: var(--text-dim); }

  /* Status message */
  .status-msg {
    padding: 10px 14px; border-radius: 6px; font-size: 13px;
    font-family: var(--mono); margin-top: 8px; display: none;
  }
  .status-msg.success { background: rgba(127,255,110,0.1); border: 1px solid var(--accent3); color: var(--accent3); display: block; }
  .status-msg.error { background: rgba(255,71,87,0.1); border: 1px solid var(--danger); color: var(--danger); display: block; }
  .status-msg.info { background: rgba(0,212,255,0.1); border: 1px solid var(--accent); color: var(--accent); display: block; }

  /* Loading state */
  .loading { display: flex; align-items: center; justify-content: center; padding: 60px; color: var(--text-dim); font-family: var(--mono); gap: 10px; }
  .spinner { width: 20px; height: 20px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* No data */
  .no-data { text-align: center; padding: 40px; color: var(--text-dim); font-family: var(--mono); font-size: 13px; }

  /* Timestamp */
  .ts { font-family: var(--mono); font-size: 11px; color: var(--text-dim); }

  /* Battery bar */
  .bat-bar { height: 6px; background: var(--surface2); border-radius: 3px; overflow: hidden; margin-top: 6px; }
  .bat-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }

  /* Section spacing */
  .section { margin-bottom: 20px; }

  /* Week chart section */
  .week-stats-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
    margin-bottom: 16px;
  }
  .week-day-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 8px;
    text-align: center;
  }
  .week-day-name { font-size: 9px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-dim); font-family: var(--mono); }
  .week-day-date { font-size: 10px; font-family: var(--mono); color: var(--text-dim); margin-bottom: 4px; }
  .week-temp-hi { font-size: 14px; font-weight: 700; font-family: var(--mono); color: var(--accent2); }
  .week-temp-lo { font-size: 11px; font-family: var(--mono); color: var(--accent); }

  /* Responsive */
  @media (max-width: 900px) {
    .grid-4 { grid-template-columns: repeat(2, 1fr); }
    .week-stats-row { grid-template-columns: repeat(4, 1fr); }
    .compare-grid { grid-template-columns: 1fr; }
    .compare-col:first-child { border-right: none; border-bottom: 1px solid var(--border); }
  }
  @media (max-width: 600px) {
    .grid-2, .grid-3 { grid-template-columns: 1fr; }
    .tabs { flex-wrap: wrap; }
  }

  .today-label {
    font-family: var(--mono); font-size: 11px; color: var(--accent);
    background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3);
    padding: 3px 8px; border-radius: 4px;
  }
</style>
</head>
<body>
<div id="app">

  <!-- Header -->
  <div class="header">
    <div class="header-left">
      <div class="station-icon">🌡</div>
      <div>
        <div class="station-title">WEATHER STATION</div>
        <div class="station-subtitle">Raspberry Pi Data Logger</div>
      </div>
    </div>
    <div class="header-right">
      <span id="today-display" class="today-label">—</span>
      <div class="live-badge">
        <div class="live-dot"></div>
        <span id="live-status">CONNECTING</span>
      </div>
      <div class="current-time" id="clock">—</div>
    </div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab active" onclick="switchTab('today')">Today</button>
    <button class="tab" onclick="switchTab('yesterday')">Yesterday</button>
    <button class="tab" onclick="switchTab('three')">3 Days</button>
    <button class="tab" onclick="switchTab('week')">7 Days</button>
    <button class="tab settings-tab" onclick="switchTab('settings')">⚙ Settings</button>
  </div>

  <!-- TODAY PANEL -->
  <div id="panel-today" class="panel active">
    <div id="today-content"><div class="loading"><div class="spinner"></div>Loading...</div></div>
  </div>

  <!-- YESTERDAY PANEL -->
  <div id="panel-yesterday" class="panel">
    <div id="yesterday-content"><div class="loading"><div class="spinner"></div>Loading...</div></div>
  </div>

  <!-- 3 DAYS PANEL -->
  <div id="panel-three" class="panel">
    <div id="three-content"><div class="loading"><div class="spinner"></div>Loading...</div></div>
  </div>

  <!-- WEEK PANEL -->
  <div id="panel-week" class="panel">
    <div id="week-content"><div class="loading"><div class="spinner"></div>Loading...</div></div>
  </div>

  <!-- SETTINGS PANEL -->
  <div id="panel-settings" class="panel">
    <div class="settings-section">
      <div class="settings-title">Simulation Controls</div>
      <div class="form-row">
        <div class="form-label">Simulated Today</div>
        <input type="date" id="sim-today-input">
        <button class="btn btn-primary" onclick="setSimulatedToday()">Set Date</button>
        <button class="btn btn-secondary" onclick="setTodayToReal()">Use Real Today</button>
      </div>
      <div id="sim-status" class="status-msg"></div>
    </div>

    <div class="settings-section">
      <div class="settings-title">CSV Data Files</div>
      <div class="form-row">
        <div class="form-label">Load CSV File</div>
        <select id="csv-file-select" style="flex:1;"></select>
        <button class="btn btn-warning" onclick="loadSelectedCSV()">Load</button>
      </div>
      <div id="csv-status" class="status-msg"></div>

      <div style="margin-top:16px;">
        <div style="font-size:11px;color:var(--text-dim);margin-bottom:8px;font-family:var(--mono);">Available CSV files in /data/:</div>
        <div id="file-list" class="file-list"><div class="no-data">No CSV files found</div></div>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-title">Generate Dummy Data</div>
      <p style="font-size:12px;color:var(--text-dim);margin-bottom:12px;font-family:var(--mono);">
        Generates realistic dummy CSV files in the /data/ directory for testing.
      </p>
      <div class="form-row">
        <div class="form-label">Days to Generate</div>
        <input type="text" id="dummy-days" value="7" style="width:80px;">
        <button class="btn btn-success" onclick="generateDummy()">Generate</button>
      </div>
      <div id="dummy-status" class="status-msg"></div>
    </div>

    <div class="settings-section">
      <div class="settings-title">Data Ingestion Endpoint</div>
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:16px;">
        <div class="card-title" style="margin-bottom:8px;">POST to /ingest</div>
        <div style="font-family:var(--mono);font-size:12px;color:var(--accent);">
          Format: Mon 10/02/2025 - 13:38:57,30.46,37.74,1012.07,4.13,98.00
        </div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:8px;font-family:var(--mono);">
          Send HTTP POST with raw CSV line as body. The Pi will auto-receive and store every 30 seconds.
        </div>
      </div>
    </div>
  </div>

</div>

<script>
let activeTab = 'today';
let charts = {};
let refreshInterval = null;

// ─── Clock ────────────────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent = now.toLocaleTimeString('en-NZ', {hour12: false});
}
setInterval(updateClock, 1000);
updateClock();

// ─── Tab Switching ─────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('panel-' + tab).classList.add('active');
  activeTab = tab;
  destroyCharts();
  loadTab(tab);
}

function loadTab(tab) {
  if (tab === 'today') loadToday();
  else if (tab === 'yesterday') loadYesterday();
  else if (tab === 'three') loadThreeDays();
  else if (tab === 'week') loadWeek();
  else if (tab === 'settings') loadSettings();
}

function destroyCharts() {
  Object.values(charts).forEach(c => { try { c.destroy(); } catch(e){} });
  charts = {};
}

// ─── Formatting ────────────────────────────────────────────────────────────────
function fmt(v, decimals=1) { return v != null ? (+v).toFixed(decimals) : '—'; }
function fmtDate(d) {
  if (!d) return '—';
  const dt = new Date(d + 'T00:00:00');
  return dt.toLocaleDateString('en-NZ', {weekday:'short', day:'numeric', month:'short', year:'numeric'});
}
function fmtTime(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleTimeString('en-NZ', {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false});
}
function batColor(pct) {
  if (pct >= 60) return 'var(--accent3)';
  if (pct >= 30) return 'var(--warn)';
  return 'var(--danger)';
}
function delta(a, b) {
  if (a == null || b == null) return '';
  const d = a - b;
  const cls = d > 0.2 ? 'pos' : d < -0.2 ? 'neg' : 'zero';
  const sign = d > 0 ? '+' : '';
  return `<span class="delta ${cls}">${sign}${d.toFixed(1)}</span>`;
}

// ─── Chart Builder ─────────────────────────────────────────────────────────────
function buildLineChart(canvasId, labels, datasets, options={}) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const c = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 400 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: datasets.length > 1, labels: { color: '#64748b', font: { family: 'Share Tech Mono', size: 11 }, boxWidth: 12, padding: 16 } },
        tooltip: {
          backgroundColor: '#111827', borderColor: '#1e2d45', borderWidth: 1,
          titleColor: '#e2e8f0', bodyColor: '#94a3b8',
          titleFont: { family: 'Share Tech Mono' }, bodyFont: { family: 'Share Tech Mono', size: 11 },
          callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(2) : '—'}${options.unit||''}` }
        }
      },
      scales: {
        x: {
          ticks: { color: '#334155', font: { family: 'Share Tech Mono', size: 10 }, maxTicksLimit: 12, maxRotation: 0 },
          grid: { color: '#1e2d45' }
        },
        y: {
          ticks: { color: '#334155', font: { family: 'Share Tech Mono', size: 10 } },
          grid: { color: '#1e2d45' },
          ...options.yScale
        }
      }
    }
  });
  charts[canvasId] = c;
}

function buildBarChart(canvasId, labels, data, color, unit='') {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const c = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data, backgroundColor: color + '66', borderColor: color, borderWidth: 1, borderRadius: 3 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { bodyFont: { family: 'Share Tech Mono' }, callbacks: { label: ctx => ` ${ctx.parsed.y.toFixed(1)}${unit}` } } },
      scales: {
        x: { ticks: { color: '#334155', font: { family: 'Share Tech Mono', size: 10 } }, grid: { color: '#1e2d45' } },
        y: { ticks: { color: '#334155', font: { family: 'Share Tech Mono', size: 10 } }, grid: { color: '#1e2d45' } }
      }
    }
  });
  charts[canvasId] = c;
}

// ─── TODAY ─────────────────────────────────────────────────────────────────────
async function loadToday() {
  try {
    const data = await fetch('/api/today').then(r => r.json());
    document.getElementById('today-display').textContent = fmtDate(data.date);
    const live = data.latest;
    const stats = data.stats;
    const met = data.metservice;
    document.getElementById('live-status').textContent = live ? 'LIVE' : 'NO DATA';

    // Decimate readings for charts (max 300 points)
    let readings = data.readings;
    if (readings.length > 300) {
      const step = Math.ceil(readings.length / 300);
      readings = readings.filter((_, i) => i % step === 0);
    }
    const times = readings.map(r => fmtTime(r.timestamp));
    const temps = readings.map(r => r.temperature);
    const hums = readings.map(r => r.humidity);
    const pres = readings.map(r => r.pressure);

    const batPct = live ? live.battery_percent : null;
    const batVolt = live ? live.battery_voltage : null;

    document.getElementById('today-content').innerHTML = `
      <div class="section">
        <div class="grid-4">
          <div class="stat-card temp">
            <div class="stat-label">Temperature</div>
            <div class="stat-value">${fmt(live?.temperature)}<span class="stat-unit">°C</span></div>
            <div class="stat-meta">Hi <span>${fmt(stats.temp_high)}°C</span> · Lo <span>${fmt(stats.temp_low)}°C</span></div>
          </div>
          <div class="stat-card hum">
            <div class="stat-label">Humidity</div>
            <div class="stat-value">${fmt(live?.humidity)}<span class="stat-unit">%</span></div>
            <div class="stat-meta">Hi <span>${fmt(stats.hum_high)}%</span> · Lo <span>${fmt(stats.hum_low)}%</span></div>
          </div>
          <div class="stat-card pres">
            <div class="stat-label">Pressure</div>
            <div class="stat-value">${fmt(live?.pressure, 0)}<span class="stat-unit">hPa</span></div>
            <div class="stat-meta">Hi <span>${fmt(stats.pres_high, 0)}</span> · Lo <span>${fmt(stats.pres_low, 0)}</span></div>
          </div>
          <div class="stat-card bat">
            <div class="stat-label">Battery</div>
            <div class="stat-value">${fmt(batPct, 0)}<span class="stat-unit">%</span></div>
            <div class="stat-meta"><span>${fmt(batVolt, 2)}V</span></div>
            <div class="bat-bar"><div class="bat-fill" style="width:${batPct||0}%;background:${batColor(batPct||0)};"></div></div>
          </div>
        </div>
        <div class="ts" style="text-align:right;margin-top:-8px;margin-bottom:12px;">Last reading: ${fmtTime(live?.timestamp) || '—'}</div>
      </div>

      <div class="grid-2 section">
        <div class="card">
          <div class="card-header"><span class="card-title">Temperature Today</span><span class="ts">°C</span></div>
          <div class="chart-container"><canvas id="ch-temp-today"></canvas></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Humidity Today</span><span class="ts">%</span></div>
          <div class="chart-container"><canvas id="ch-hum-today"></canvas></div>
        </div>
      </div>

      <div class="card section">
        <div class="card-header"><span class="card-title">Pressure Today</span><span class="ts">hPa</span></div>
        <div class="chart-container"><canvas id="ch-pres-today"></canvas></div>
      </div>

      <div class="section">
        <div class="card-title" style="margin-bottom:12px;">MetService Comparison — Auckland</div>
        ${met ? `
        <div class="compare-grid">
          <div class="compare-col">
            <div class="compare-title">🏠 Station Reading</div>
            <div class="compare-row"><span class="compare-key">Temperature</span><span class="compare-val" style="color:var(--accent2)">${fmt(live?.temperature)}°C</span></div>
            <div class="compare-row"><span class="compare-key">Humidity</span><span class="compare-val" style="color:var(--accent)">${fmt(live?.humidity)}%</span></div>
            <div class="compare-row"><span class="compare-key">Pressure</span><span class="compare-val" style="color:var(--accent3)">${fmt(live?.pressure, 0)} hPa</span></div>
          </div>
          <div class="compare-col">
            <div class="compare-title">🌐 Open-Meteo (Auckland)</div>
            <div class="compare-row">
              <span class="compare-key">Temperature</span>
              <span class="compare-val">${fmt(met.temperature)}°C</span>
              ${delta(live?.temperature, met.temperature)}
            </div>
            <div class="compare-row">
              <span class="compare-key">Humidity</span>
              <span class="compare-val">${fmt(met.humidity)}%</span>
              ${delta(live?.humidity, met.humidity)}
            </div>
            <div class="compare-row">
              <span class="compare-key">Pressure</span>
              <span class="compare-val">${fmt(met.pressure, 0)} hPa</span>
              ${delta(live?.pressure, met.pressure)}
            </div>
          </div>
        </div>
        <div class="ts" style="margin-top:8px;">Fetched: ${met.fetched_at ? new Date(met.fetched_at).toLocaleTimeString('en-NZ') : '—'} · Source: Open-Meteo API</div>
        ` : `<div class="no-data">MetService data unavailable — check internet connection</div>`}
      </div>
    `;

    if (readings.length) {
      buildLineChart('ch-temp-today', times, [{label:'Temp', data:temps, borderColor:'#ff6b35', backgroundColor:'rgba(255,107,53,0.1)', borderWidth:1.5, tension:0.4, pointRadius:0}], {unit:'°C'});
      buildLineChart('ch-hum-today', times, [{label:'Hum', data:hums, borderColor:'#00d4ff', backgroundColor:'rgba(0,212,255,0.1)', borderWidth:1.5, tension:0.4, pointRadius:0}], {unit:'%'});
      buildLineChart('ch-pres-today', times, [{label:'Pressure', data:pres, borderColor:'#7fff6e', backgroundColor:'rgba(127,255,110,0.05)', borderWidth:1.5, tension:0.4, pointRadius:0}], {unit:' hPa'});
    }
  } catch (e) {
    document.getElementById('today-content').innerHTML = `<div class="no-data">Error loading data: ${e.message}</div>`;
  }
}

// ─── YESTERDAY ─────────────────────────────────────────────────────────────────
async function loadYesterday() {
  try {
    const data = await fetch('/api/yesterday').then(r => r.json());
    const s = data.stats;
    let readings = data.readings;
    if (readings.length > 300) {
      const step = Math.ceil(readings.length / 300);
      readings = readings.filter((_, i) => i % step === 0);
    }
    const times = readings.map(r => fmtTime(r.timestamp));

    document.getElementById('yesterday-content').innerHTML = `
      <div class="section">
        <div style="font-size:18px;font-weight:700;margin-bottom:16px;">${fmtDate(data.date)}</div>
        ${s.count ? `
        <div class="grid-3">
          <div class="card">
            <div class="card-title" style="margin-bottom:12px;">Temperature</div>
            <div class="hla-row">
              <div class="hla-card"><div class="hla-label">High</div><div class="hla-value hla-high">${fmt(s.temp_high)}°</div></div>
              <div class="hla-card"><div class="hla-label">Low</div><div class="hla-value hla-low">${fmt(s.temp_low)}°</div></div>
              <div class="hla-card"><div class="hla-label">Avg</div><div class="hla-value hla-avg">${fmt(s.temp_avg)}°</div></div>
            </div>
          </div>
          <div class="card">
            <div class="card-title" style="margin-bottom:12px;">Humidity</div>
            <div class="hla-row">
              <div class="hla-card"><div class="hla-label">High</div><div class="hla-value hla-high">${fmt(s.hum_high)}%</div></div>
              <div class="hla-card"><div class="hla-label">Low</div><div class="hla-value hla-low">${fmt(s.hum_low)}%</div></div>
              <div class="hla-card"><div class="hla-label">Avg</div><div class="hla-value hla-avg">${fmt(s.hum_avg)}%</div></div>
            </div>
          </div>
          <div class="card">
            <div class="card-title" style="margin-bottom:12px;">Pressure</div>
            <div class="hla-row">
              <div class="hla-card"><div class="hla-label">High</div><div class="hla-value hla-high">${fmt(s.pres_high, 0)}</div></div>
              <div class="hla-card"><div class="hla-label">Low</div><div class="hla-value hla-low">${fmt(s.pres_low, 0)}</div></div>
              <div class="hla-card"><div class="hla-label">Avg</div><div class="hla-value hla-avg">${fmt(s.pres_avg, 0)}</div></div>
            </div>
          </div>
        </div>
        <div class="ts" style="margin-bottom:16px;">${s.count} readings</div>
        ` : '<div class="no-data">No data for yesterday</div>'}
      </div>
      ${readings.length ? `
      <div class="grid-2 section">
        <div class="card">
          <div class="card-header"><span class="card-title">Temperature</span></div>
          <div class="chart-container"><canvas id="ch-temp-yd"></canvas></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Humidity</span></div>
          <div class="chart-container"><canvas id="ch-hum-yd"></canvas></div>
        </div>
      </div>
      <div class="card section">
        <div class="card-header"><span class="card-title">Pressure</span></div>
        <div class="chart-container"><canvas id="ch-pres-yd"></canvas></div>
      </div>
      ` : ''}
    `;

    if (readings.length) {
      const times = readings.map(r => fmtTime(r.timestamp));
      buildLineChart('ch-temp-yd', times, [{label:'Temp', data:readings.map(r=>r.temperature), borderColor:'#ff6b35', backgroundColor:'rgba(255,107,53,0.1)', borderWidth:1.5, tension:0.4, pointRadius:0}], {unit:'°C'});
      buildLineChart('ch-hum-yd', times, [{label:'Hum', data:readings.map(r=>r.humidity), borderColor:'#00d4ff', backgroundColor:'rgba(0,212,255,0.1)', borderWidth:1.5, tension:0.4, pointRadius:0}], {unit:'%'});
      buildLineChart('ch-pres-yd', times, [{label:'Pressure', data:readings.map(r=>r.pressure), borderColor:'#7fff6e', backgroundColor:'rgba(127,255,110,0.05)', borderWidth:1.5, tension:0.4, pointRadius:0}], {unit:' hPa'});
    }
  } catch (e) {
    document.getElementById('yesterday-content').innerHTML = `<div class="no-data">Error: ${e.message}</div>`;
  }
}

// ─── 3 DAYS ────────────────────────────────────────────────────────────────────
async function loadThreeDays() {
  try {
    const data = await fetch('/api/last3days').then(r => r.json());
    const days = data.dates;
    let html = '<div class="section"><div class="grid-3">';

    for (const day of days) {
      const s = data.days[day]?.stats || {};
      html += `
        <div class="day-summary">
          <div class="day-date-label">${fmtDate(day)}</div>
          ${s.count ? `
          <div class="hla-row" style="margin-bottom:8px;">
            <div class="hla-card"><div class="hla-label">High</div><div class="hla-value hla-high">${fmt(s.temp_high)}°C</div></div>
            <div class="hla-card"><div class="hla-label">Low</div><div class="hla-value hla-low">${fmt(s.temp_low)}°C</div></div>
            <div class="hla-card"><div class="hla-label">Avg</div><div class="hla-value hla-avg">${fmt(s.temp_avg)}°C</div></div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:8px;">
              <div class="hla-label">Humidity</div>
              <div style="font-family:var(--mono);font-size:12px;margin-top:4px;">
                <span style="color:var(--accent2)">${fmt(s.hum_high)}%</span> /
                <span style="color:var(--accent)">${fmt(s.hum_low)}%</span> /
                <span style="color:var(--accent3)">${fmt(s.hum_avg)}%</span>
              </div>
            </div>
            <div style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:8px;">
              <div class="hla-label">Pressure</div>
              <div style="font-family:var(--mono);font-size:12px;margin-top:4px;">
                <span style="color:var(--accent2)">${fmt(s.pres_high,0)}</span> /
                <span style="color:var(--accent)">${fmt(s.pres_low,0)}</span>
                <span style="color:var(--text-dim);font-size:10px;"> hPa</span>
              </div>
            </div>
          </div>
          <div class="ts" style="margin-top:8px;">${s.count} readings</div>
          ` : '<div class="no-data" style="padding:16px;">No data</div>'}
        </div>
      `;
    }
    html += '</div></div>';

    // Combined chart for all 3 days
    const allReadings = [];
    for (const day of days) {
      allReadings.push(...(data.days[day]?.readings || []));
    }
    allReadings.sort((a,b) => a.timestamp.localeCompare(b.timestamp));

    let decimated = allReadings;
    if (decimated.length > 300) {
      const step = Math.ceil(decimated.length / 300);
      decimated = decimated.filter((_, i) => i % step === 0);
    }

    if (decimated.length) {
      html += `
        <div class="card section">
          <div class="card-header"><span class="card-title">Temperature — 3 Days</span></div>
          <div class="chart-container tall"><canvas id="ch-temp-3d"></canvas></div>
        </div>
        <div class="grid-2 section">
          <div class="card">
            <div class="card-header"><span class="card-title">Humidity</span></div>
            <div class="chart-container"><canvas id="ch-hum-3d"></canvas></div>
          </div>
          <div class="card">
            <div class="card-header"><span class="card-title">Pressure</span></div>
            <div class="chart-container"><canvas id="ch-pres-3d"></canvas></div>
          </div>
        </div>
      `;
    }

    document.getElementById('three-content').innerHTML = html;

    if (decimated.length) {
      const labels = decimated.map(r => {
        const dt = new Date(r.timestamp);
        return dt.toLocaleDateString('en-NZ',{month:'short',day:'numeric'}) + ' ' + dt.toLocaleTimeString('en-NZ',{hour:'2-digit',minute:'2-digit',hour12:false});
      });
      buildLineChart('ch-temp-3d', labels, [{label:'Temp', data:decimated.map(r=>r.temperature), borderColor:'#ff6b35', backgroundColor:'rgba(255,107,53,0.08)', borderWidth:1.5, tension:0.3, pointRadius:0}], {unit:'°C'});
      buildLineChart('ch-hum-3d', labels, [{label:'Humidity', data:decimated.map(r=>r.humidity), borderColor:'#00d4ff', backgroundColor:'rgba(0,212,255,0.08)', borderWidth:1.5, tension:0.3, pointRadius:0}], {unit:'%'});
      buildLineChart('ch-pres-3d', labels, [{label:'Pressure', data:decimated.map(r=>r.pressure), borderColor:'#7fff6e', backgroundColor:'rgba(127,255,110,0.05)', borderWidth:1.5, tension:0.3, pointRadius:0}], {unit:' hPa'});
    }
  } catch (e) {
    document.getElementById('three-content').innerHTML = `<div class="no-data">Error: ${e.message}</div>`;
  }
}

// ─── WEEK ──────────────────────────────────────────────────────────────────────
async function loadWeek() {
  try {
    const data = await fetch('/api/lastweek').then(r => r.json());
    const days = data.dates;

    let weekCards = '<div class="week-stats-row">';
    for (const day of days) {
      const s = data.days[day]?.stats || {};
      const dt = new Date(day + 'T00:00:00');
      const dayName = dt.toLocaleDateString('en-NZ',{weekday:'short'});
      const dayNum = dt.toLocaleDateString('en-NZ',{day:'numeric',month:'short'});
      weekCards += `
        <div class="week-day-card">
          <div class="week-day-name">${dayName}</div>
          <div class="week-day-date">${dayNum}</div>
          ${s.count ? `
            <div class="week-temp-hi">${fmt(s.temp_high)}°</div>
            <div class="week-temp-lo">${fmt(s.temp_low)}°</div>
          ` : '<div style="font-size:10px;color:var(--text-muted);font-family:var(--mono);">—</div>'}
        </div>
      `;
    }
    weekCards += '</div>';

    // Bar charts: daily hi/lo/avg
    const validDays = days.filter(d => data.days[d]?.stats?.count);
    const dayLabels = validDays.map(d => {
      const dt = new Date(d + 'T00:00:00');
      return dt.toLocaleDateString('en-NZ',{weekday:'short', day:'numeric'});
    });

    // All readings for sparklines
    let allReadings = data.readings || [];
    allReadings.sort((a,b) => a.timestamp.localeCompare(b.timestamp));
    let decimated = allReadings;
    if (decimated.length > 400) {
      const step = Math.ceil(decimated.length / 400);
      decimated = decimated.filter((_, i) => i % step === 0);
    }

    document.getElementById('week-content').innerHTML = `
      <div class="section">${weekCards}</div>

      ${validDays.length ? `
      <div class="grid-2 section">
        <div class="card">
          <div class="card-header"><span class="card-title">Daily Temp Hi/Lo/Avg</span></div>
          <div class="chart-container"><canvas id="ch-temp-wk"></canvas></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Daily Humidity Hi/Lo/Avg</span></div>
          <div class="chart-container"><canvas id="ch-hum-wk"></canvas></div>
        </div>
      </div>
      <div class="card section">
        <div class="card-header"><span class="card-title">Pressure — 7 Days</span></div>
        <div class="chart-container tall"><canvas id="ch-pres-wk"></canvas></div>
      </div>
      ` : '<div class="no-data">No data available for the past 7 days</div>'}
    `;

    if (validDays.length) {
      const hiTemps = validDays.map(d => data.days[d]?.stats?.temp_high);
      const loTemps = validDays.map(d => data.days[d]?.stats?.temp_low);
      const avgTemps = validDays.map(d => data.days[d]?.stats?.temp_avg);
      const hiHum = validDays.map(d => data.days[d]?.stats?.hum_high);
      const loHum = validDays.map(d => data.days[d]?.stats?.hum_low);
      const avgHum = validDays.map(d => data.days[d]?.stats?.hum_avg);

      buildLineChart('ch-temp-wk', dayLabels, [
        {label:'High', data:hiTemps, borderColor:'#ff6b35', backgroundColor:'rgba(255,107,53,0.1)', borderWidth:2, tension:0.4, pointRadius:4, pointBackgroundColor:'#ff6b35'},
        {label:'Avg', data:avgTemps, borderColor:'#7fff6e', backgroundColor:'rgba(127,255,110,0.05)', borderWidth:1.5, tension:0.4, pointRadius:3, borderDash:[4,2]},
        {label:'Low', data:loTemps, borderColor:'#00d4ff', backgroundColor:'rgba(0,212,255,0.05)', borderWidth:2, tension:0.4, pointRadius:4, pointBackgroundColor:'#00d4ff'},
      ], {unit:'°C'});

      buildLineChart('ch-hum-wk', dayLabels, [
        {label:'High', data:hiHum, borderColor:'#ff6b35', backgroundColor:'rgba(255,107,53,0.05)', borderWidth:2, tension:0.4, pointRadius:4},
        {label:'Avg', data:avgHum, borderColor:'#7fff6e', backgroundColor:'rgba(127,255,110,0.05)', borderWidth:1.5, tension:0.4, pointRadius:3, borderDash:[4,2]},
        {label:'Low', data:loHum, borderColor:'#00d4ff', backgroundColor:'rgba(0,212,255,0.05)', borderWidth:2, tension:0.4, pointRadius:4},
      ], {unit:'%'});

      if (decimated.length) {
        const presLabels = decimated.map(r => {
          const dt = new Date(r.timestamp);
          return dt.toLocaleDateString('en-NZ',{month:'short',day:'numeric'}) + ' ' + dt.toLocaleTimeString('en-NZ',{hour:'2-digit',minute:'2-digit',hour12:false});
        });
        buildLineChart('ch-pres-wk', presLabels, [
          {label:'Pressure', data:decimated.map(r=>r.pressure), borderColor:'#7fff6e', backgroundColor:'rgba(127,255,110,0.05)', borderWidth:1.5, tension:0.3, pointRadius:0}
        ], {unit:' hPa'});
      }
    }
  } catch(e) {
    document.getElementById('week-content').innerHTML = `<div class="no-data">Error: ${e.message}</div>`;
  }
}

// ─── SETTINGS ──────────────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    const data = await fetch('/api/settings').then(r => r.json());
    document.getElementById('sim-today-input').value = data.simulated_today;

    const select = document.getElementById('csv-file-select');
    select.innerHTML = data.csv_files.map(f => `<option value="${f}">${f}</option>`).join('');
    if (!data.csv_files.length) select.innerHTML = '<option>No CSV files found</option>';

    const fileList = document.getElementById('file-list');
    if (data.csv_files.length) {
      fileList.innerHTML = data.csv_files.map(f => `
        <div class="file-item">
          <span class="file-name">${f}</span>
          <button class="btn btn-secondary" style="padding:4px 10px;font-size:11px;" onclick="quickLoad('${f}')">Load</button>
        </div>
      `).join('');
    }
  } catch(e) {}
}

async function setSimulatedToday() {
  const d = document.getElementById('sim-today-input').value;
  if (!d) return;
  const res = await fetch('/api/set-today', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({date:d})});
  const data = await res.json();
  showStatus('sim-status', data.error ? data.error : `Simulated today set to: ${data.simulated_today}`, data.error ? 'error' : 'success');
  document.getElementById('today-display').textContent = fmtDate(d);
  destroyCharts();
  if (activeTab !== 'settings') loadTab(activeTab);
}

function setTodayToReal() {
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('sim-today-input').value = today;
  setSimulatedToday();
}

async function loadSelectedCSV() {
  const filename = document.getElementById('csv-file-select').value;
  if (!filename || filename === 'No CSV files found') return;
  const res = await fetch('/api/load-csv', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({filename, clear_existing:true})});
  const data = await res.json();
  if (data.error) {
    showStatus('csv-status', `Error: ${data.error}`, 'error');
  } else {
    showStatus('csv-status', `Loaded ${data.inserted} readings for ${data.day_date} (${data.errors} errors)`, 'success');
    destroyCharts();
    if (activeTab !== 'settings') loadTab(activeTab);
  }
}

async function quickLoad(filename) {
  const res = await fetch('/api/load-csv', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({filename, clear_existing:true})});
  const data = await res.json();
  if (data.error) {
    showStatus('csv-status', `Error: ${data.error}`, 'error');
  } else {
    showStatus('csv-status', `Loaded ${data.inserted} readings for ${data.day_date}`, 'success');
  }
}

async function generateDummy() {
  const days = parseInt(document.getElementById('dummy-days').value) || 7;
  showStatus('dummy-status', 'Generating...', 'info');
  const res = await fetch('/api/generate-dummy-data', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({days})});
  const data = await res.json();
  if (data.error) {
    showStatus('dummy-status', `Error: ${data.error}`, 'error');
  } else {
    showStatus('dummy-status', `Generated ${data.files_created.length} files in ${data.data_dir}`, 'success');
    loadSettings();
  }
}

function showStatus(id, msg, type) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.className = `status-msg ${type}`;
  setTimeout(() => { el.className = 'status-msg'; }, 5000);
}

// ─── Init & Auto-refresh ───────────────────────────────────────────────────────
loadToday();
setInterval(() => {
  if (activeTab === 'today') loadToday();
}, 30000); // refresh every 30s
</script>
</body>
</html>
"""


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    print("=" * 60)
    print("  Weather Station Dashboard")
    print("  http://localhost:5000")
    print("  POST readings to: http://localhost:5000/ingest")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
