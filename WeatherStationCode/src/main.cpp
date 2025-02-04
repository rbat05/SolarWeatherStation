#include <Arduino.h>  // Built-in library
#include <Wire.h>
#include <string.h>

#include <iostream>  // Built-in library

#include "49e_wind_speed_dir.hpp"
#include "bme280_temp_humi_pres.hpp"
#include "ds3231_rtc.hpp"
#include "s12sd_uv.hpp"
#include "sd_read_write.hpp"
#include "utilities.hpp"

// BME280 - Connected via I2C, G22 = SCL, G21 = SDA
Adafruit_BME280 bme280;

// S12SD - Connected via Analog, G36 = UV
const int UV_PIN = 36;

// DS3231 - Connected via I2C, G22 = SCL, G21 = SDA
RTC_DS3231 rtc;

// Battery Pin - Connected via Analog, G25 = Battery
const int BATTERY_PIN = 25;

// 49E - Connected via Analog, G39 = North, G34 = South, G35 = East, G32 = West
// WIND DIRECTION
const int PIN_49E_NORTH = 39;
const int PIN_49E_SOUTH = 34;
const int PIN_49E_EAST = 35;
const int PIN_49E_WEST = 32;

// 49E - Connected via Analog, G33 = Tachometer
// WIND SPEED
const int PIN_49E_TACH = 33;

void setup() {
  Serial.begin(115200);
  printWakeupReason();
  bme280Setup(bme280);
  setupRTC(rtc);

  esp32ModemSleep();
  bme280ForcedMode();
  esp32ClockSpeedChange(80);

  float temperature = bme280GetTemperature(bme280);
  float humidity = bme280GetHumidity(bme280);
  float pressure = bme280GetPressure(bme280);

  bme280SleepMode();

  Serial.print("Temperature: " + String(temperature) + "°C ");
  Serial.print("Humidity: " + String(humidity) + "% ");
  Serial.println("Pressure: " + String(pressure) + "hPa");

  // int uvIndexInt = getUVIndexValue(UV_PIN);
  // String uvIndexStr = getUVIndex(uvIndexInt);

  int uvIndexInt = 0;
  String uvIndexStr = "OFF";

  String timestamp = getTimestamp(rtc);
  Serial.println("Timestamp: " + timestamp);

  BatteryInfo battery_info = getBatteryInfo(BATTERY_PIN);
  Serial.print("Battery Voltage: " + String(battery_info.voltage) + "V ");
  Serial.println("Battery Percentage: " + String(battery_info.percentage) +
                 "%");

  int north49eReading = 10;
  int south49eReading = 20;
  int east49eReading = 30;
  int west49eReading = 40;

  int tach49eReading = 15;

  WeatherData weather_data;
  weather_data.temperature = temperature;
  weather_data.humidity = humidity;
  weather_data.pressure = pressure;
  weather_data.windSpeed = tach49eReading;
  weather_data.windDirection = "NORTH";
  weather_data.uvIndexInt = uvIndexInt;
  weather_data.uvIndexStr = uvIndexStr;
  weather_data.dateTime = timestamp;

  sdWriteWeatherData(weather_data);

  Diagnostics diagnostics;
  diagnostics.dateTime = timestamp;
  diagnostics.batteryVoltage = battery_info.voltage;
  diagnostics.batteryPercentage = battery_info.percentage;
  diagnostics.bme280Address = 118;
  diagnostics.ds3231Address = 104;
  diagnostics.uvSensorReading = 0;
  diagnostics.north49eReading = 1.2;
  diagnostics.south49eReading = 1.3;
  diagnostics.east49eReading = 1.4;
  diagnostics.west49eReading = 1.5;
  diagnostics.tach49eReading = 1.6;

  sdWriteDiagnostics(diagnostics);

  Serial.println("Going to sleep now");
  Serial.flush();
  delay(1000);
  esp32DeepSleep(60);
}

// Empty due to deep sleep
void loop() {}
