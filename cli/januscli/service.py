import time
from janus_client import Session, Service, NodeResponse
from .util import col
from .ssh import get_pubkeys


SRV_OPTS = ['create', 'start', 'stop', 'del']

def handle_service(client, args, cfg):
    parts = args.split(" ")
    if not args:
        print (col.ITEM + f"No argument, session options: {SRV_OPTS}" + col.ENDC)
        return
    if parts[0] not in SRV_OPTS:
        print (col.FAIL + f"Unknown service option \"{parts[0]}\"" + col.ENDC)
        return

    if parts[0] == "create":
        try:
            instances = parts[1].split(",")
            image = parts[3]
            profile = parts[5]
            
            sess = client.getSession()
            srv = Service(instances=instances,
                          image=image,
                          profile=profile,
                          username='janus',
                          public_key=get_pubkeys())
            sess.addService(srv)
            ret = sess.initialize()
            cfg['active'].append(ret.json())
            sid = next(iter(ret.json()))
            print (col.WARNING + f"Initialized new session with id \"{sid}\"" + col.ENDC)
            return True
        except Exception as e:
            print (col.FAIL + f"Could not create session: {e}" + col.ENDC)
    elif parts[0] == "start":
        if len(parts) < 2:
            print (col.FAIL + f"No session specified" + col.ENDC)
            return False

        try:
            key = parts[1]
            active = cfg['active']
            res = next((a for a in active if next(iter(a)) == key), None)
            if res:
                print (col.WARNING + f"Starting session \"{key}\"" + col.ENDC)
            else:
                print (col.FAIL + f"Session not found: \"{key}\"" + col.ENDC)
                return False
            
            ret = client.start(key)
            res.update(ret.json())
            return True
        except Exception as e:
            print (col.FAIL + f"Could not start session: {e}" + col.ENDC)
    elif parts[0] == "stop":
        if len(parts) < 2:
            print (col.FAIL + f"No session specified" + col.ENDC)
            return False

        try:
            key = parts[1]
            active = cfg['active']
            res = next((a for a in active if next(iter(a)) == key), None)
            if res:
                print (col.WARNING + f"Stopping session \"{key}\"" + col.ENDC)
            else:
                print (col.FAIL + f"Session not found: \"{key}\"" + col.ENDC)
                return False
            
            ret = client.stop(key)
            res.update(ret.json())
            return True
        except Exception as e:
            print (col.FAIL + f"Could not stop session: {e}" + col.ENDC)
    elif parts[0] == "del":
        if len(parts) < 2:
            print (col.FAIL + f"No session specified" + col.ENDC)
            return False

        try:
            key = parts[1]
            active = cfg['active']
            res = next((a for a in active if next(iter(a)) == key), None)
            if res:
                print (col.WARNING + f"Deleting session \"{key}\"" + col.ENDC)
            else:
                print (col.FAIL + f"Session not found: \"{key}\"" + col.ENDC)
                return False
            
            ret = client.delete(key)
            active.remove(res)
            return True
        except Exception as e:
            print (col.FAIL + f"Could not delete session: {e}" + col.ENDC)

        

