# 🌱 ProgrammingForIotProject

## SMART GARDEN

---

## 📘 Description

This project aims to provide a **smart and automated solution** for managing a garden composed of multiple **greenhouses**, each divided into different **areas**.

Each area is equipped with its own sensors that periodically send environmental data:

- 🌡️ Temperature sensor  
- 💧 Humidity sensor  
- 💡 Luminosity sensor  
- 🕴️ Motion sensor

These sensors allow real-time monitoring and smart management of the greenhouse environments.

---

## 🔗 Communication Paradigms

The system integrates **two main communication paradigms**:

### 1. 🔄 Synchronous – REST Web Service

This service uses standard HTTP methods for interaction:

- `GET` – Retrieve data  
- `POST` – Add new data  
- `PUT` – Update existing data  
- `DELETE` – Remove data  

### 2. 📡 Asynchronous – MQTT Protocol

The MQTT-based architecture includes:

- **Message Broker** (e.g., Mosquitto)  
- **Publishers** (sensor nodes sending data)  
- **Subscribers** (applications or components consuming the data)

This approach ensures **low-latency**, **lightweight communication**, ideal for IoT scenarios.

---

## 🚀 Features

- Modular greenhouse and area structure
- Dual communication paradigms (REST + MQTT)
- Real-time sensor monitoring


## 🛠️ Technologies Used

- Python
- REST APIs 
- MQTT 
- Sensors (DHT22, Motion sensor, Luminosity sensor)
- Raspberry Pi 


