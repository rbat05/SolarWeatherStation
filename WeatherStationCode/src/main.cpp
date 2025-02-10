#include <Arduino.h>  // Built-in library
#include <Wire.h>
#include <string.h>

#include <iostream>  // Built-in library

#include "49e_wind_speed_dir.hpp"
#include "bme280_temp_humi_pres.hpp"
#include "ds3231_rtc.hpp"
#include "espNOW_send.hpp"
#include "sd_write.hpp"
#include "utilities.hpp"

// Add this line to include the ESP32-specific header
#include "soc/rtc_cntl_reg.h"
#include "soc/soc.h"

// BME280 - Connected via I2C, G22 = SCL, G21 = SDA
Adafruit_BME280 bme280;

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
  // Disable brownout detector, thug it out lil bro
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);
  printWakeupReason();

  bme280Setup(bme280);
  setupRTC(rtc);

  // ESP BT and Wifi off, clock speed 240MHz->80MHz
  esp32ModemSleep();
  esp32ClockSpeedChange(80);

  // BME280 into forced mode to take readings
  bme280ForcedMode();

  float temperature = bme280GetTemperature(bme280);
  float humidity = bme280GetHumidity(bme280);
  float pressure = bme280GetPressure(bme280);

  // BME280 into sleep mode after readings taken
  bme280SleepMode();

  Serial.print("Temperature: " + String(temperature) + "°C ");
  Serial.print("Humidity: " + String(humidity) + "% ");
  Serial.println("Pressure: " + String(pressure) + "hPa");

  String timestamp = getTimestamp(rtc);
  Serial.println("Timestamp: " + timestamp);

  BatteryInfo battery_info = getBatteryInfo(BATTERY_PIN);
  Serial.print("Battery Voltage: " + String(battery_info.voltage) + "V ");
  Serial.println("Battery Percentage: " + String(battery_info.percentage) +
                 "%");

  String filename = getFilename(rtc);
  Serial.println("Filename: " + filename);

  // Create a data struct to hold all the readings
  Readings data;
  data.dateTime = timestamp;
  data.temperature = temperature;
  data.humidity = humidity;
  data.pressure = pressure;
  data.windSpeed = -1.0;
  data.windDirection = "NA";
  data.batteryVoltage = battery_info.voltage;
  data.batteryPercentage = battery_info.percentage;

  if (!SD.begin(5)) {
    Serial.println("Card Mount Failed");
    return;
  }

  // Get string representation of the data, and write data to SD
  String formattedData = sdWriteReadings(data, filename);

  // Send data via ESP-NOW
  sendData(formattedData);

  // Clear the serial buffer, turn off modems
  Serial.flush();
  esp32ModemSleep();
  // Go to sleep for 5mins
  Serial.println("Going to sleep now.");
  esp32DeepSleep(300);
}

// Empty due to deep sleep
void loop() {}
