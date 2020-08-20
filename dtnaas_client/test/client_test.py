import time
from dtnaas_client import Client, Session

URL="http://localhost:5000"

user = 'admin'
mykey = 'ssh-rsa'

client = Client(URL, auth=(user, 'pass'))

print (client.nodes())
print (client.active())

print()

sess = client.getSession()
print (sess)
print()

srv = Service(instances=['odroidc2'],
              image='dtnaas/gct:latest',
              profile='arm64',
              username=user,
              public_key=mykey)
sess.addService(srv)

sess.start()

print (sess)

time.sleep(2)

sess.stop()
