# Weather Station Dashboard

Flask-based dashboard for the Raspberry Pi weather station.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 in a browser (or Chromium kiosk mode on the Pi).

---

## Data Ingestion

Your weather station sends a POST to `/ingest` every 30 seconds.

**Format (raw body):**
```
Mon 10/02/2025 - 13:38:57,30.46,37.74,1012.07,4.13,98.00
```

**MicroPython / ESP32 example:**
```python
import urequests
data = f"{day_str},{temp:.2f},{hum:.2f},{pres:.2f},{volt:.2f},{pct:.2f}"
urequests.post("http://PI_IP:5000/ingest", data=data)
```

---

## Testing with Dummy Data

1. Open the dashboard → **Settings** tab
2. Click **Generate** to create 7 days of dummy CSV files
3. Set **Simulated Today** to any generated date
4. Use **Load CSV** to load that date's data into the database

CSV files live in `./data/YYYY-MM-DD.csv`.

---

## CSV Format

Filename: `YYYY-MM-DD.csv`

```
# Comments are ignored
Mon 10/02/2025 - 13:38:57,30.46,37.74,1012.07,4.13,98.00
Mon 10/02/2025 - 13:39:27,30.51,37.82,1012.09,4.12,97.80
```

Columns: `timestamp, temperature_C, humidity_%, pressure_hPa, battery_V, battery_%`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Receive a live reading |
| GET | `/api/today` | Today's data + MetService comparison |
| GET | `/api/yesterday` | Yesterday's stats + readings |
| GET | `/api/last3days` | 3-day stats + readings |
| GET | `/api/lastweek` | 7-day stats + all readings |
| GET | `/api/settings` | Current sim date + CSV file list |
| POST | `/api/set-today` | Set simulated today `{"date":"YYYY-MM-DD"}` |
| POST | `/api/load-csv` | Load CSV `{"filename":"YYYY-MM-DD.csv"}` |
| POST | `/api/generate-dummy-data` | Generate test data `{"days":7}` |

---

## Kiosk Mode (Raspberry Pi)

Add to `/etc/rc.local` before `exit 0`:

```bash
# Start dashboard server
cd /home/pi/weather_station && python app.py &

# Launch Chromium in kiosk mode after 5s
sleep 5 && chromium-browser --kiosk --noerrdialogs \
  --disable-infobars http://localhost:5000 &
```

---

## MetService Comparison

Uses the free [Open-Meteo API](https://open-meteo.com/) — no API key required.
Default location: Wellington, NZ.

To change location, edit `fetch_metservice_current()` in `app.py` and add
your coordinates to the `locations` dict.
