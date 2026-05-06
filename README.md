# SolarWeatherStation
An end-to-end, off-grid IoT environmental telemetry system featuring custom hardware, low-power RF bridging, and a retro LCD-themed web dashboard.

![Project Status](https://img.shields.io/badge/status-in--progress-yellow)
![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Platform: ESP32](https://img.shields.io/badge/platform-ESP32-blue)
![Platform: ESP8266](https://img.shields.io/badge/platform-ESP8266-blue)
![Framework: Arduino](https://img.shields.io/badge/framework-Arduino-green)
![PlatformIO](https://img.shields.io/badge/built%20with-PlatformIO-orange)
![Last Commit](https://img.shields.io/github/last-commit/rbat05/SolarWeatherStation)

<p align="center">
*(ADD HERO PROJECT IMAGE HERE LATER)*
</p>

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Performance](#performance)
4. [Design Showcase](#design-showcase)
5. [Bill of Materials](#bill-of-materials)
6. [System Architecture](#system-architecture)
7. [Firmware & Code](#firmware--code)
8. [3D-Printed Parts](#3d-printed-parts)

---

## 1. Overview
The **Solar Weather Station** is a completely custom-engineered, three-tier IoT ecosystem designed to capture, transmit, and visualize highly accurate micro-climate data. 

Operating entirely off-grid, the remote sensor node utilizes solar power and aggressive deep-sleep optimizations to monitor environmental conditions indefinitely. To bypass the extreme battery drain of standard WiFi, it broadcasts lightweight packets via ESP-NOW to a continuously powered indoor Relay node. This Relay acts as a bridge, forwarding the data into a local Python Flask server where it is logged, archived, and displayed on a visually striking, retro-commercial LCD-style dashboard.

## 2. Features
* **100% Off-Grid Operation:** Powered by a localized solar charging circuit and Li-Po battery.
* **Decoupled RF Architecture:** Uses a low-latency, low-power ESP-NOW to WiFi bridge, saving massive amounts of battery life compared to direct-to-router connections.
* **Bulletproof Failsafes:** Features hardware brownout bypassing, local SD card data logging, offline memory buffering (RTC memory), and relay rate-limited backfilling so data is never lost during network dropouts.
* **Retro LCD Dashboard:** A beautiful, responsive, bespoke green-and-black dot-matrix web interface built with pure HTML/JS, Flask, and SQLite.
* **Historical Replay Engine:** A dual-database architecture allows you to dynamically load archived CSV data into a sandbox database to "replay" historical weather events on the dashboard without interrupting the live data stream.
* **Local vs. Regional Analytics:** Automatically fetches regional telemetry from the Open-Meteo API to compare your micro-climate directly against metropolitan averages.

## 3. Performance
Aggressive power-saving techniques were implemented in the ESP32 C++ firmware. By throttling the clock speed down to 80MHz, actively forcing the WiFi/Bluetooth modems off during boot initialization, and removing parasitic hardware LEDs (like the one on the DS3231 RTC), the remote station achieves incredible efficiency:

* **Average Active Time:** < 8.0 seconds per wake cycle.
* **Average Active Current:** ~60 mA (Peak during SD Write & ESP-NOW transmission).
* **Average Sleep Current:** ~2.5 mA.
* **Weighted Average Draw:** ~4.03 mA over a standard cycle.

This ultra-low consumption allows the station to easily survive extended periods of heavy cloud cover without dropping below critical battery voltages.

## 4. Design Showcase
*(ADD DESIGN IMAGES HERE)*
- Image of the custom PCB routing.
- Image of the assembled Weather Station inside the Stevenson Screen.
- Screenshot of the LCD Dashboard.

## 5. Bill of Materials
### Remote Weather Station
* **Microcontroller:** ESP32 (Throttled to 80MHz)
* **Environmental Sensor:** BME280 (Temperature, Humidity, Absolute Pressure)
* **Real-Time Clock:** DS3231 (Hardware power LED physically removed for power savings)
* **Storage:** MicroSD Card Module (SPI)
* **Power:** Solar Panel, TP4056 (or equivalent) Charge Controller, 3.7v Li-Po/18650 Battery

### Indoor Relay Node
* **Microcontroller:** ESP8266

### Local Server
* **Hardware:** Any local machine (e.g., Raspberry Pi) capable of running Python 3.

## 6. System Architecture
The system is broken into three distinct operational layers:

1. **Layer 1: Edge Telemetry (Weather Station)** 
   Wakes up on an interval timer, samples the BME280 and battery voltage, writes to the local SD card, and fires a rapid ESP-NOW string to the Relay before returning to deep sleep. For a detailed breakdown, see the [Weather Station README](./code/WeatherStationCode/README.md).
2. **Layer 2: Network Bridge (Relay Node)** 
   Stays awake permanently on mains power. Listens for the ESP-NOW MAC address. Upon receiving a packet, it formats it into a JSON payload and executes an HTTP POST request over the home WiFi network. For a detailed breakdown, see the [Relay Node README](./code/RelayCode/README.md).
3. **Layer 3: Data Ingestion & Visualization (Dashboard)** 
   A Python Flask server operating on a local machine. It intercepts the HTTP POST at the `/ingest` endpoint, commits the data to an SQLite database, handles infinite 7-day auto-archiving to CSV, and serves the UI. For a detailed breakdown, see the [Dashboard README](./code/DashboardCode/README.md).

## 7. Firmware & Code
The codebase is heavily modularized across three main directories. Please refer to their individual `README.md` files for deep dives into their logic.

* **`/code/WeatherStationCode`:** 
  C++ (PlatformIO) for the remote ESP32. Handles aggressive power management, hardware watchdog failsafes, I2C/SPI bus management, and RTC memory buffering.
* **`/code/RelayCode`:** 
  C++ (PlatformIO) for the indoor ESP8266. Features a non-blocking `millis()` architecture, in-memory offline packet buffering, auto-WiFi reconnections, and OTA flashing support.
* **`/code/DashboardCode`:** 
  Python/Flask backend and HTML/JS frontend. Handles the API endpoints, Open-Meteo polling, database querying, and the retro Chart.js interactive graph rendering.

## 8. Custom Hardware Integration
### Custom PCB (`/pcb`)
Rather than relying on messy jumper wires and breadboards, the Weather Station relies on a completely custom-designed Printed Circuit Board. This custom PCB integrates the ESP32, charge controllers, and sensor headers into a single, reliable footprint. This minimizes point-of-failure wire disconnects, reduces electrical noise on the I2C/SPI busses, and provides a perfectly dimensioned mounting solution for the 3D-printed case.

### 3D-Printed Parts (`/cad`)
All physical enclosures for the project were custom modeled in CAD to fit the bespoke electronics and withstand the elements.

* **Stevenson Screen (Weather Station):** 
  A classic multi-louvered meteorological enclosure. It is specifically designed to shield the BME280 sensor from direct UV radiation and precipitation while allowing ambient wind/air to freely pass through. This prevents artificial greenhouse heating inside the case, ensuring the temperature readings are a true reflection of the outside air.
* **Low-Profile Relay Case:** 
  This enclosure can be found at [Makerworld](https://makerworld.com/en/models/58547-nodemcu-v2-cp2102-cover#profileId-60347). Credit to Lyron for the original design. A hole was cut onto th etop for the heatsink.
