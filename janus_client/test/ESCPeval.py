import os
import sys
import time
import logging
import subprocess
import threading
from IPython.display import display
import ipywidgets as widgets
from subprocess import PIPE, STDOUT
from ipaddress import IPv4Network, IPv4Address


logging.basicConfig(stream=sys.stdout,
                    format='[%(asctime)s] %(levelname)s: %(msg)s',
                    level=logging.INFO)
log = logging.getLogger("ESCPeval")

def run_host_cmd(host, user, cmd, interactive=False, out=None, keypath=None):
    log.debug(f"Running \"{cmd}\" on \"{host}\"")
    init_cmd = ["ssh", "-tt", "-o", "StrictHostKeyChecking=no"]
    if keypath:
        init_cmd += ["-i", keypath]
    hstr = host
    parts = host.split(":")
    if len(parts) > 1:
        hstr = parts[0]
        init_cmd += ["-p", parts[1]]
    if user:
        hstr = f"{user}@{hstr}"
    rcmd = init_cmd + [hstr] + cmd.split(" ")
    log.debug(rcmd)
    #print (rcmd)
    proc = subprocess.Popen(rcmd, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
    try:
        if interactive:
            for p in proc.stdout:
                if out:
                    out.append_stdout(p.decode('utf-8'))
                else:
                    print (p.decode('utf-8'), end='')
        outs, errs = proc.communicate()
    except Exception as e:
        print (e)
        proc.kill()
        outs, errs = proc.communicate()
    if errs and not interactive:
        print (errs)
    return

def setup(sess, user=None, keypath=None):
    res = sess.status().json()[0]
    for idx,ep in sess.endpoints().json().items():
        
        # Setup ssh for some tools
        log.info(f"Setting up environment on {idx}")
        
        cmd = "echo -e 'Host *\n\tStrictHostKeyChecking no' > ~/.ssh/config"
        run_host_cmd(ep, sess.user, cmd, keypath=sess.keypath)
        cmd = "echo -e '[escp]\ndtn_path = /usr/local/bin/dtn\ndtn_args = -t 12 -b 8M --cpumask FFF --memnode 1' | sudo tee /etc/escp.conf"
        run_host_cmd(ep, sess.user, cmd, keypath=sess.keypath)
        
        parts = ep.split(":")
        cmd = f"scp -o StrictHostKeyChecking=no -q -i {sess.keypath} -P {parts[1]} {sess.keypath} {sess.user}@{parts[0]}:~/.ssh/id_rsa"
        ret = os.system(cmd)
        cmd = f"scp -o StrictHostKeyChecking=no -q -i {sess.keypath} -P {parts[1]} scripts/* {sess.user}@{parts[0]}:/data/scripts/"
        ret = os.system(cmd)

# simple sequential jobs for ESCP eval
def run_job(sess, source, **kwargs):
    sess.tstop = False
    out = widgets.Output()
    display(out)
    snode = None
    dnode = None
    for idx,ep in sess.endpoints().json().items():
        # run eval script on src host
        if idx == source:
            snode = ep
        elif idx != source:
            dnode = ep
    out.append_stdout(f"Running workflow using src={snode}, dst={dnode}\n")
    out.append_stdout(f"ESCP params: {kwargs}\n")
    
    cmd = f'/data/scripts/escp_eval.sh {kwargs.get("src")} {snode.split(":")[-1]} {kwargs.get("dst")} {dnode.split(":")[-1]} {kwargs.get("iters")} {kwargs.get("tag")}'
    out.append_stdout(f"Executing {cmd}\n")
    run_host_cmd(snode, sess.user, cmd, interactive=True, out=out, keypath=sess.keypath)
    return

def stop_job(sess, hndl):
    sess.tstop = True
    for th in hndl:
        th.join()
    log.info("Stopped job")