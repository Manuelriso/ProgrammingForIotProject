# 🌿 Greenhouse Catalog REST API

This project implements a **RESTful Catalog Service** for managing greenhouses, areas, IoT devices, and microservices in a smart agriculture environment. The service is built with **CherryPy** and uses a `catalog.json` file to store system data.

---

## 🚀 Features

- Add, retrieve, update, and delete greenhouses and their areas
- Register and manage IoT services
- Handle motion detection events (security microservice integration)
- Automatically remove inactive services based on last update
- File locking with `portalocker` to ensure safe concurrent access


## GET
- /greenhouses – List all greenhouses

- /greenhouses/{id} – Get specific greenhouse

- /greenhouse{id}/numberOfAreas – Number of areas in greenhouse

- /greenhouse{id}/areas – List all areas of a greenhouse

- /greenhouse{id}/areas/{areaId} – Get specific area

- /services – List all registered services

## POST

- /greenhouse – Add a new greenhouse

- /greenhouse{id}/area – Add a new area to a greenhouse

- /device – Register a new device

- /service – Register a new service


## PUT

- /greenhouse – Update a greenhouse

- /greenhouse{id}/area – Update a specific area

- /device – Update device info

- /service – Update service info

- /greenhouse{id}/area{areaId}/motion – Increase motion detection counter


## DELETE

- /greenhouse/{id} – Delete a greenhouse

- /greenhouse{id}/area/{areaId} – Delete an area from a greenhouse
