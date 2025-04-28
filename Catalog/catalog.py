import cherrypy
import json
import requests

class CatalogREST(object):
    exposed=True
    def GET(self,*uri,**params):
        print(f"Richiesta ricevuta - URI: {uri}, Parametri: {params}")
        output={}
        
        with open("catalog.json","r") as file:
            data=json.load(file)
                
            
        if(len(uri)==1 and uri[0]=="devices"):
            output["devices"]=data["devices"]
         
         
        #greenhouse1/numberOfAreas   
        if(len(uri)==2 and uri[1]=="numberOfAreas"):
            greenhouse=int(uri[0].replace("greenhouse",""))
            AllGreenhouse=data["greenhouses"]
            
            for registeredGreenHouse in AllGreenhouse:
                if(registeredGreenHouse["greenhouseID"]==greenhouse):
                    output["numberOfAreas"]=registeredGreenHouse["numberOfAreas"]
        
        
        if(len(uri)==1 and uri[0]=="services"):
            output["services"]=data["services"]
            
        
        #greenhouse1/areas
        if(len(uri)==2 and uri[1]=="areas"):
            greenhouse=int(uri[0].replace("greenhouse",""))
            AllGrennhouse=data["greenhouses"]
            
            for registeredGreenHouse in AllGrennhouse:
                if(registeredGreenHouse["greenhouseID"]==greenhouse):
                    output["areas"]=registeredGreenHouse["areas"]
        
        
        #greenhouses     
        if(len(uri)==1 and uri[0]=="greenhouses"):
            output["greenhouses"]=data["greenhouses"]
            print(str(output))
         
         
        #greenhouse1/areas/1    
        if(len(uri)==3 and uri[1]=="areas"):
            requestedArea=int(uri[2])
            greenhouse=int(uri[0].replace("greenhouse",""))
            AllGreenhouse=data["greenhouses"]
            
            for registeredGreenHouse in AllGreenhouse:
                if(registeredGreenHouse["greenhouseID"]==greenhouse):
                    areas=registeredGreenHouse["areas"]
                    
            for registeredArea in areas:
                if(registeredArea["ID"]==requestedArea):
                    output=registeredArea
                    
        
        #greenhouses/1
        if(len(uri)==2 and uri[0]=="greenhouses"):
            requestedGreenHouses=int(uri[1])
            greenhouses=data["greenhouses"]
            for registeredGreenHouse in greenhouses:
                if(registeredGreenHouse["greenhouseID"]==requestedGreenHouses):
                    output=registeredGreenHouse
        
        return json.dumps(output)
    
    
    
    def POST(self,*uri,**params):
        body=cherrypy.request.body.read()
        
        if(len(uri)==1 and uri[0]=="device"):
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
        
        if(len(uri)==1 and uri[0]=="service"):
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
        
        
        #/greenhouse1/area
        if(len(uri)==2 and uri[1]=="area"):
            greenhouseRequested=int(uri[0].replace("greenhouse",""))
            area=json.loads(body)
            
            with open("catalog.json","r") as file:
                data=json.load(file)
            
            greenhouses=data["greenhouses"]
            for registeredGreenHouse in greenhouses:
                if(greenhouseRequested==registeredGreenHouse["greenhouseID"]):
                    greenhouse=registeredGreenHouse
            
            areas=greenhouse["areas"]
            numberOfAreas=greenhouse["numberOfAreas"]
            for registeredArea in areas:
                if(area["ID"]==registeredArea["ID"]):
                    raise cherrypy.HTTPError(404,"Error in the id")
            areas.append(area)
            numberOfAreas+=1
            greenhouse["areas"]=areas
            greenhouse["numberOfAreas"]=numberOfAreas
            
            updatedGreenhouses=[]
            for registeredGreenhouses in data["greenhouses"]:
                if(registeredGreenhouses["greenhouseID"]==greenhouse["greenhouseID"]):
                    updatedGreenhouses.append(greenhouse)
                else:
                    updatedGreenhouses.append(registeredGreenhouses)
            
            
            data["greenhouses"]=updatedGreenhouses
            with open("catalog.json","w") as file:
                json.dump(data,file,indent=4)
            
            return json.dumps(data)
        
        #/greenhouse
        if(len(uri)==1 and uri[0]=="greenhouse"):
            greenhouse=json.loads(body)
            with open("catalog.json","r") as file:
                data=json.load(file)
            greenhouses=data["greenhouses"]
            for registeredGreenHouse in greenhouses:
                if(greenhouse["greenhouseID"]==registeredGreenHouse["greenhouseID"]):
                    raise cherrypy.HTTPError(404,"Error in the id")
            greenhouses.append(greenhouse)
            data["greenhouses"]=greenhouses
            with open("catalog.json","w") as file:
                json.dump(data,file,indent=4)
            
            return json.dumps(data)
        
        
                
    def PUT(self,*uri,**params):
        body=cherrypy.request.body.read()
        
        if(len(uri)==1 and uri[0]=="device"):
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
            
            return json.dumps(data)
                
        
        if(len(uri)==1 and uri[0]=="service"):
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
        
        
        if(len(uri)==1 and uri[0]=="greenhouse"):
            greenhouse=json.loads(body)
            
            with open("catalog.json","r") as file:
                    data=json.load(file)
            
            updatedGreenhouses=[]
            for registeredGreenhouse in data["greenhouses"]:
                if(registeredGreenhouse["greenhouseID"]==greenhouse["greenhouseID"]):
                    updatedGreenhouses.append(greenhouse)
                else:
                    updatedGreenhouses.append(registeredGreenhouse)
            
            data["greenhouses"]=updatedGreenhouses
            with open("catalog.json","w")as file:
                json.dump(data,file,indent=4)
            
            return json.dumps(data)
        
        #/greenhouse1/area
        if(len(uri)==2 and uri[1]=="area"):
            greenhouseRequested=int(uri[0].replace("greenhouse",""))
            area=json.loads(body)
            
            with open("catalog.json","r") as file:
                    data=json.load(file)
                    
            greenhouses=data["greenhouses"]
            for registeredGreenHouse in greenhouses:
                if(greenhouseRequested==registeredGreenHouse["greenhouseID"]):
                    greenhouse=registeredGreenHouse
            
            areas=greenhouse["areas"]
            
            updatedAreas=[]
            for registeredArea in areas:
                if(registeredArea["ID"]==area["ID"]):
                    updatedAreas.append(area)
                else:
                    updatedAreas.append(registeredArea)
                    
            greenhouse["areas"]=updatedAreas
            
            updatedGreenhouses=[]
            for registeredGreenhouses in data["greenhouses"]:
                if(registeredGreenhouses["greenhouseID"]==greenhouse["greenhouseID"]):
                    updatedGreenhouses.append(greenhouse)
                else:
                    updatedGreenhouses.append(registeredGreenhouses)
            
            
            data["greenhouses"]=updatedGreenhouses
            with open("catalog.json","w")as file:
                json.dump(data,file,indent=4)
            
            return json.dumps(data)
         
        
        #Called by Security microservice every time there's an alert
        #/greenhouse1/area1/motion  
        if(len(uri)==3 and uri[2]=="motion"):
            greenhouseRequested=int(uri[0].replace("greenhouse",""))
            areaID=int(uri[1].replace("area",""))
            
            with open("catalog.json","r") as file:
                    data=json.load(file)
                    
                    
            greenhouses=data["greenhouses"]
            for registeredGreenHouse in greenhouses:
                if(greenhouseRequested==registeredGreenHouse["greenhouseID"]):
                    greenhouse=registeredGreenHouse
            
            if greenhouse is None:
                raise cherrypy.HTTPError(404, "Greenhouse not found")
            
            areas=greenhouse["areas"]
            
            updatedAreas=[]
            for registeredArea in areas:
                if(registeredArea["ID"]==areaID):
                    registeredArea["motionDetected"]+=1
                    updatedAreas.append(registeredArea)
                else:
                    updatedAreas.append(registeredArea)
            
            
            greenhouse["areas"]=updatedAreas
            
            updatedGreenhouses=[]
            for registeredGreenhouses in data["greenhouses"]:
                if(registeredGreenhouses["greenhouseID"]==greenhouse["greenhouseID"]):
                    updatedGreenhouses.append(greenhouse)
                else:
                    updatedGreenhouses.append(registeredGreenhouses)
            
            
            data["greenhouses"]=updatedGreenhouses
            with open("catalog.json","w")as file:
                json.dump(data,file,indent=4)
            return json.dumps(data)
        
        
    def DELETE(self,*uri,**params):
            body=cherrypy.request.body.read()
            
            #greenhouse/1 it deletes the greenhouse with ID=1
            if(len(uri)==2 and uri[0]=="greenhouse"):
                grennhouseID=int(uri[1])
                
                with open("catalog.json","r") as file:
                        data=json.load(file)
                
                updatedGreenhouses=[]
                for registeredGreenhouse in data["greenhouses"]:
                    if(registeredGreenhouse["greenhouseID"]==grennhouseID):
                        continue
                    else:
                        updatedGreenhouses.append(registeredGreenhouse)
                
                data["greenhouses"]=updatedGreenhouses
                with open("catalog.json","w")as file:
                    json.dump(data,file,indent=4)
                
                return json.dumps(data)
            
            
            #greenhouse1/area/1 it deletes the area with ID=1 in the greenhouse 1
            if(len(uri)==3 and uri[1]=="area"):
                grennhouseID=int(uri[0].replace("greenhouse",""))
                areaID=int(uri[2])
                
                with open("catalog.json","r") as file:
                        data=json.load(file)
                
                greenhouses=data["greenhouses"]
                for registeredGreenHouse in greenhouses:
                    if(grennhouseID==registeredGreenHouse["greenhouseID"]):
                        greenhouse=registeredGreenHouse
                
                if greenhouse is None:
                    raise cherrypy.HTTPError(404, "Greenhouse not found")
                areas=greenhouse["areas"]
                
                updatedAreas=[]
                for registeredArea in areas:
                    if(registeredArea["ID"]==areaID):
                        continue
                    else:
                        updatedAreas.append(registeredArea)
                
                
                greenhouse["areas"]=updatedAreas
                greenhouse["numberOfAreas"]=len(updatedAreas)
                
                updatedGreenhouses=[]
                for registeredGreenhouses in data["greenhouses"]:
                    if(registeredGreenhouses["greenhouseID"]==greenhouse["greenhouseID"]):
                        updatedGreenhouses.append(greenhouse)
                    else:
                        updatedGreenhouses.append(registeredGreenhouses)
                
                
                data["greenhouses"]=updatedGreenhouses
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
        