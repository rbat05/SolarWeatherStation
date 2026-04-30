#include <Arduino.h>  // Built-in library
#include <Wire.h>
#include <string.h>

#include <iostream>  // Built-in library

#include "49e_wind_speed_dir.hpp"
#include "bme280_temp_humi_pres.hpp"
#include "ds1307_rtc.hpp"
#include "espNOW_send.hpp"
#include "sd_write.hpp"
#include "utilities.hpp"

// Add this line to include the ESP32-specific header
#include "soc/rtc_cntl_reg.h"
#include "soc/soc.h"

// Custom I2C Pins
const int I2C_SDA = 33;
const int I2C_SCL = 35;

// BME280 - Connected via I2C
Adafruit_BME280 bme280;

// Tiny RTC (DS1307) - Connected via I2C
RTC_DS1307 rtc;

// Battery Pin - Connected via Analog, G1 = Battery
const int BATTERY_PIN = 1;

// 49E - Connected via Analog, G39 = North, G34 = South, G35 = East, G32 = West
// WIND DIRECTION
const int PIN_49E_NORTH = 39;
const int PIN_49E_SOUTH = 34;
const int PIN_49E_EAST = 35;
const int PIN_49E_WEST = 32;

// 49E - Connected via Analog, G33 = Tachometer
// WIND SPEED
const int PIN_49E_TACH = 33;

// Program parameters
const int SLEEP_SECONDS = 30;    // Sleep for 30 seconds
const int ESP_CLOCK_SPEED = 80;  // Set clock speed to 80MHz

// Custom SPI Pins
const int SPI_SCK = 7;
const int SPI_MISO = 9;
const int SPI_MOSI = 11;
const int SD_CS_PIN = 12;  // Chip select pin for SD card

// LED Pin
const int LED = 15;

void setup() {
  // Disable brownout detector, thug it out lil bro
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);

  // Blink LED twice - signify program start
  pinMode(LED, OUTPUT);
  digitalWrite(LED, HIGH);
  delay(50);
  digitalWrite(LED, LOW);
  delay(50);
  digitalWrite(LED, HIGH);
  delay(50);
  digitalWrite(LED, LOW);
  delay(50);

  // Explicitly start I2C and SPI using our defined pins
  Wire.begin(I2C_SDA, I2C_SCL);
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, SD_CS_PIN);

  printWakeupReason();

  bme280Setup(bme280);
  setupRTC(rtc);

  // ESP BT and Wifi off, clock speed 240MHz->80MHz
  esp32ModemSleep();
  esp32ClockSpeedChange(ESP_CLOCK_SPEED);

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

  // Get string representation of the data, and write data to SD
  String formattedData = sdWriteReadings(data, filename);

  // Send data via ESP-NOW
  sendData(formattedData);

  // Clear the serial buffer, turn off modems
  Serial.flush();
  esp32ModemSleep();

  // Blink LED twice - signify program end
  digitalWrite(LED, HIGH);
  delay(50);
  digitalWrite(LED, LOW);
  delay(50);
  digitalWrite(LED, HIGH);
  delay(50);
  digitalWrite(LED, LOW);
  delay(50);

  // Go to sleep for 30sec
  Serial.println("Going to sleep now.");
  esp32DeepSleep(SLEEP_SECONDS);
}

int loopCounter = 0;

// Safety catch loop
void loop() {
  loopCounter++;
  if (loopCounter >= 1000) {
    Serial.println(
        "Safety catch triggered: Trapped in loop, forcing deep sleep!");
    esp32DeepSleep(SLEEP_SECONDS);
  }
  delay(10);  // Prevent watchdog timeout while looping
}

/*
 * Power Consumption & Battery Life Estimate
 * ---------------------------------------
 * Based on a 5-minute (300s) deep sleep cycle and a 4000mAh LiPo battery.
 *
 * 1. Active Mode: ~8.0 seconds per cycle
 *    - Average Active Current: ~60 mA (includes SD write and ESP-NOW WiFi
 * spikes)
 * 2. Deep Sleep Mode: ~292 seconds per cycle
 *    - Average Sleep Current: ~0.5 mA (500 uA, largely from MicroSD module idle
 * draw)
 *
 * Weighted Average Current: ~2.08 mA
 * Estimated Runtime (without solar): ~76 Days
 */
