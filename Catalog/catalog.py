import cherrypy
import json
import requests

class WebService(object):
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
        elif(uri[0]=="devices"):
            devices=data["devices"]
            for device in devices:
                if(device["deviceID"]==uri[1]):
                    output["device"]=device
        
        
        if(uri[0]=="users" and len(uri)==1):
            output=data["users"]
        elif(uri[0]=="users"):
            users=data["users"]
            for user in users:
                if(user["userID"]==uri[1]):
                    output["user"]=user
        return json.dumps(output)
    
    def POST(self,*uri,**params):
        body=cherrypy.request.body.read()
        if(uri[0]=="device"):
            device=json.loads(body)
            with open("catalog.json","r") as file:
                data=json.load(file)
            devices=data["devices"]
            for registeredDevice in devices:
                if(device["deviceID"]==registeredDevice["deviceID"]):
                    raise cherrypy.HTTPError(404,"Error in the id")
            devices.append(device)
            data["devices"]=devices
            with open("catalog.json","w") as file:
                json.dump(data,file,indent=4)
                
            return json.dumps(data)
        
        if(uri[0]=="user"):
            user=json.loads(body)
            with open("catalog.json","r") as file:
                data=json.load(file)
            users=data["users"]
            for registeredUser in users:
                if(user["userID"]==registeredUser["userID"]):
                    raise cherrypy.HTTPError(404,"Error in the id")
            users.append(device)
            data["users"]=users
            with open("catalog.json","w") as file:
                json.dump(data,file,indent=4)
            
            return json.dumps(data)
                
    def PUT(self,*uri,**params):
        body=cherrypy.request.body.read()
        device=json.loads(body)
        
        with open("catalog.json","r") as file:
                data=json.load(file)
        
        updatedDevices=[]
        for registeredDevice in data["devices"]:
            if(registeredDevice["deviceID"]==device["deviceID"]):
                updatedDevices.append(device)
            else:
                updatedDevices.append(registeredDevice)
        
        data["devices"]=updatedDevices
        with open("catalog.json","w")as file:
            json.dump(data,file,indent=4)
            
        return json.dumps(data)


if __name__=="__main__":
    conf={
        '/':{
            'request.dispatch':cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on':True
        }
    }
    webService=WebService()
    cherrypy.tree.mount(webService,'/',conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
        