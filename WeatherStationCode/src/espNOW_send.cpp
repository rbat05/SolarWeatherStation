#include "espNOW_send.hpp"

uint8_t receiverMac[] = {0x2C, 0x3A, 0xE8,
                         0x08, 0xDB, 0x6A};  // ESP8266 MAC Address

void onDataSent(const uint8_t* macAddr, esp_now_send_status_t status) {
  Serial.print("Last Packet Send Status: ");
  if (status == ESP_NOW_SEND_SUCCESS) {
    Serial.println("Delivery success");
  } else {
    Serial.println("Delivery fail");
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
  memcpy(peerInfo.peer_addr, receiverMac, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }

  // Converting String to char array
  const char* dataCStr = data.c_str();
  uint8_t dataToSend[strlen(dataCStr) + 1];
  strcpy((char*)dataToSend, dataCStr);

  // Send message via ESP-NOW
  esp_err_t result = esp_now_send(receiverMac, dataToSend, sizeof(dataToSend));

  if (result == ESP_OK) {
    Serial.println("Sent with success");
  } else {
    Serial.println("Error sending the data");
    // Try 5 times
    for (int i = 0; i < 5; i++) {
      delay(100);
      result = esp_now_send(receiverMac, dataToSend, sizeof(dataToSend));
      if (result == ESP_OK) {
        Serial.println("Sent with success");
        break;
      } else {
        Serial.println("Error sending the data");
      }
    }
  }
}
