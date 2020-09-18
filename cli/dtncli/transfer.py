from dtnaas_client import Session, Service, NodeResponse
from ssh import get_pubkeys

def transfer(client, args):
    parts = args.split(" ")
    sess = client.getSession()
    for inst in parts:
        srv = Service(instances=['surf-dtn-ppc'],
                      image='dtnaas/gct',
                      profile='surf',
                      username='kissel',
                      public_key=get_pubkeys())
        sess.addService(srv)
    print (sess)
    ret = sess.start()
    print (ret)
    
