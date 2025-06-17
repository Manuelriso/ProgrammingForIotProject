# ProgrammingForIotProject

TELEGRAM BOT

Telegram Bot is a service that integrates the proposed infrastructure into the Telegram
platform, a cloud-based instant messaging infrastructure. 

Users can:
1) Handle their greenhouses and areas. Adding and deleting them under the system limits.
Setting the plant type inside each area and the trhesholds/objectives to be followed by the automatic systems in the greenhouses.
2) Retrieve current data from the different sensors in the area of interest. It retrieves  measurements from IoT devices exploiting REST Web Services. Those data are provided by the Raspberry Pi and Other Device Connectors.
3) Retrieve historical data from areas managed in graphical way, from the Thingspeak Adaptor - NodeRED.
4) Send actuation commands to our IoT devices as wished, as a MQTT publisher.
5) It acts as a MQTT subscriber, to show motions alerts.
In this first free version subscription, all temeprature, humidity and light alerts, are handled by the internal system.

% It has a timeout of 3 minutes.


