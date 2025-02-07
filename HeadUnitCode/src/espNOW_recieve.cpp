#include "espNOW_recieve.hpp"

void onDataReceived(uint8_t *senderMac, uint8_t *incomingData, uint8_t len) {
  Serial.print("Received: ");
  for (int i = 0; i < len; i++) {
    Serial.print((char)incomingData[i]);
  }
  Serial.println();
}

void setupEspNOW() {
  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // Print MAC address of the receiver
  Serial.print("Receiver MAC: ");
  for (int i = 0; i < 6; i++) {
    Serial.print(WiFi.macAddress()[i], HEX);
    if (i < 5) {
      Serial.print(":");
    }
  }
  Serial.println();

  // Initialize ESP-NOW
  if (esp_now_init() != 0) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Register callback for receiving data
  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE);
  esp_now_register_recv_cb(onDataReceived);
}