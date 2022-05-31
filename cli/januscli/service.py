import time
from janus_client import Session, Service, NodeResponse
from .util import col
from .ssh import get_pubkeys
from .util import CText

cout = CText()

SRV_OPTS = ['create', 'start', 'stop', 'del']

def handle_service(client, args, cfg):
    parts = args.split(" ")
    if not args:
        cout.item(f"No argument, session options: {SRV_OPTS}")
        return
    if parts[0] not in SRV_OPTS:
        cout.error(f"Unknown service option \"{parts[0]}\"")
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
            cout.warn(f"Initialized new session with id \"{sid}\"")
            return True
        except Exception as e:
            cout.error(f"Could not create session: {e}")
    elif parts[0] == "start":
        if len(parts) < 2:
            cout.error(f"No session specified")
            return False

        try:
            key = parts[1]
            active = cfg['active']
            res = next((a for a in active if next(iter(a)) == key), None)
            if res:
                cout.warn(f"Starting session \"{key}\"")
            else:
                cout.error(f"Session not found: \"{key}\"")
                return False

            ret = client.start(key)
            res.update(ret.json())
            return True
        except Exception as e:
            cout.error(f"Could not start session: {e}")
    elif parts[0] == "stop":
        if len(parts) < 2:
            cout.error(f"No session specified")
            return False

        try:
            key = parts[1]
            active = cfg['active']
            res = next((a for a in active if next(iter(a)) == key), None)
            if res:
                cout.warn(f"Stopping session \"{key}\"")
            else:
                cout.error(f"Session not found: \"{key}\"")
                return False

            ret = client.stop(key)
            res.update(ret.json())
            return True
        except Exception as e:
            cout.error(f"Could not stop session: {e}")
    elif parts[0] == "del":
        if len(parts) < 2:
            cout.error(f"No session specified")
            return False

        try:
            key = parts[1]
            active = cfg['active']
            res = next((a for a in active if next(iter(a)) == key), None)
            if res:
                cout.warn(f"Deleting session \"{key}\"")
            else:
                cout.error(f"Session not found: \"{key}\"")
                return False

            ret = client.delete(key)
            if ret.error():
                cout.error(f"Could not clear remote state: {ret}")
                return False
            active.remove(res)
            return True
        except Exception as e:
            cout.error(f"Could not delete session: {e}")


