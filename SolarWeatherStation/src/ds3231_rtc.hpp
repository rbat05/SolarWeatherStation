#ifndef DS3231_RTC_HPP
#define DS3231_RTC_HPP
#include <Arduino.h>
#include <RTClib.h>
#include <Wire.h>
#include <string.h>

// Checks if the BME280 sensor is connected
void ds3231_setup(RTC_DS3231 rtc);
// Returns the current timestamp
std::string ds3231_get_timestamp(RTC_DS3231 rtc);

#endif