#include "s12sd_uv.hpp"

// BROKEN REWRITE
// int get_uv_index_value(int uv_pin) {
//   float sensor_value = analogRead(uv_pin);
//   float sensor_voltage = sensor_value / 4095.0 * 3.3;
//   int uv_index_value = 0;
//   Serial.println(sensor_voltage);

//   if (sensor_voltage < 0.05)
//     uv_index_value = 0;  // LOW
//   else if (sensor_voltage > 0.05 && sensor_voltage <= 0.227)
//     uv_index_value = 1;  // LOW
//   else if (sensor_voltage > 0.227 && sensor_voltage <= 0.318)
//     uv_index_value = 2;  // LOW
//   else if (sensor_voltage > 0.318 && sensor_voltage <= 0.408)
//     uv_index_value = 3;  // MODERATE
//   else if (sensor_voltage > 0.408 && sensor_voltage <= 0.503)
//     uv_index_value = 4;  // MODERATE
//   else if (sensor_voltage > 0.503 && sensor_voltage <= 0.606)
//     uv_index_value = 5;  // MODERATE
//   else if (sensor_voltage > 0.606 && sensor_voltage <= 0.696)
//     uv_index_value = 6;  // HIGH
//   else if (sensor_voltage > 0.696 && sensor_voltage <= 0.795)
//     uv_index_value = 7;  // HIGH
//   else if (sensor_voltage > 0.795 && sensor_voltage <= 0.881)
//     uv_index_value = 8;  // VERY HIGH
//   else if (sensor_voltage > 0.881 && sensor_voltage <= 0.976)
//     uv_index_value = 9;  // VERY HIGH
//   else if (sensor_voltage > 0.976 && sensor_voltage <= 1.079)
//     uv_index_value = 10;  // VERY HIGH
//   else if (sensor_voltage > 1.079 && sensor_voltage <= 1.170)
//     uv_index_value = 11;  // EXTREME
//   else
//     uv_index_value = -1;  // INVALID

//   return uv_index_value;
// }

std::string get_uv_index(int uv_index_value) {
  std::string uv_index = "";

  switch (uv_index_value) {
    case 0:
      uv_index = "LOW";
      break;
    case 1:
      uv_index = "LOW";
      break;
    case 2:
      uv_index = "LOW";
      break;
    case 3:
      uv_index = "MODERATE";
      break;
    case 4:
      uv_index = "MODERATE";
      break;
    case 5:
      uv_index = "MODERATE";
      break;
    case 6:
      uv_index = "HIGH";
      break;
    case 7:
      uv_index = "HIGH";
      break;
    case 8:
      uv_index = "VERY HIGH";
      break;
    case 9:
      uv_index = "VERY HIGH";
      break;
    case 10:
      uv_index = "VERY HIGH";
      break;
    case 11:
      uv_index = "EXTREME";
      break;
    default:
      uv_index = "INVALID";
      break;
  }

  return uv_index;
}