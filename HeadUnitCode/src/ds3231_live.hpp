#ifndef DS3231_LIVE_HPP
#define DS3231_LIVE_HPP

#include "RTClib.h"

void setup_ds3231(RTC_DS3231 &rtc);
String get_day_date(RTC_DS3231 &rtc);
String get_time(RTC_DS3231 &rtc);

#endif