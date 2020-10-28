import os
import time
import json
import subprocess
from subprocess import PIPE, STDOUT
from dtnaas_client import Session, Service, NodeResponse
from .ssh import ssh_cmd_tmux_window, cmd_tmux_window
from .util import col
from pygments import highlight, lexers, formatters

try:
    from zx.client import Client as zxClient
    from zx.client import HTTPError, APIError
    from zx.const import *
    zx_enabled = True
except:
    print ("Zettar\t: Not available")
    zx_enabled = False
    
SSH_TMPL = "ssh -t -o StrictHostKeyChecking=no -l {user} -p {port} {host} {cmd}"

class zxTransfer:
    site_map = {
        "nersc-tbn-6": "RsiteA",
        "nersc-tbn-7": "RsiteB"
    }
    
    def __init__(self, zxc, task, src, dst, typ):
        self._zxc = zxc
        self._task = task
        self._src = src
        self._dst = dst
        self._typ = typ

    def __str__(self):
        return f"{self._src} -> {self._dst} [{self._typ}]"
        
    def getlog(self, dst=True):
        if dst:
            zxc = zxClient(self._dst, 8443, "zx", "zx")
            tasks = zxc.list_tasks([OPT_HASH])
            task = next((s for s in tasks if s['hash'] == self._task['hash']), None)
            if not task:
                return dict({"error": "Destination task not found"})
        else:
            zxc = self._zxc
            task = self._task

        task = zxc.read_task(task['id'])
        jstr = json.dumps(task, sort_keys=True, indent=4)
        coljson = highlight(jstr, lexers.JsonLexer(), formatters.TerminalFormatter())
        return coljson

    def stop(self):
        try:
            self._zxc.remove_task(self._task['id'])
        except Exception as e:
            print (col.FAIL + f"Failed to remove src task \"{self._task[hash]}\": {e}" + col.ENDC)

        try:
            zxc = zxClient(self._dst, 8443, "zx", "zx")
            tasks = zxc.list_tasks([OPT_HASH])
            task = next((s for s in tasks if s['hash'] == self._task['hash']), None)
            zxc.remove_task(task['id'])
        except Exception as e:
            print (col.FAIL + f"Failed to remove dst task \"{task[hash]}\": {e}" + col.ENDC)
            
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
        
    def getlog(self, dst=True, lines=5):
        pane = self._dpane if dst else self._spane
        ret = '\n'.join(pane.cmd('capture-pane', '-p').stdout[-lines:])
        return ret

    def stop(self):
        self._spane.window.kill_window()
        self._dpane.window.kill_window()

def _rdma_xfer(sinfo, dinfo, src, dst, sfile, dfile, typ):
    sip = sinfo['data_ipv4']
    dip = dinfo['data_ipv4']

    scmd = f"xfer_test -c {dip} -i 2 -o 31 -a 4 -r -f {sfile}"
    dcmd = f"xfer_test -i 2 -s -r -f {dfile}"
    dpane = ssh_cmd_tmux_window(dinfo['ctrl_host'],
                                dinfo['ctrl_port'],
                                dinfo['container_user'],
                                dcmd)
    
    time.sleep(3)
    
    spane = ssh_cmd_tmux_window(sinfo['ctrl_host'],
                                sinfo['ctrl_port'],
                                sinfo['container_user'],
                                scmd)
    return MuxTransfer(spane, dpane, src, dst, typ)

def _griftp_xfer(sinfo, dinfo, src, dst, sfile, dfile, typ):
    cmd = f"globus-url-copy -vb -p 32 -bs 4M sshftp://{sinfo['container_user']}@{sinfo['ctrl_host']}:{sinfo['ctrl_port']}/{sfile} sshftp://{dinfo['container_user']}@{dinfo['ctrl_host']}:{dinfo['ctrl_port']}/{dfile}"
    spane = cmd_tmux_window(cmd)
    dpane = spane
    return MuxTransfer(spane, dpane, src, dst, typ)

def _zx_xfer(sinfo, dinfo, src, dst, sfile, dfile, typ):
    if not zx_enabled:
        print (col.FAIL + f"Transfer type \"{typ}\" not available" + col.ENDC)
        return False

    dname = zxTransfer.site_map.get(dst, None)
    if not dname:
        print (col.FAIL + f"Could not find remote Zettar site with name \"{dst}\"" + col.ENDC)
        return False

    try:
        zxc = zxClient(src, 8443, "zx", "zx")
        sites = zxc.list_sites([OPT_NAME])
        zdst = next((s for s in sites if s['name'] == dname), None)
        
        path = os.path.dirname(sfile)
        dataset = [os.path.basename(sfile)]
        fields = {OPT_NAME:	f"dtncli transfer ({src} -> {dst})",
                  OPT_COMMENTS: "zx-pysdk transfer"}
        task = zxc.add_task([zdst['id']], path, dataset, 32*1024*1024, create_paused=False, fields=fields)
    except HTTPError as e:
        print(col.FAIL + f"{e.code}: {e.reason}" + col.ENDC)
        return False
    except APIError as e:
        print(col.FAIL + f"{e}" + col.ENDC)
        return False
    except Exception as e:
        print(col.FAIL + f"Error: {e}" + col.ENDC)
        return False

    return zxTransfer(zxc, task, src, dst, typ)
    
def transfer(cfg, client, args):
    active = cfg['active']
    parts = args.split(" ")
    
    try:
        if len(parts) < 3 or len(parts) > 3:
            raise Exception()
        src, sfile = parts[0].split(":")
        dst, dfile = parts[1].split(":")
        typ = parts[2]
    except:
        print (col.FAIL + "Invalid transfer specification, usage: transfer <src:path> <dst:path> <type>" + col.ENDC)
        return False

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
        print (col.FAIL + "No suitable sessions found" + col.ENDC)
        return False

    sinfo = active['services'][src][0]
    dinfo = active['services'][dst][0]
    
    # The transfer object to return
    xfer = None
    # XXX: this is where we need to be smarter and optimize params based on what's known/learned
    if typ == "rdma":
        xfer = _rdma_xfer(sinfo, dinfo, src, dst, sfile, dfile, typ)
    elif typ == "gridftp":
        xfer = _gridftp_xfer(sinfo, dinfo, src, dst, sfile, dfile, typ)
    elif typ == "zx":
        xfer = _zx_xfer(sinfo, dinfo, src, dst, sfile, dfile, typ)
    else:
        print (col.FAIL + f"Unknown transfer type \"{typ}\"" + col.ENDC)
        return False

    if xfer:
        print (col.WARNING + f"Starting transfer for {src} -> {dst} using transfer type {typ}" + col.ENDC)
    return xfer
