import json
import uuid
import logging
import requests
from enum import Enum

class State(Enum):
    INITIALIZED = 1
    STARTED = 2
    STOPPED = 3
    MIXED = 4
    CREATED = 5
    DESTROYED = 6

log = logging.getLogger(__name__)
API_PREFIX="/api/dtnaas/controller"

class SessionResponse(object):
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

class SessEndpointResponse(SessionResponse):
    def __str__(self):
        return '\n'.join([ "{}: {}".format(k,v) for k,v in self._data.items() ])

class SessStatusResponse(SessionResponse):
    def __str__(self):
        ret = ""
        for item in self._data:
            for k,v in item.items():
                for l,w in v['services'].items():
                    for s in w:
                        ret += "id: {}, service: {}, errors: {}\n".format(k, l, s['errors'])
        return ret

class Service(object):
    def __init__(self, instances=None, image=None, profile=None,
                 username=None, public_key=None, manifest=None, **kwargs):
        self._instances = instances
        self._image = image
        self._profile = profile
        self._username = username
        self._public_key = public_key
        self._kwargs = kwargs
        self._manifest = manifest
        
    def json(self):
        kwargs = self._kwargs
        if self._username:
            kwargs["USER_NAME"] = self._username
        if self._public_key:
            kwargs["PUBLIC_KEY"] = self._public_key
        ret = {"instances": self._instances,
               "image": self._image,
               "profile": self._profile,
               "kwargs": kwargs}
        return ret

    def endpoints(self):
        if not self._manifest:
            return None
        eps = dict()
        for k,v in self._manifest.items():
            for l,w in v['services'].items():
                for s in w:
                    if s['errors']:
                        eps.update({"{} (Errors)".format(l): "{}".format(s['errors'])})
                    else:
                        eps.update({l: "{}:{}".format(s['ctrl_host'], s['ctrl_port'])})
        return SessEndpointResponse(eps)

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

class ProfileResponse(Response):
    def __str__(self):
        if self.error():
            return super().__str__()
        return '\n'.join([ n for n in self.json() ])

class ActiveResponse(Response):
    def __str__(self):
        if self.error():
            return super().__str__()
        return '\n'.join([ "{}".format(*n) for n in self.json() ])

    def services(self):
        ret = dict()
        for item in self.json():
            for k,v in item.items():
                if k not in ret:
                    ret[k] = list()
                svc = v['services']
                for s in svc:
                    ret[k].append(Service(manifest=v))
        return ret
    
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

    def profiles(self, refresh=False):
        ep = '/profiles'
        if refresh:
            ep = "{}{}".format(ep, "?refresh=true")
        url = "{}{}".format(self.url, ep)
        return ProfileResponse(self._call("GET", url))

    def nodes(self, refresh=False):
        ep = '/nodes'
        if refresh:
            ep = "{}{}".format(ep, "?refresh=true")
        url = "{}{}".format(self.url, ep)
        return NodeResponse(self._call("GET", url))

    def create(self, req):
        hdr = {"Content-type": "application/json"}
        payload = json.dumps(req)
        url = "{}{}".format(self.url, '/create')
        return Response(self._call("POST", url, hdr, payload))

    def start(self, id):
        url = "{}{}/{}".format(self.url, '/start', id)
        return Response(self._call("PUT", url))

    def stop(self, id):
        url = "{}{}/{}".format(self.url, '/stop', id)
        return Response(self._call("PUT", url))

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
        elif op == "PUT":
            return requests.put(url, auth=auth)
        

class Session(object):
    TMPL="id: {}\nallocated: {}\nrequests: {}\nmanifest: {}\nstate: {}"
    
    def __init__(self, client, clone=None, json=None):
        self._id = uuid.uuid4()
        self._client = client
        self._allocated = False
        self._requests = list()
        self._manifest = dict()
        self._state = State.CREATED.name

        if clone:
            ret = self._client.active(Id=clone).json()
            for s in ret:
                for k,v in s.items():
                    self._manifest.update(s)
                    self._requests.extend(v['request'])
        if json:
            for k,v in json.items():
                self._manifest.update(json)
                self._requests.extend(v['request'])
                    
    def __str__(self):
        return self.__class__.TMPL.format(self._id,
                                          self._allocated,
                                          self._requests,
                                          self._manifest,
                                          self._state)

    def addService(self, srv):
        if type(srv) == Service:
            self._requests.append(srv.json())
        else:
            raise Exception("Not a valid Service object: {}".format(srv))

    def initialize(self):
        ret = self._client.create(self._requests)
        if not ret.error():
            self._manifest.update(ret.json())
        else:
            raise Exception("Error initializing service: {}".format(ret))
        return ret

    def destroy(self):
        for k,v in self._manifest.items():
            self._client.delete(k)
            self._state = State.DESTROYED.name

    def start(self):
        if self._state is not State.INITIALIZED.name:
            self.initialize()
        ret = dict()
        for k,v in self._manifest.items():
            ret = self._client.start(k)
            if not ret.error():
                self._manifest.update(ret.json())
            else:
                raise Exception("Error starting service: {}".format(ret))
            print (ret.json())
            self._state = ret.json()[k]['state']
        return ret

    def status(self):
        ret = list()
        for k in self._manifest.keys():
            ret.extend(self._client.active(Id=k).json())
        return SessStatusResponse(ret)

    def stop(self):
        for k,v in self._manifest.items():
            ret = self._client.stop(k)
            if ret.error():
                raise Exception("Error stopping service: {}".format(ret))
            self._state = ret.json()[k]['state']

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
