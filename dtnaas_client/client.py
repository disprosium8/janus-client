import json
import uuid
import logging
import requests

log = logging.getLogger(__name__)
API_PREFIX="/api/dtnaas/controller"

class SessEndpointResponse(object):
    def __init__(self, data):
        self._data = data

    def __str__(self):
        return '\n'.join([ "{}: {}".format(k,v) for k,v in self._data.items() ])

    def json(self):
        return self._data
    
class Response(object):
    def __init__(self, res):
        self._data = res

    def __str__(self):
        return "{} {}".format(self._data.status_code,
                              self._data.text)
        
    def json(self):
        return self._data.json()

    def error(self):
        if self._data.status_code > 400:
            return True
        else:
            return False
    
class NodeResponse(Response):
    def __str__(self):
        if self.error():
            return super().__str__()
        return '\n'.join([ n['name'] for n in self.json() ])

class CreateResponse(Response):
    pass

class ActiveResponse(Response):
    def __str__(self):
        if self.error():
            return super().__str__()
        return '\n'.join([ "{}".format(*n) for n in self.json() ])
    
class Client(object):
    def __init__(self, url=None, auth=None):
        self.url = "{}{}".format(url, API_PREFIX)
        self.auth = auth

    def setURL(self, url):
        self.url = url

    def getSession(self, clone=None):
        return Session(self, clone)

    def config(self):
        print ("URL: ".format(self.url))
    
    def nodes(self):
        url = "{}{}".format(self.url, '/nodes')
        return NodeResponse(self._call("GET", url))

    def create(self, req):
        hdr = {"Content-type": "application/json"}
        payload = json.dumps(req)
        url = "{}{}".format(self.url, '/create')
        return CreateResponse(self._call("POST", url, hdr, payload))

    def delete(self, Id):
        url = "{}{}".format(self.url, '/active/{}'.format(Id))
        return Response(self._call("DELETE", url))
    
    def active(self, Id=None, user=None):
        url = "{}{}".format(self.url, '/active')
        if Id:
            url = "{}/{}".format(url, Id)
        elif user:
            url = "{}/{}".format(url, user)
        return ActiveResponse(self._call("GET", url))

    def _call(self, op, url, hdrs=None, data=None, auth=None):
        if not auth:
            auth = self.auth
        if op == "POST":
            return requests.post(url, headers=hdrs, data=data, auth=auth)
        elif op == "GET":
            return requests.get(url, auth=auth)
        elif op == "DELETE":
            return requests.delete(url, auth=auth)
        

class Session(object):
    TMPL="id: {}\nallocated: {}\nrequests: {}\nmanifest: {}"
    
    def __init__(self, client, clone=None):
        self._id = uuid.uuid4()
        self._client = client
        self._allocated = False
        self._requests = list()
        self._manifest = dict()

        if clone:
            ret = self._client.active(Id=clone).json()
            for s in ret:
                for k,v in s.items():
                    self._manifest.update(s)
                    self._requests.extend(v['request'])

    def __str__(self):
        return self.__class__.TMPL.format(self._id,
                                          self._allocated,
                                          self._requests,
                                          self._manifest)

    def addInstance(self, instances, image, profile=None):
        self._requests.append({"instances": instances,
                               "image": image,
                               'profile': profile})

    def start(self):
        ret = self._client.create(self._requests)
        if not ret.error():
            self._manifest.update(ret.json())
        return ret

    def status(self):
        ret = list()
        for k in self._manifest.keys():
            ret.extend(self._client.active(Id=k).json())
        return ret

    def stop(self):
        for k,v in self._manifest.items():
            self._client.delete(k)

    def endpoints(self):
        eps = dict()
        for k,v in self._manifest.items():
            for l,w in v['services'].items():
                for s in w:
                    if s['errors']:
                        eps.update({"{} (Errors)".format(l): "{}".format(s['errors'])})
                    else:
                        eps.update({l: "{}:{}".format(s['ctrl_host'], s['ctrl_port'])})
        return SessEndpointResponse(eps)
