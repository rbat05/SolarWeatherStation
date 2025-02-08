#include "espNOW_send.hpp"

uint8_t receiverAddress[] = {0x2c, 0x3a, 0xe8, 0x08, 0xdb, 0x6a};

void onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("Last Packet Send Status: ");

  if (status == ESP_NOW_SEND_SUCCESS) {
    Serial.println("Delivery success.");
  } else {
    Serial.println("Delivery fail.");
  }
}

void sendData(String data) {
  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Register callback for sending data
  esp_now_register_send_cb(onDataSent);

  // Add receiver's MAC address
  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, receiverAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer, exiting.");
    return;
  }

  uint8_t send[data.length() + 1];
  data.getBytes(send, data.length() + 1);
  esp_err_t result = esp_now_send(receiverAddress, send, sizeof(send));

  if (result == ESP_OK) {
    Serial.println("Data sent successfully.");
  } else {
    Serial.println("Error sending data.");
  }
}
