#include "ds3231_live.hpp"

char daysOfTheWeek[7][12] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};

void setupDS3231(RTC_DS3231 &rtc) {
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1);
  }
}

String getDayDate(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char dayDate[33];
  sprintf(dayDate, "%s %02d/%02d/%04d", daysOfTheWeek[now.dayOfTheWeek()],
          now.day(), now.month(), now.year());

  return String(dayDate);
}

String getTime(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char time[15];
  sprintf(time, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(time);
}