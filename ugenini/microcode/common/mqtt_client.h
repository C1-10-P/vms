// firmware/common/mqtt_client.h
#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <PubSubClient.h>
#include <WiFi.h>

extern PubSubClient mqttClient;

void connectMQTT();
void publishMessage(const char* topic, const char* payload);
void mqttCallback(char* topic, byte* payload, unsigned int length);

#endif