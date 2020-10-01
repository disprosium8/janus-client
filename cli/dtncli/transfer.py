from dtnaas_client import Session, Service, NodeResponse
from .ssh import ssh_cmd_tmux_window
from .util import col


def transfer(cfg, client, args):
    active = cfg['active']
    parts = args.split(" ")
    if len(parts) < 3 or len(parts) > 3:
        print (col.FAIL + "Invalid transfer specification, usage: transfer <src> <dst> <type>" + col.ENDC)

    src = parts[0]
    dst = parts[1]
    typ = parts[2]

    found = False
    for a in active:
        for k,v in a.items():
            if src in v['allocations'] and dst in v['allocations']:
                active = a[k]
                found = True
                print (col.ITEM + f"Found suitable existing session {k}" + col.ENDC)
                break

    if not found:
        # must allocate
        #sess = client.getSession()
        #for inst in parts:
        #    print (inst)
        """
        srv = Service(instances=['surf-dtn-ppc'],
                      image='dtnaas/gct',
                      profile='surf',
                      username='kissel',
                      public_key=get_pubkeys())
        sess.addService(srv)
        """
        #print (sess)
        #ret = sess.start()
        #print (ret)
        pass
    
    sinfo = active['services'][src][0]
    dinfo = active['services'][dst][0]

    spane = ssh_cmd_tmux_window(sinfo['ctrl_host'],
                                sinfo['ctrl_port'],
                                sinfo['container_user'],
                                "xfer_test -s -r")

    ip = sinfo['data_ipv4']
    dpane = ssh_cmd_tmux_window(dinfo['ctrl_host'],
                                dinfo['ctrl_port'],
                                dinfo['container_user'],
                                f"xfer_test -c {ip} -t 20 -i 2 -r")
