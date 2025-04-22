import cherrypy
import json
import time
from TemperatureController import TempController
from CatalogClient import CatalogAPI, Catalog_Navigator

class TempControllerREST:
    exposed = True
    
    def __init__(self, settings):
        self.settings = settings
        self.catalog_navigator = Catalog_Navigator()
        
        # Initialize Temperature Controller
        self.temp_controller = TempController(settings)
        
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
    try:
        settings = json.load(open('settings.json'))
        if "clientID" not in settings:
            settings["clientID"] = "temp_controller_1"
    except Exception as e:
        print(f"Error loading settings: {e}")
        exit(1)

    # Initialize the service
    service = TempControllerREST(settings)
    
    # Register with catalog
    print("Registering service...")
    service.registerService()
    service.registerDevice()
    
    # Start MQTT client
    print("Starting MQTT client...")
    service.temp_controller.startSim()
    
    # Configure CherryPy
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': settings.get('servicePort', 8082)  # Different port than pump controller
    })
    
    cherrypy.tree.mount(service, '/', conf)
    
    try:
        # Start the service
        print("Starting REST API...")
        cherrypy.engine.start()
        
        # Service maintenance loop
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            
            # Periodically update (every 40 seconds)
            if counter >= 20:
                service.updateService()
                service.updateDevice()
                # Update subscriptions in case catalog changed
                service.temp_controller.update_subscriptions()
                counter = 0
                
    except KeyboardInterrupt:
        # Cleanup on exit
        print("Shutting down...")
        service.stop()
        cherrypy.engine.exit()
        print("Temperature Controller Service Stopped")