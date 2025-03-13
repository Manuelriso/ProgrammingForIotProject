import cherrypy
import json
import requests

class CatalogREST(object):
    exposed=True
    def GET(self,*uri,**params):
        output={}
        
        with open("catalog.json","r") as file:
            data=json.load(file)
            
        
        if(uri[0]=="mqtt"):
            broker=data["messageBroker"]
            output["ipAddress"]=broker["ipAddress"]
            output["port"]=broker["port"]
        
            
        if(uri[0]=="devices" and len(uri)==1):
            output=data["devices"]
        
        
        if(uri[0]=="services" and len(uri)==1):
            output=data["services"]
        
        return json.dumps(output)
    
    
    
    def POST(self,*uri,**params):
        body=cherrypy.request.body.read()
        if(uri[0]=="device"):
            device=json.loads(body)
            with open("catalog.json","r") as file:
                data=json.load(file)
            devices=data["devices"]
            for registeredDevice in devices:
                if(device["ID"]==registeredDevice["ID"]):
                    raise cherrypy.HTTPError(404,"Error in the id")
            devices.append(device)
            data["devices"]=devices
            with open("catalog.json","w") as file:
                json.dump(data,file,indent=4)
                
            return json.dumps(data)
        
        if(uri[0]=="service"):
            service=json.loads(body)
            with open("catalog.json","r") as file:
                data=json.load(file)
            services=data["services"]
            for registeredService in services:
                if(service["ID"]==registeredService["ID"]):
                    raise cherrypy.HTTPError(404,"Error in the id")
            services.append(service)
            data["users"]=services
            with open("catalog.json","w") as file:
                json.dump(data,file,indent=4)
            
            return json.dumps(data)
        
        
                
    def PUT(self,*uri,**params):
        body=cherrypy.request.body.read()
        
        if(uri[0]=="device"):
            device=json.loads(body)
            
            with open("catalog.json","r") as file:
                    data=json.load(file)
            
            updatedDevices=[]
            for registeredDevice in data["devices"]:
                if(registeredDevice["ID"]==device["ID"]):
                    updatedDevices.append(device)
                else:
                    updatedDevices.append(registeredDevice)
            
            data["devices"]=updatedDevices
            with open("catalog.json","w")as file:
                json.dump(data,file,indent=4)
                
        
        if(uri[0]=="service"):
            service=json.loads(body)
            
            with open("catalog.json","r") as file:
                    data=json.load(file)
            
            updatedServices=[]
            for registeredService in data["services"]:
                if(registeredService["ID"]==service["ID"]):
                    updatedServices.append(service)
                else:
                    updatedServices.append(registeredService)
            
            data["services"]=updatedServices
            with open("catalog.json","w")as file:
                json.dump(data,file,indent=4)
            
        return json.dumps(data)


if __name__=="__main__":
    catalogClient = CatalogREST("catalog.json")
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 80})
    #cherrypy.config.update({'server.socket_port': 8080})
    cherrypy.tree.mount(catalogClient, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()
        