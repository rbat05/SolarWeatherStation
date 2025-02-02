#include "ds3231_rtc.hpp"
#define SENSOR_ADDR 0x68
// RTC_DS3231 rtc;

char daysOfTheWeek[7][12] = {"Sunday",   "Monday", "Tuesday", "Wednesday",
                             "Thursday", "Friday", "Saturday"};

// Checks if the DS3231 sensor is connected
void setup_rtc(RTC_DS3231 &rtc) {
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC.");
    Serial.flush();
    while (1) delay(10);
  }
  Serial.println("RTC is connected.");
}

// Prints the current date and time
String get_timestamp(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char dateTime[33];
  sprintf(dateTime, "%s %02d/%02d/%04d - %02d:%02d:%02d",
          daysOfTheWeek[now.dayOfTheWeek()], now.day(), now.month(), now.year(),
          now.hour(), now.minute(), now.second());

  return String(dateTime);
}
