# Solar Weather Station - Remote Node

## Overview
The Weather Station code powers the remote, solar-charged ESP32 microcontroller unit responsible for capturing local environmental telemetry. Its primary goal is to operate entirely off-grid, efficiently managing its own power reserves while providing highly accurate, continuous weather data via a BME280 sensor, DS3231 RTC, and local SD card storage.

## Features & Functions
*   **Environmental Telemetry:** Interfaces with a BME280 sensor via custom I2C pins (SDA: 33, SCL: 35) to capture Temperature, Relative Humidity, and Absolute Pressure. The sensor is kept in a low-power "sleep mode" and briefly awoken into "forced mode" just long enough to capture a reading.
*   **Aggressive Power Management:** The ESP32's clock speed is heavily throttled down from 240MHz to 80MHz, and the WiFi/Bluetooth modems are actively forced asleep during boot (`esp32ModemSleep()`) to aggressively shave off milli-amps during the active cycle.
*   **Deep Sleep Cycling:** To conserve battery, the station wakes up every 30 seconds, takes rapid readings, writes to the SD card, transmits the data packet via ESP-NOW, and immediately returns to a low-power deep sleep state. Active time is kept to an absolute minimum (under 8 seconds).
*   **Local SD Card Archival:** Every reading is appended to a local CSV file on an SD card via a custom SPI bus (SCK: 7, MISO: 9, MOSI: 11, CS: 12). If wireless transmission fails, the physical data is completely secure.
*   **RTC Memory Buffering:** The code utilizes the ESP32's `RTC_DATA_ATTR` memory to maintain an offline buffer of up to 10 readings across deep sleep cycles. If the Relay node is unreachable, the station stores the readings and bulk-sends the backlog (oldest first) on the next successful connection.

## Code Outcome
A highly resilient, "deploy-and-forget" weather node that can run indefinitely on solar power, constantly delivering localized weather patterns without human intervention.

## Hardware & Software Safety Features
Because this node is deployed remotely and exposed to the elements, several safety mechanisms have been implemented in the code:

1.  **Manual Brownout Override:** Standard ESP32 hardware brownout detection can sometimes trigger false-positive boot loops on solar setups when the voltage slightly dips during radio spikes. The code intentionally bypasses the internal hardware check (`WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0)`) to ensure the board successfully boots and delegates battery management directly to the firmware logic.
2.  **Infinite Loop Safety Catch:** A failsafe `loopCounter` mechanism exists in the main `loop()` function. Because the execution is entirely handled sequentially in `setup()`, if the main loop accidentally iterates more than 1,000 times, the code mathematically determines the microcontroller is hung/frozen and forcefully throws it back into deep sleep to prevent battery drain.
3.  **Offline Resilience:** The combination of local SD storage and the 10-packet `RTC_DATA_ATTR` buffer ensures that brief networking dropouts, relay reboots, or WiFi outages do not result in permanent data loss. 
4.  **Visual Debugging:** Pin 15 provides physical LED flashes upon boot initialization and successful cycle completion, allowing for on-site visual confirmation of the unit's health without connecting it to a computer.

## Power Consumption & Hardware Notes
Based on a typical solar-assisted Li-Po setup, the system is highly optimized:
*   **Average Active Current:** ~60 mA (including SD write and ESP-NOW WiFi spikes).
*   **Average Sleep Current:** ~2.5 mA.
*   **Weighted Draw:** ~4.03 mA average over a cycle.

**⚠️ CRITICAL HARDWARE WARNING:** 
The DS3231 RTC module contains a surface-mounted power LED. Because the DS3231 is kept constantly powered, this LED single-handedly draws almost as much current as the sleeping ESP32! To achieve proper multi-month battery life, the power LED on the DS3231 breakout board *must* be physically desoldered or destroyed.