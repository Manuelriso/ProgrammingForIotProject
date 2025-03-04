# ProgrammingForIotProject

Project about the Programing for IoT course.

Catalog

The Catalog acts as a service and device registry for all actors in the system (excluding thirdparty ones). It provides information about endpoints (e.g., REST Web Services and MQTT
topics) for all devices, resources, and services within the platform. It also serves as a central
repository for runtime metadata, such as MQTT topic names, sensor/client identifiers, and
web service URLs, ensuring seamless interaction among all actors. During startup, each
actor registers itself in the catalog and then retrieves this metadata from the Catalog using
its REST Web Services.

So, in the catalog, we will have a .json file with all informations about everything, 
It acts like a Rest WEB Service in order to retrieve/get/update data.