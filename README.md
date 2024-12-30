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
#### Problem Breakdown
##### Transmitter side i.e. external weather station
1. Microcontroller & Processing subsystem
   i.   Need a microcontroller and an external storage system. 
   ii.  Readings need to be timestamped and transmitted.
2. Sensors subsystem
   i.   Need various sensors to get readings. 
   ii.  Need to be low power and reasonably accurate. 
   iii. Custom design for anemometer and wind vane.
3. Power subsystem
   i.  Power balance i.e. power coming in through various means enough to power the entire system without outage. 
   ii.  Various power saving tricks.
4. Housing
   i.  Need to store all electronics in a weather resistant housing design.
   ii. Not be an eye-sore.

##### Receiver side i.e. internal server
1. Microcontroller & Processing subsystem
   i.  Microcontroller to receive and process data.
   ii. Store data locally for user reference.
2. User Interface
   i. An interface to give readings to user.
3. Power
   i. Easy to power interface.
#### Solution Matrix

| Transmitter Side                       | i                                                                                                                                                                                                                    | ii                                                                                 | iii                                                        |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Microcontroller & Processing subsystem | ESP32 or Arduino Nano. MicroSD external module to read and write.                                                                                                                                                    | Real Time Clock module for timestamps. Transmission through Bluetooth or WiFi.     | -                                                          |
| Sensors subsystem                      | I2C compatible sensors. BME180/280/680 for temp, humidity and pressure. S12SD for UV.                                                                                                                                | Listed modules are all reasonably accurate and power efficient.                    | Hall effect sensors for wind data build. 3D printed parts. |
| Power subsystem                        | Large solar panel placed facing north for maximum power generation. Wind is inefficient at this scale. Charging circuit for a lithium battery to store excess power to run system during bad weather and night-time. | ESP32 has configurable modules i.e. modems can be turned off. Also has deep sleep. | -                                                          |
| Housing                                | Stevenson screen to prevent water from entering system.                                                                                                                                                              | Later stage design dependant.                                                      | -                                                          |

| Receiver Side                          | i                                                                                                                                                                  | ii                                         |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| Microcontroller & Processing subsystem | ESP32 or Arduino Nano.                                                                                                                                             | MicroSD external module to read and write. |
| User Interface                         | Small LED panel display to show most recent readings/current status. Online control panel accessible through internet anywhere shows current/historic/future data. | -                                          |
| Power                                  | USB C power interface, simple.                                                                                                                                     | -                                          |

#### Solution Selection

The problem is relatively simple, and with my experience with sensors and microcontrollers, I can make well educated decisions.
##### Transmitter side i.e. external weather station

| Subproblem                             | Parts Chosen & Reasoning                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Microcontroller & Processing subsystem | ESP32 microcontroller - Inbuilt wifi, power saving modes with configurable setups. Arduino Nano does not have these, and would require an external networking adapter.<br><br>MicroSD adapter - To store readings locally, simplest solution.<br><br>DS3231 RTC Module - To get time readings reliably, ESP32s RTC resets on restart so it is not reliable.              |
| Sensors subsystem                      | BME280 - For temperature, humidity and pressure readings. Is power efficient and reliable. DHT22 is unreliable as it has a large error.<br><br>S12SD - For UV readings, simplest solution, compatible with microcontroller.<br><br>49E Hall Effect Sensor - Analog 3 pin hall effect sensor to be used in the anemometer and wind vane build.                            |
| Power subsystem                        | 5V 500mAh Solar Panel - High current solar panel to generate power reliably.<br><br>4000mAh Single Cell Battery - High capacity battery to store excess power generated. Can cover system power requirements for weeks.<br><br>These combined together allow for the system to function off the grid, system will be designed to save power using deep sleep techniques. |
| Housing                                | Custom designed and 3D printed parts. Stevenson screen to waterproof the shell.                                                                                                                                                                                                                                                                                          |

##### Receiver side i.e. internal server

| Subproblem                             | Parts Chosen & Reasoning                                                                                                                                                                      |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Microcontroller & Processing subsystem | Same setup as weather station, ESP32 with an SD card adapter. To maintain parity and prevent incompatibility issues.                                                                          |
| User Interface                         | SSD1306 Small OLED Display - To display current readings as well as status.<br>ESPHome - IoT server hosted locally to show current/historic/future data to user, accessible through internet. |
| Power                                  | USB-C charger.                                                                                                                                                                                |
