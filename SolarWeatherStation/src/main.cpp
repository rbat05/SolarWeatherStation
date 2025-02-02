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
  print_wakeup_reason();
  bme280_setup(bme280);
  setup_rtc(rtc);

  esp32_modem_sleep();
  bme280_forced_mode();
  esp32_clock_speed_change(80);

  float temperature = bme280_get_temperature(bme280);
  float humidity = bme280_get_humidity(bme280);
  float pressure = bme280_get_pressure(bme280);

  bme280_sleep_mode();

  Serial.print("Temperature: " + String(temperature) + "°C ");
  Serial.print("Humidity: " + String(humidity) + "% ");
  Serial.println("Pressure: " + String(pressure) + "hPa");

  // int uv_index_int = get_uv_index_value(UV_PIN);
  // String uv_index_str = get_uv_index(uv_index_int);

  int uv_index_int = 0;
  String uv_index_str = "OFF";

  String timestamp = get_timestamp(rtc);
  Serial.println("Timestamp: " + timestamp);

  BatteryInfo battery_info = get_battery_info(BATTERY_PIN);
  Serial.print("Battery Voltage: " + String(battery_info.voltage) + "V ");
  Serial.println("Battery Percentage: " + String(battery_info.percentage) +
                 "%");

  int north_49e_reading = 10;
  int south_49e_reading = 20;
  int east_49e_reading = 30;
  int west_49e_reading = 40;

  int tach_49e_reading = 15;

  WeatherData weather_data;
  weather_data.temperature = temperature;
  weather_data.humidity = humidity;
  weather_data.pressure = pressure;
  weather_data.wind_speed = tach_49e_reading;
  weather_data.wind_direction = "NORTH";
  weather_data.uv_index_int = uv_index_int;
  weather_data.uv_index_str = uv_index_str;
  weather_data.date_time = timestamp;

  sd_write_weather_data(weather_data);

  Diagnostics diagnostics;
  diagnostics.date_time = timestamp;
  diagnostics.battery_voltage = battery_info.voltage;
  diagnostics.battery_percentage = battery_info.percentage;
  diagnostics.bme280_address = 118;
  diagnostics.ds3231_address = 104;
  diagnostics.uv_sensor_reading = 0;
  diagnostics.north_49e_reading = 1.2;
  diagnostics.south_49e_reading = 1.3;
  diagnostics.east_49e_reading = 1.4;
  diagnostics.west_49e_reading = 1.5;
  diagnostics.tach_49e_reading = 1.6;

  sd_write_diagnostics(diagnostics);

  Serial.println("Going to sleep now");
  Serial.flush();
  delay(1000);
  esp32_deep_sleep(60);
}

// Empty due to deep sleep
void loop() {}
