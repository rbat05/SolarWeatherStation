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

// Returns daily filename
String getFilename(RTC_DS3231 &rtc) {
  // Format: DD-MM-YYYY.csv
  DateTime now = rtc.now();
  char dateTime[25];
  sprintf(dateTime, "%02d-%02d-%04d.csv", now.day(), now.month(), now.year());

  return String(dateTime);
}

TimeDifference getTimeDifference(RTC_DS3231 &rtc, String latest_reading_time,
                                 String latest_reading_day_date) {
  DateTime now = rtc.now();

  int latest_reading_hour = latest_reading_time.substring(0, 2).toInt();
  int latest_reading_minute = latest_reading_time.substring(3, 5).toInt();
  int latest_reading_second = latest_reading_time.substring(6, 8).toInt();

  int latest_reading_day = latest_reading_day_date.substring(4, 7).toInt();
  int latest_reading_month = latest_reading_day_date.substring(7, 10).toInt();
  int latest_reading_year = latest_reading_day_date.substring(10, 15).toInt();

  DateTime latest_reading(latest_reading_year, latest_reading_month,
                          latest_reading_day, latest_reading_hour,
                          latest_reading_minute, latest_reading_second);

  TimeDifference timeDifference;
  TimeSpan difference = now - latest_reading;

  timeDifference.hours = difference.hours();
  timeDifference.minutes = difference.minutes();
  timeDifference.seconds = difference.seconds();

  return timeDifference;
}
