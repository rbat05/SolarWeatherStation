#ifndef DS3231_LIVE_HPP
#define DS3231_LIVE_HPP

#include "RTClib.h"

void setupDS3231(RTC_DS3231 &rtc);
String getDayDate(RTC_DS3231 &rtc);
String getTime(RTC_DS3231 &rtc);

#endif