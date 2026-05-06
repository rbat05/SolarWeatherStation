# Solar Weather Station - Dashboard

## Overview
The Dashboard code provides a visually striking, Retro Commercial LCD-themed web interface and a robust Python Flask backend to serve as the central hub for your Solar Weather Station. It receives incoming telemetry via HTTP POST, stores the data locally in an SQLite database, archives historical readings, and presents everything in a highly interactive, at-a-glance format.

## Features & Functions
*   **Flask Web Server & API:** Listens on `/ingest` for JSON or CSV formatted POST requests sent by the Relay node, validating and parsing the payload.
*   **Dual-Database Architecture:** Maintains a `weather.db` for live operational data and a separate `replay.db` for isolated historical analysis, ensuring the live data stream is never interrupted.
*   **Auto-Archival System:** Automatically prunes live database entries older than 7 days to prevent bloat, appending all raw incoming data to permanent daily `.csv` files inside the `archive` directory.
*   **External API Integration:** Fetches comparative weather metrics in real-time from the Open-Meteo API (Auckland Metro) to provide a local vs. regional analysis.

## Code Outcome
A complete, self-hosted web dashboard that requires no external cloud services to operate. It provides deep analytical tools for micro-climate data while maintaining a uniquely stylized, immersive user experience.

## Usability & Dashboard Interface

The dashboard is designed entirely around an aesthetic "Commercial Dot-Matrix LCD" theme. It prioritizes clarity, high contrast, and at-a-glance readability using a bespoke green-and-black color palette.

### Operational Modes
*   **LIVE Mode:** The default, real-time state. The dashboard automatically polls the backend every 5 seconds, pulling the absolute latest data. The UI displays real-time health badges (`RX: OK` or `RX: WAIT`) and updates the hero readouts instantaneously when the relay pushes a new packet.
*   **REPLAY Mode:** A powerful historical analysis tool. The user can select any archived `.csv` file from a dropdown, load it into the temporary replay database, and set a simulated date. The entire dashboard behaves as if that historical day is currently happening, allowing for deep-dive investigations into past weather events using a Custom Time Range filter.

### Displayed Metrics & Readouts
*   **Hero Readouts:**
    *   **Temperature (°C):** Features a massive digital readout with trend indicators (▲/≈/▼) showing if the temperature is rising, falling, or stable compared to the last hour. Includes daily Min/Max values.
    *   **Relative Humidity (%):** Includes visual segment thresholds indicating whether the air is `DRY` (<40%), `COMFORT` (40%-60%), or `WET` (>60%).
    *   **Absolute Pressure (hPa):** Monitors barometric pressure with rapid change indicators to help predict incoming weather fronts.
    *   **Battery Level (%):** A visual fill-bar representing the remote solar station's Li-Po battery charge, including a flashing `LOW!` warning segment if it drops below 20%.

### Interactive Charting
Powered by Chart.js, the main graph renders a strict dot-matrix style line chart (using straight lines and square points) with an animated radar-sweep effect sweeping across the canvas.
*   **Timeframes:** Users can pivot between 1H, 3H, 12H, 24H, 72H, and 7D views.
*   **Dynamic Gap Visualization:** If the weather station goes offline, the chart mathematically detects the missing time buckets. Instead of connecting unrelated data points, it seamlessly breaks the solid line, rendering a transparent, dashed "gap" line so the user knows exactly when data was lost.

### Summaries & Diagnostics
*   **Live Comparison:** The summary panel displays a side-by-side table comparing the local station's data directly against the regional Open-Meteo API, calculating the exact numerical difference.
*   **Aggregate Data:** Users can tab through yesterday, the last 3 days, and the last 7 days to view automatically calculated Highs, Lows, and Averages across all metrics.
*   **System Diagnostics Panel:** A collapsible menu dedicated to hardware health. It displays the timestamp of the last contact, raw payload strings, HTTP response codes, total packets received, and a calculated Packet Loss percentage.