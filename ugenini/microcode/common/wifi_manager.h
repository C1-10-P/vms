// firmware/common/wifi_manager.h
#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>

extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

void connectWiFi();
bool isWiFiConnected();

#endif