# THINGSPEAK ADAPTOR


The Thingspeak Adaptor is an MQTT subscriber that receives environmental
measurement’s data. --->area1/sensor1/temperature, area1/sensor1/humidity, area1/sensor1/luminosity etc..


It uploads it to Thingspeak through REST Web Services. 


It also provides REST communication to retrieve some data, used for example by the Threshold management microservice.

## GET

- \greenhouse{id}|area{id}\temperature

- \greenhouse{id}|area{id}\luminosity

-\greenhouse{id}|area{id}\humidity

It will, in every method, ask the database for the last 10 values of that specific area and property.