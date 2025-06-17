# 🌡️ Threshold Management

This service dynamically adjusts temperature, humidity, and luminosity thresholds for greenhouse areas based on historical sensor data retrieved from the ThingSpeak adaptor. It registers itself with a system catalog, updates its status periodically, and sends adjusted thresholds back to the catalog.

---

## 📋 Features

- 📥 Retrieves real-time sensor data (temperature, humidity, luminosity)
- 📈 Calculates weighted moving averages
- ⚖️ Adjusts thresholds intelligently based on environmental trends
- 🧠 Adaptive logic to account for climatic changes (e.g., hot/cold days)