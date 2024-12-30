# SolarWeatherStation
## IOT Weather Station with Data Logging & AI Powered Predictions
### Brief Description
Solar powered weather station with 4000mAh lithium battery backup, featuring automatic charging when not in use. Based on ESP32-WROOM-32 microcontroller measuring temperature, humidity, pressure, UV level, wind speed and direction using various sensors. Custom designed anemometer to measure wind speed and wind vane to measure wind direction. Data saved and then transmitted over WiFi to IoT server where it is collated and displayed. Custom trained AI model to make future predictions, gets better with time.
### Product Design Specification
#### Functional Requirements
- Must measure temperature, humidity, pressure, UV level, wind speed and direction every 5 minutes.
- Must save readings locally.
- Must transmit readings to internal server.
- Must be weather proof.
- Must present readings to user in some form.
#### Constraints
- Design must be entirely off the grid i.e. no power plug.
- Anemometer and Wind Vane must be on the same shaft.
#### Design Objectives
- Minimize cost.
- Minimize footprint.
- Make it look good.
- Attempt to use collected data to make predictions using custom AI model.

### Concept Design Phase