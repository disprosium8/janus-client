import time
from dtnaas_client import Client, Session

URL="http://localhost:5000"

client = Client(URL)

print (client.nodes())
print (client.active())

print()

sess = client.getSession()
print (sess)
print()

sess.addInstance(['nersc-tbn-6', 'nersc-tbn-7'], 'gcsv5')
sess.start()

print (sess)

time.sleep(2)

sess.stop()
