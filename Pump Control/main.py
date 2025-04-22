import cherrypy
import json
from datetime import datetime
from CatalogClient import *
import time
from pumpcontroller import PumpController
from CatalogClient import CatalogAPI, Catalog_Navigator

class PumpControllerREST:
    exposed = True
    
    def __init__(self, settings):
        self.settings = settings
        self.catalog_navigator = Catalog_Navigator()
        
        # Initialize PumpController
        self.pump_controller = PumpController(settings)
        
        # Initialize CatalogAPI for REST operations
        self.catalog_api = CatalogAPI(self.catalog_navigator, settings)
        
    def registerService(self):
        return self.catalog_api.registerService()
        
    def registerDevice(self):
        return self.catalog_api.registerDevice()
        
    def updateService(self):
        self.catalog_api.updateService()
        
    def updateDevice(self):
        self.catalog_api.updateDevice()
        
    def stop(self):
        self.temp_controller.stopSim()

if __name__ == "__main__":
    # Load settings
    settings = json.load(open('settings.json'))
    
    # Initialize the combined REST/MQTT service
    service = PumpControllerREST(settings)
    
    # Register the service with the catalog
    service.registerService()
    service.registerDevice()
    
    # Start the MQTT client
    service.pump_controller.startSim()
    
    # Configure CherryPy
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': settings.get('servicePort', 8080)
    })
    
    cherrypy.tree.mount(service, '/', conf)
    
    try:
        cherrypy.engine.start()
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            
            # Periodically update (every 40 seconds)
            if counter >= 20:
                service.updateService()
                service.updateDevice()
                # Update subscriptions in case catalog changed
                service.pump_controller.update_subscriptions()
                counter = 0
                
    except KeyboardInterrupt:
        # Cleanup on exit
        service.pump_controller.stopSim()  # Changed from stop() to stopSim()
        cherrypy.engine.exit()
        print("Pump Controller Service Stopped")
    
