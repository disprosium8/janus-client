import time
from janus_client import Client, Session, Service

URL="https://localhost:5000"

user = 'admin'
passwd = 'admin'
mykey = 'ssh-rsa'

client = Client(URL, auth=(user, passwd))

print (client.nodes())
active = client.active()
services = client.active().services
print (active)
print (services)
for srv in services:
    for k,ep in srv.items():
        print (ep.endpoints())

print()

sess = client.getSession()
print (sess)
print()

srv = Service(instances=['local'],
              image='dtnaas/tools',
              profile='default',
              username=user,
              public_key=mykey)
sess.addService(srv)

sess.start()

print (sess.status())

time.sleep(2)

sess.stop()
sess.destroy()
