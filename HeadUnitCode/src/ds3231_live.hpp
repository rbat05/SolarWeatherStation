#ifndef DS3231_LIVE_HPP
#define DS3231_LIVE_HPP

#include "RTClib.h"
struct TimeDifference {
  int hours;
  int minutes;
  int seconds;
};

void setupDS3231(RTC_DS3231 &rtc);
String getDayDate(RTC_DS3231 &rtc);
String getTime(RTC_DS3231 &rtc);
String getFilename(RTC_DS3231 &rtc);
TimeDifference getTimeDifference(RTC_DS3231 &rtc, String latest_reading_time,
                                 String latest_reading_day_date);
#endif