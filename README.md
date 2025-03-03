# SolarWeatherStation

A **solar-powered weather station** with an indoor head unit and a web server for displaying real-time weather data. Built using **ESP32** and **ESP8266** platforms with off-the-shelf components, featuring custom power management for self-sufficient operation.

---

## 🌟 Features

### Observations

- 🌡️ Temperature
- 📊 Pressure
- 💧 Humidity
- 🌬️ Wind Speed (**TODO**)
- 🧭 Wind Direction (**TODO**)

### Functionality

- **Self-Sustaining Power System**: Runs completely on solar power during the day and switches to battery power at night or in bad weather.
- **Energy-Efficient Operation**: Reads sensor data, transmits via **ESPNOW**, and then enters deep sleep for 5 minutes.
- **Local & Web-Based Monitoring**: Displays readings on an OLED screen and a web server (local network, working on global access).
- **Data Logging & Analysis**: Stores data on an **SD card** for historical tracking (daily, weekly, monthly statistics).

---

## 🛠️ How It Works

### **External Weather Station**

1. Reads **temperature, pressure, humidity, wind speed, wind direction, and battery telemetry**.
2. Stores data locally on an **SD card**.
3. Sends data to the head unit via **ESPNOW**.
4. Shuts off sensors and enters **deep sleep** for 5 minutes to conserve power.
5. Operates on a **solar-battery hybrid power system**, ensuring continuous operation even during poor weather.

### **Internal Head Unit**

1. Receives data from the weather station.
2. Displays the latest readings on an **OLED screen**.
3. Logs data on an **SD card** (stored efficiently in daily CSV files).
4. Updates a **web server** for remote access to real-time and historical data.

---

## 💾 Code & CAD Models

The repository contains all necessary code and CAD models for building the project. The code for the **external weather station** and the **head unit** is kept separate for easier implementation and modification.

---

## 🔧 Hardware Components

### **External Weather Station**

| Component | Function |
|-----------|----------|
| **ESP-WROOM-32** | Microcontroller for data processing & transmission |
| ESP32 Expansion Board | Simplifies wiring & pin access |
| **BME280** | Temperature, pressure, and humidity sensor |
| **49E Hall Effect Sensor** | Measures wind speed and direction |
| **DS3231 RTC** | Provides accurate timestamps |
| **SD Card Module + Card** | Stores sensor data locally |
| **5V 500mA Solar Panel (2.5W, 130x150mm)** | Powers the station |
| **TP4056 USB-C Charge Module** | Manages battery charging |
| **4000mAh 3.7V Battery** | Stores power for nighttime and cloudy weather |
| **Power Management Circuitry** | Regulates and distributes power |

### **Internal Head Unit**

| Component | Function |
|-----------|----------|
| **ESP8266 + Expansion Board** | Handles display, data logging, and web hosting |
| **SSD1306 OLED Display (128x64)** | Displays real-time weather data |
| **DS3231 RTC** | Provides accurate timestamps |
| **SD Card Module + Card** | Stores received data |
| **TP4056 USB-C Charge Module** | Powers the head unit via USB-C |

---

## 📸 Demo (To Be Added)

_Images showing the system in action_

### **Data Flow**

1. Weather station reads data → timestamps using **RTC** → stores locally.
2. Transmits data to the **head unit** via **ESPNOW**.
3. Head unit writes new readings to the **SD card** → displays on **OLED**.
4. Web server updates real-time readings and calculates statistics (min/max/average over time).

---

## 🚀 Future Improvements

- ✅ Implement **wind speed & direction measurement**
- ✅ Enable **global access** to web server data
- ✅ Optimize **data storage efficiency**
- ✅ Improve **power management for extended operation**

---

## 📜 License

This project is open-source under the **MIT License**.

---

## 💬 Contributing

Pull requests are welcome! If you find any issues or have feature suggestions, feel free to open an issue.

---

## 📩 Contact

For inquiries, reach out via GitHub Issues or Discussions.

---
