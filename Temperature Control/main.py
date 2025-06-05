import cherrypy
import json
import time
from TemperatureController import TempController
from CatalogClient import CatalogAPI, Catalog_Navigator

if __name__ == "__main__":
    # Load settings
    settings = json.load(open('settings.json'))
    
    # Initialize components directly
    catalog_navigator = Catalog_Navigator(settings=settings)  # Pass settings here
    catalog_api = CatalogAPI(catalog_navigator, settings)
    pump_controller = TempController(settings)
    time.sleep(2)
    # Register the service
    catalog_api.registerService()
    
    # Start the MQTT client
    pump_controller.startSim()
    
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
    
    # Mount the CatalogAPI instance if you need REST endpoints
    cherrypy.tree.mount(catalog_api, '/', conf)
    
    try:
        cherrypy.engine.start()
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            
            # Update every 30 seconds (15*2)
            if counter >= 15:
                catalog_api.updateService()
                pump_controller.update_subscriptions()
                counter = 0
                
    except KeyboardInterrupt:
        # Cleanup
        pump_controller.stopSim()
        cherrypy.engine.exit()
        print("Service stopped gracefully")