#ifndef UTILITIES_HPP
#define UTILITIES_HPP
#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_bt.h>
#include <esp_wifi.h>

struct BatteryInfo {
  float voltage;
  float percentage;
};

BatteryInfo get_battery_info(int battery_pin);
void esp32_modem_sleep();
void esp32_modem_wake();
void esp32_deep_sleep(int seconds);
void esp32_clock_speed_change(int freq);
void I2C_Scan();
void print_wakeup_reason();

// Need to implement ESPNOW -
// https://randomnerdtutorials.com/esp-now-esp32-arduino-ide/

#endif