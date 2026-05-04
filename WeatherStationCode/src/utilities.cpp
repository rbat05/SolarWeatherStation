#include "utilities.hpp"

#include <Arduino.h>

// Returns battery voltage and percentage in a struct
BatteryInfo getBatteryInfo(int battery_pin) {
  BatteryInfo result;

  // Set ADC configuration for ESP32-S2
  analogReadResolution(12);        // 0-4095 range for ESP32-S2
  analogSetAttenuation(ADC_11db);  // Sets max voltage to ~2.5V

  float rollingTotal = 0.0;
  for (int i = 0; i < 100; i++) {
    rollingTotal += analogRead(battery_pin);
  }

  float averageRaw = rollingTotal / 100.0;

  // Step 1: Convert raw value to Voltage at the ADC Pin (0.0 - 2.5V)
  float v_adc = (averageRaw / 4095.0) * 2.5;

  // Step 2: Scale back up to Battery Voltage using divider ratio
  // V_bat = V_adc * ((R1 + R2) / R2) with R1 = 68k, R2 = 100k
  float batVoltage = v_adc * ((68000.0 + 100000.0) / 100000.0);
  float batPercentage = (batVoltage / 4.2) * 100;

  batPercentage = min(round(batPercentage), static_cast<float>(100.0));

  result.voltage = batVoltage;
  result.percentage = batPercentage;

  return result;
}

// Turns off ESP32 WiFi (S2 has no BT)
void esp32ModemSleep() {
  esp_wifi_stop();
  WiFi.mode(WIFI_OFF);
}

// Puts ESP32 into deep sleep for input seconds
void esp32DeepSleep(int seconds) {
  esp_sleep_enable_timer_wakeup(seconds * 1000000);
  // Serial.println("Entering deep sleep for " + String(seconds) + " seconds.");
  esp_deep_sleep_start();
}

// Changes ESP32 clock speed to input value, 80 is good enough for sensors
void esp32ClockSpeedChange(int freq) {
  switch (freq) {
    case 240:
      setCpuFrequencyMhz(240);
      // Serial.println("CPU Frequency set to 240 MHz.");
      break;
    case 160:
      setCpuFrequencyMhz(160);
      // Serial.println("CPU Frequency set to 160 MHz.");
      break;
    case 80:
      setCpuFrequencyMhz(80);
      // Serial.println("CPU Frequency set to 80 MHz.");
      break;
    case 40:
      setCpuFrequencyMhz(40);
      // Serial.println("CPU Frequency set to 40 MHz.");
      break;
    case 20:
      setCpuFrequencyMhz(20);
      // Serial.println("CPU Frequency set to 20 MHz.");
      break;
    case 13:
      setCpuFrequencyMhz(13);
      // Serial.println("CPU Frequency set to 13 MHz.");
      break;
    default:
      setCpuFrequencyMhz(10);
      // Serial.println("CPU Frequency set to 10 MHz.");
      break;
  }
}

// Scans I2C bus for devices 10 times
void I2CScan() {
  Wire.begin(); /*I2C Communication begins*/
  // Serial.println("\nI2C Scanner"); /*print scanner on serial monitor*/
  for (int i = 0; i < 10; i++) {
    byte error, address;
    int nDevices;
    // Serial.println("Scanning..."); /*ESP32 starts scanning available I2C
    // devices*/
    nDevices = 0;
    for (address = 1; address < 127;
         address++) { /*for loop to check number of devices on 127 address*/
      Wire.beginTransmission(address);
      error = Wire.endTransmission();
      if (error == 0) { /*if I2C device found*/
        // Serial.print("I2C device found at address 0x"); /*print this line if
        // I2C
        //                                                    device found*/
        if (address < 16) {
          // Serial.print("0");
        }
        // Serial.println(address, HEX); /*prints the HEX value of I2C address*/
        nDevices++;
      } else if (error == 4) {
        // Serial.print("Unknown error at address 0x");
        if (address < 16) {
          // Serial.print("0");
        }
        // Serial.println(address, HEX);
      }
    }
    if (nDevices == 0) {
      // Serial.println("No I2C devices found\n"); /*If no I2C device attached
      // print
      //                                              this message*/
    } else {
      // Serial.println("done\n");
    }
    delay(5000); /*Delay given for checking I2C bus every 5 sec*/
  }
}

// Prints the wakeup reason
void printWakeupReason() {
  esp_sleep_wakeup_cause_t wakeup_reason;

  wakeup_reason = esp_sleep_get_wakeup_cause();

  switch (wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT0:
      // Serial.println("Wakeup caused by external signal using RTC_IO");
      break;
    case ESP_SLEEP_WAKEUP_EXT1:
      // Serial.println("Wakeup caused by external signal using RTC_CNTL");
      break;
    case ESP_SLEEP_WAKEUP_TIMER:
      // Serial.println("Wakeup caused by timer");
      break;
    case ESP_SLEEP_WAKEUP_TOUCHPAD:
      // Serial.println("Wakeup caused by touchpad");
      break;
    case ESP_SLEEP_WAKEUP_ULP:
      // Serial.println("Wakeup caused by ULP program");
      break;
    default:
      // Serial.printf("Wakeup was not caused by deep sleep: %d\n",
      // wakeup_reason);
      break;
  }
}
