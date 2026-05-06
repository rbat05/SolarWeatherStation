# Solar Weather Station - Relay Node

## Overview
The Relay code acts as the crucial bridge between the remote, low-power Weather Station and the centralized Server/Dashboard. Running on an ESP8266, it sits within the range of both the station's low-power radio (ESP-NOW) and the home's high-power WiFi network.

## Features & Functions
*   **Continuous Listening:** Operates completely awake, utilizing ESP-NOW to constantly listen for incoming, transient data packets broadcasted by the remote weather station.
*   **WiFi Forwarding:** Establishes and maintains a connection to the local WiFi network, taking the incoming ESP-NOW string and forwarding it to the Dashboard's `/ingest` API endpoint via HTTP POST requests.
*   **Health Dashboard Server:** Hosts a lightweight web server on port 80 displaying real-time diagnostics, including uptime, WiFi RSSI, rolling packet loss percentage, and offline buffer status.
*   **Over-The-Air (OTA) Updates:** Supports wireless flashing, allowing you to update the relay's firmware remotely without needing to physically disconnect it.

## Code Outcome
By decoupling the remote station from the local WiFi network, the Relay allows the station to save massive amounts of battery. The Relay guarantees data packets are successfully transitioned from off-grid radio signals to standard web traffic.

## Hardware & Software Safety Features
Because the Relay serves as a single point of failure for data ingestion, it includes robust fault-tolerance mechanisms:

1.  **Offline Buffering:** If the home WiFi drops or the backend Flask server restarts, the Relay does not discard incoming data. It stores up to 100 missed packets in an in-memory string array buffer.
2.  **Rate-Limited Backfill:** Once the server connection is re-established, the Relay pushes the buffered backlog using a rate-limited retry interval (e.g., 5 seconds) to prevent overwhelming the server with a massive burst of HTTP requests.
3.  **Non-Blocking Architecture:** Uses `millis()`-based timing instead of `delay()` for all primary loop operations. This ensures that a stalled HTTP request or a slow WiFi reconnection attempt never blocks the ESP-NOW callback, guaranteeing it never misses a radio packet from the outdoor station.
4.  **Auto-Reconnection:** Built-in WiFi fallback routines automatically negotiate reconnections if the primary network drops out.