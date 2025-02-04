#include "ds3231_live.hpp"

char daysOfTheWeek[7][12] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};

void setup_ds3231(RTC_DS3231 &rtc) {
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1);
  }
}

String get_day_date(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char day_date[33];
  sprintf(day_date, "%s %02d/%02d/%04d", daysOfTheWeek[now.dayOfTheWeek()],
          now.day(), now.month(), now.year());

  return String(day_date);
}

String get_time(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char time[15];
  sprintf(time, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(time);
}