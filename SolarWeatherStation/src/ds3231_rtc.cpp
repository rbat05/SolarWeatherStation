#include "ds3231_rtc.hpp"
#define SENSOR_ADDR 0x68

void ds3231_setup(RTC_DS3231 rtc) {
  bool status = rtc.begin();

  if (status == true) {
    Serial.printf("DS3231 RTC is connected @0x%X!\n", SENSOR_ADDR);

    // Set the initial date and time
    // rtc.adjust(DateTime(__DATE__, __TIME__));

    return;
  } else {
    Serial.println("DS3231 RTC is not connected, check wiring or reset.");
    while (1);
  }
}

std::string ds3231_get_timestamp(RTC_DS3231 rtc) {
  DateTime now = rtc.now();
  // Format: HH:MM:SS - DD/MM/YYYY
  char timestamp[21];
  sprintf(timestamp, "%02d:%02d:%02d - %02d/%02d/%04d", now.hour(),
          now.minute(), now.second(), now.day(), now.month(), now.year());
  return timestamp;
}

// void printTwoDigits(int number) {
//   if (number < 10) {
//     Serial.print("0");  // Add a leading zero for single-digit numbers
//   }

//   Serial.print(number);
// }