#include "ds3231_live.hpp"

char daysOfTheWeek[7][12] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};

// Setup the DS3231 RTC
void setupDS3231(RTC_DS3231 &rtc) {
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1);
  }
}

// Returns the current day date
String getDayDate(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char dayDate[33];
  sprintf(dayDate, "%s %02d/%02d/%04d", daysOfTheWeek[now.dayOfTheWeek()],
          now.day(), now.month(), now.year());

  return String(dayDate);
}

// Returns the current time
String getTime(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char time[15];
  sprintf(time, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(time);
}

// Returns daily filename
String getFilename(RTC_DS3231 &rtc) {
  // Format: YYYY-MM-DD.csv
  DateTime now = rtc.now();
  char dateTime[25];
  sprintf(dateTime, "%04d-%02d-%02d.csv", now.year(), now.month(), now.day());

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

// Returns dates x days before today
String getDateRange(RTC_DS3231 &rtc, int days) { return "Not implemented"; }