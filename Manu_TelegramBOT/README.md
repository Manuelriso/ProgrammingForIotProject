# 🌱 Smart Greenhouse Telegram Bot

A Telegram bot for managing and monitoring smart greenhouses using MQTT and REST APIs. This bot allows users to control actuators (like lights, pumps, and ventilation) and view sensor data in real time.

---

## 🚀 Features

- ✅ Add and delete greenhouses and areas
- 🌡 View live sensor data (temperature, humidity, luminosity)
- 🕹 Control actuators (lights, pumps, ventilation)
- 🔄 Real-time communication via MQTT
- 🔗 REST API integration for system catalog
- 👥 Per-user chat state tracking and command management

---

## 🧰 Technologies Used

- **Python 3.7+**
- `telepot` – Telegram Bot API
- `paho-mqtt` – MQTT client
- `requests` – HTTP requests to system catalog
- `uuid`, `json`, `time`, `threading`, `os` – Utilities

---

## Available commands

- /start	Starts the bot and shows main menu
- /add_greenhouse	Adds a new greenhouse
- /add_area	Adds a new area to an existing greenhouse
- /delete_greenhouse	Deletes a greenhouse
- /delete_area	Deletes a specific area
- /viewcurrentdata	View latest sensor data
- /sendactuation	Control actuators (pump, light, etc.)

