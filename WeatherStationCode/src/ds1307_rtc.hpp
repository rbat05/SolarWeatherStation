#ifndef DS1307_RTC_HPP
#define DS1307_RTC_HPP
#include <Arduino.h>
#include <RTClib.h>
#include <Wire.h>
#include <string.h>

void setupRTC(RTC_DS1307& rtc);
String getTimestamp(RTC_DS1307& rtc);
String getFilename(RTC_DS1307& rtc);
#endif