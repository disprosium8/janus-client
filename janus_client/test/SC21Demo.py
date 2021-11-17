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
log = logging.getLogger("SC21Demo")

def run_host_cmd(host, cmd, ofname=None, stop=None, interactive=False, out=None):
    log.debug(f"Running \"{cmd}\" on \"{host}\", with output to file \"{ofname}\"")
    parts = host.split(":")
    if len(parts) > 1:
        initcmd = ["ssh", "-t", "-o", "StrictHostKeyChecking=no", "-p", parts[1], parts[0]]
    else:
        initcmd = ["ssh", "-t", "-o", "StrictHostKeyChecking=no", host]
    rcmd = initcmd + cmd.split(" ")
    log.debug(rcmd)
    try:
        proc = subprocess.Popen(rcmd, stdout=PIPE)
        if interactive:
            for p in proc.stdout:
                if out:
                    out.append_stdout(p.decode('utf-8'))
                else:
                    print (p.decode('utf-8'), end='')
                if stop and stop():
                    proc.kill()
                    return
    except Exception as e:
        log.info(f"Error running {rcmd}: {e}")
        return
    outs = None
    errs = None
    if stop:
        while not stop():
            time.sleep(1)
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except TimeoutExpired:
            proc.kill()
    else:
        outs, errs = proc.communicate()
        proc.terminate()

    if not ofname:
        return
    try:
        f = open(ofname, 'wb')
        if not outs:
            outs = proc.stdout.read()
        f.write(outs)
        f.close()
    except Exception as e:
        log.error(f"Could not write output for \"{ofname}\": {e}")
        return

def setup(sess):
    res = sess.status().json()[0]
    for idx,ep in sess.endpoints().json().items():
        
        # Setup ssh for some tools
        log.info(f"Setting up environment on {idx}")
        """
        cmd = f"sudo mkdir /.ssh; sudo chown {user} /.ssh; echo -e 'Host *\n\tStrictHostKeyChecking no' > /.ssh/config"
        run_host_cmd(ep, cmd)
        parts = ep.split(":")
        cmd = f"scp -o StrictHostKeyChecking=no -q -P {parts[1]} ~/.ssh/id_rsa_jupyter {user}@{parts[0]}:/.ssh/id_rsa"
        ret = os.system(cmd)
        """

        for k,v in res.items():
            if idx in v['services']:
                svc = v['services'][idx][0]
                sess.image = svc['image']
                
                if idx == "nersc-tbn-1":
                    sess.dst = ep
                    sess.dst_ip = "10.33.1.11"
                    sess.dst_gw = "10.33.1.1"
                elif idx == "nersc-tbn-2":
                    sess.src = ep
                    sess.src_ip = "10.33.2.12"
                    sess.src_gw = "10.33.2.1"
                
                try:
                    v4net = IPv4Network(svc['data_ipv4']+'/24', strict=False)
                    cmd = None
                    if str(v4net[1]) == "10.33.1.1":
                        cmd = "sudo route add -net 10.33.2.0/24 gw 10.33.1.1"
                        sess.dst = ep
                        sess.dst_ip = svc['data_ipv4']
                        sess.dst_gw = "10.33.1.1"
                    elif str(v4net[1]) == "10.33.2.1":
                        cmd = "sudo route add -net 10.33.1.0/24 gw 10.33.2.1"
                        sess.src = ep
                        sess.src_ip = svc['data_ipv4']
                        sess.src_gw = "10.33.2.1"
                    if cmd:
                        run_host_cmd(ep, cmd)
                except:
                    continue
                    
def run_job(sess):
    sess.stop = False
    out = widgets.Output()
    display(out)
    out.append_stdout(f"Running workflow on {sess.src} and {sess.dst}")
    if sess.image.startswith("dtnaas/ofed"):
        dst_cmd = f"ping -c 2 {sess.src_gw}; xfer_test -s -r -d 128"
        dst_thr = threading.Thread(target=run_host_cmd, args=(sess.dst, dst_cmd, None, lambda: sess.stop))
        src_cmd = f"ping -c 2 {sess.dst_gw}; stdbuf -oL xfer_test -c {sess.dst_ip} -t 12000 -i 5 -r -a 1 -o 24 -d 112"
        src_thr = threading.Thread(target=run_host_cmd, args=(sess.src, src_cmd, None, lambda: sess.stop, True, out))
    elif sess.image.startswith("dtnaas/tools"):
        dst_cmd = f"ping -c 2 {sess.src_gw}; iperf -s -i 20"
        dst_thr = threading.Thread(target=run_host_cmd, args=(sess.dst, dst_cmd, None, lambda: sess.stop, True, out))
        src_cmd = f"ping -c 2 {sess.src_gw}; iperf -c {sess.dst_ip} -t 12000 -w 512M -P 8"
        src_thr = threading.Thread(target=run_host_cmd, args=(sess.src, src_cmd, None, lambda: sess.stop))
    dst_thr.start()
    time.sleep(1)
    src_thr.start()
    return [dst_thr, src_thr]

def stop_job(sess, hndl):
    sess.stop = True
    for th in hndl:
        th.join()
    log.info("Stopped job")