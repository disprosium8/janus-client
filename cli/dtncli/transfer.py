import time
import subprocess
from subprocess import PIPE, STDOUT
from dtnaas_client import Session, Service, NodeResponse
from .ssh import ssh_cmd_tmux_window, cmd_tmux_window
from .util import col


SSH_TMPL = "ssh -t -o StrictHostKeyChecking=no -l {user} -p {port} {host} {cmd}"

class ProcTransfer:
    def __init__(self, sproc, dproc):
        self._sproc = sproc
        self._dproc = dproc
        self._sbuf = bytes()
        self._dbuf = bytes()
        
    def getlog(self, dst=True):
        proc = self._dproc if dst else self._sproc
        try:
            outs, errs = proc.communicate(timeout=15)
        except TimeoutExpired:
            proc.kill()
            outs, errs = proc.communicate()

        print (errs)
        return outs

class MuxTransfer:
    def __init__(self, spane, dpane, src, dst, typ):
        self._src = src
        self._dst = dst
        self._typ = typ
        self._spane = spane
        self._dpane = dpane

    def __str__(self):
        return f"{self._src} -> {self._dst} [{self._typ}]"
        
    def getlog(self, dst=True, lines=10):
        pane = self._dpane if dst else self._spane
        ret = '\n'.join(pane.cmd('capture-pane', '-p').stdout[-lines:])
        return ret

    def stop(self):
        self._spane.window.kill_window()
        self._dpane.window.kill_window()

def transfer(cfg, client, args):
    active = cfg['active']
    parts = args.split(" ")
    
    if len(parts) < 3 or len(parts) > 3:
        print (col.FAIL + "Invalid transfer specification, usage: transfer <src> <dst> <type>" + col.ENDC)
        return False
        
    src, sfile = parts[0].split(":")
    dst, dfile = parts[1].split(":")
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
        print ("not matching active found")
        return

    sinfo = active['services'][src][0]
    dinfo = active['services'][dst][0]
    
    sip = sinfo['data_ipv4']
    dip = dinfo['data_ipv4']
    
    # XXX: this is where we need to be smarter and optimize params based on what's known/learned
    if typ == "rdma":
        scmd = f"xfer_test -c {dip} -i 2 -o 31 -a 4 -r -f {sfile}"
        dcmd = f"xfer_test -i 2 -s -r -f {dfile}"
        dpane = ssh_cmd_tmux_window(dinfo['ctrl_host'],
                                    dinfo['ctrl_port'],
                                    dinfo['container_user'],
                                    dcmd)
        
        time.sleep(2)
        
        spane = ssh_cmd_tmux_window(sinfo['ctrl_host'],
                                    sinfo['ctrl_port'],
                                    sinfo['container_user'],
                                    scmd)
    elif typ == "gridftp":
        cmd = f"globus-url-copy -vb -p 8 sshftp://{sinfo['ctrl_host']}:{sinfo['ctrl_port']}/{sfile} sshftp://{dinfo['ctrl_host']}:{dinfo['ctrl_port']}/{dfile}"
        spane = cmd_tmux_window(cmd)
        dpane = spane
    else:
        print (col.FAIL + f"Unknown transfer type \"{typ}\"" + col.ENDC)
        return False
        
    print (col.WARNING + f"Starting transfer for {src} -> {dst} using transfer type {typ}" + col.ENDC)
    return MuxTransfer(spane, dpane, src, dst, typ)
