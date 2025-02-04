#ifndef DS3231_RTC_HPP
#define DS3231_RTC_HPP
#include <Arduino.h>
#include <RTClib.h>
#include <Wire.h>
#include <string.h>

void setupRTC(RTC_DS3231 &rtc);
String getTimestamp(RTC_DS3231 &rtc);
#endif