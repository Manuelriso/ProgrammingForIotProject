import cherrypy
import json
import requests

class CatalogREST(object):
    exposed=True
    def GET(self,*uri,**params):
        output={}
        
        with open("catalog.json","r") as file:
            data=json.load(file)
                
            
        if(uri[0]=="devices" and len(uri)==1):
            output=data["devices"]
            
        if(uri[0]=="numberOfArea" and len(uri)==1):
            output=data["numberOfAreas"]
        
        
        if(uri[0]=="services" and len(uri)==1):
            output=data["services"]
            
        
        if(uri[0]=="areas" and len(uri)==1):
            output=data["areas"]
         
         
            
        if(uri[0]=="areas" and len(uri)==2):
            requestedArea=int(uri[1])
            areas=data["areas"]
            for registeredArea in areas:
                if(registeredArea["ID"]==requestedArea):
                    output=registeredArea
        
        
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
            data["services"]=services
            with open("catalog.json","w") as file:
                json.dump(data,file,indent=4)
            
            return json.dumps(data)
        
        if(uri[0]=="area"):
            area=json.loads(body)
            with open("catalog.json","r") as file:
                data=json.load(file)
            areas=data["areas"]
            numberOfAreas=data["numberOfAreas"]
            for registeredArea in areas:
                if(area["ID"]==registeredArea["ID"]):
                    raise cherrypy.HTTPError(404,"Error in the id")
            areas.append(area)
            numberOfAreas+=1
            data["areas"]=services
            data["numberOfAreas"]=numberOfAreas
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
        
        
        if(uri[0]=="area"):
            area=json.loads(body)
            
            with open("catalog.json","r") as file:
                    data=json.load(file)
            
            updatedAreas=[]
            for registeredArea in data["areas"]:
                if(registeredArea["ID"]==area["ID"]):
                    updatedAreas.append(area)
                else:
                    updatedAreas.append(registeredArea)
            
            data["areas"]=updatedAreas
            with open("catalog.json","w")as file:
                json.dump(data,file,indent=4)
            
        return json.dumps(data)


if __name__=="__main__":
    catalogClient = CatalogREST()
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
        