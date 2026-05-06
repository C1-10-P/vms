// firmware/common/config.h
#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// MQTT Configuration
const char* MQTT_BROKER = "192.168.1.100";  // Your Raspberry Pi IP
const int MQTT_PORT = 1883;
const char* MQTT_USER = "esp32_camera";
const char* MQTT_PASSWORD = "your_password";

// Node Configuration
const char* NODE_UUID = "CAM-001";
const char* NODE_TYPE = "camera";

// Pin Configuration
#define PIR_PIN 13
#define LED_PIN 4

#endif