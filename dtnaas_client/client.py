import json
import uuid
import logging
import requests

log = logging.getLogger(__name__)
API_PREFIX="/api/dtnaas/controller"

class Response(object):
    def __init__(self, res):
        self._data = res

    def __str__(self):
        return "{} {}".format(self._data.status_code,
                              self._data.text)
        
    def json(self):
        return self._data.json()

class NodeResponse(Response):
    def __str__(self):
        return '\n'.join([ n['name'] for n in self._data.json() ])

class CreateResponse(Response):
    def __str__(self):
        return self._data.json()

class ActiveResponse(Response):
    def __str__(self):
        return "Active: "
    
class Client(object):
    def __init__(self, url=None):
        self.url = "{}{}".format(url, API_PREFIX)

    def setURL(self, url):
        self.url = url

    def getSession(self):
        return Session(self)

    def config(self):
        print ("URL: ".format(self.url))
    
    def nodes(self):
        url = "{}{}".format(self.url, '/nodes')
        return NodeResponse(requests.get(url))

    def create(self, req):
        hdr = {"Content-type": "application/json"}
        payload = json.dumps(req)
        url = "{}{}".format(self.url, '/create')
        return CreateResponse(requests.post(url, headers=hdr, data=payload))

    def delete(self, Id):
        url = "{}{}".format(self.url, '/active/{}'.format(Id))
        return Response(requests.delete(url))
    
    def active(self):
        url = "{}{}".format(self.url, '/active')
        return ActiveResponse(requests.get(url))

class Session(object):
    TMPL="id: {}\nallocated: {}\nrequests: {}\nmanifest: {}"
    
    def __init__(self, client):
        self._id = uuid.uuid4()
        self._client = client
        self._allocated = False
        self._requests = dict()
        self._manifest = dict()
        
    def __str__(self):
        return self.__class__.TMPL.format(self._id,
                                          self._allocated,
                                          self._requests,
                                          self._manifest)
        
    def addInstance(self, instances, image, profile=None):
        self._requests = {"instances": instances,
                          "image": image,
                          'profile': profile}

    def start(self):
        ret = self._client.create(self._requests)
        self._manifest = ret.json()
        return ret
        
    def stop(self):
        for k,v in self._manifest.items():
            self._client.delete(k)
