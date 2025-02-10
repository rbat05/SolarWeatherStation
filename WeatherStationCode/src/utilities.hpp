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

BatteryInfo getBatteryInfo(int battery_pin);
void esp32ModemSleep();
void esp32DeepSleep(int seconds);
void esp32ClockSpeedChange(int freq);
void I2CScan();
void printWakeupReason();

#endif