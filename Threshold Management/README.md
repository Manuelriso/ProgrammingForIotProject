# ProgrammingForIotProject

Project about the Programing for IoT course.

Threshold Management



Threshold Management is a microservice in which there will be some post-process
operations performed that consists in retrieving historical data from the ThingSpeak database
with REST Web Services, and some computations will be done on this data, in order to
dynamically change thresholds to activate some actuators to preserve the optimal
environment.

So it retrieves historical data from the Thingspeak Adaptor, based on those, it modify dinamically 
thresholds about temperature and humidity, and then we send them with MQTT???? or we modify them in the catalog???