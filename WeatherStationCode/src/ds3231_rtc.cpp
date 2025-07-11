#include "ds3231_rtc.hpp"
#define SENSOR_ADDR 0x68
// RTC_DS3231 rtc;

char daysOfTheWeek[7][12] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};

// Checks if the DS3231 sensor is connected
void setupRTC(RTC_DS3231 &rtc) {
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC.");
    Serial.flush();
    while (1) delay(10);
  }
  Serial.println("RTC is connected.");
}

// Returns the current date and time
String getTimestamp(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char dateTime[33];
  sprintf(dateTime, "%s %02d/%02d/%04d - %02d:%02d:%02d",
          daysOfTheWeek[now.dayOfTheWeek()], now.day(), now.month(), now.year(),
          now.hour(), now.minute(), now.second());

  return String(dateTime);
}

// Returns daily filename
String getFilename(RTC_DS3231 &rtc) {
  // Format: YYYY-MM-DD.csv
  DateTime now = rtc.now();
  char dateTime[25];
  sprintf(dateTime, "%04d-%02d-%02d.csv", now.year(), now.month(), now.day());

  return String(dateTime);
}
