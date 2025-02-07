#include "s12sd_uv.hpp"
// NOT USED ANYWHERE

// BROKEN REWRITE
int getUVIndexValue(int uv_pin) {
  float sensorVoltage = analogReadMilliVolts(uv_pin);
  int uvIndexValue = 0;
  Serial.println(sensorVoltage);
  return 0;

  if (sensorVoltage < 0.05)
    uvIndexValue = 0;  // LOW
  else if (sensorVoltage > 0.05 && sensorVoltage <= 0.227)
    uvIndexValue = 1;  // LOW
  else if (sensorVoltage > 0.227 && sensorVoltage <= 0.318)
    uvIndexValue = 2;  // LOW
  else if (sensorVoltage > 0.318 && sensorVoltage <= 0.408)
    uvIndexValue = 3;  // MODERATE
  else if (sensorVoltage > 0.408 && sensorVoltage <= 0.503)
    uvIndexValue = 4;  // MODERATE
  else if (sensorVoltage > 0.503 && sensorVoltage <= 0.606)
    uvIndexValue = 5;  // MODERATE
  else if (sensorVoltage > 0.606 && sensorVoltage <= 0.696)
    uvIndexValue = 6;  // HIGH
  else if (sensorVoltage > 0.696 && sensorVoltage <= 0.795)
    uvIndexValue = 7;  // HIGH
  else if (sensorVoltage > 0.795 && sensorVoltage <= 0.881)
    uvIndexValue = 8;  // VERY HIGH
  else if (sensorVoltage > 0.881 && sensorVoltage <= 0.976)
    uvIndexValue = 9;  // VERY HIGH
  else if (sensorVoltage > 0.976 && sensorVoltage <= 1.079)
    uvIndexValue = 10;  // VERY HIGH
  else if (sensorVoltage > 1.079 && sensorVoltage <= 1.170)
    uvIndexValue = 11;  // EXTREME
  else
    uvIndexValue = -1;  // INVALID

  return uvIndexValue;
}

String getUVIndex(int uvIndexValue) {
  String uvIndex = "";

  switch (uvIndexValue) {
    case 0:
      uvIndex = "LOW";
      break;
    case 1:
      uvIndex = "LOW";
      break;
    case 2:
      uvIndex = "LOW";
      break;
    case 3:
      uvIndex = "MODERATE";
      break;
    case 4:
      uvIndex = "MODERATE";
      break;
    case 5:
      uvIndex = "MODERATE";
      break;
    case 6:
      uvIndex = "HIGH";
      break;
    case 7:
      uvIndex = "HIGH";
      break;
    case 8:
      uvIndex = "VERY HIGH";
      break;
    case 9:
      uvIndex = "VERY HIGH";
      break;
    case 10:
      uvIndex = "VERY HIGH";
      break;
    case 11:
      uvIndex = "EXTREME";
      break;
    default:
      uvIndex = "INVALID";
      break;
  }

  return uvIndex;
}

float uv_sensor_testing(int uv_pin) {
  float sensorVoltage = 0.0;
  for (int i = 0; i < 100; i++) {
    sensorVoltage += analogReadMilliVolts(uv_pin);
    delay(10);
  }
  Serial.println(sensorVoltage / 100);
  return sensorVoltage / 100;
}