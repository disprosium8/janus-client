import sys
import glob
import libtmux
import ptyprocess
import threading
import signal
from pathlib import Path
from .util import Util, col


try:
    tmux= libtmux.Server()
    tsess = tmux.find_where({ "session_name": "janus" })
except:
    tsess = None
    print ("SSH\t: Running without tmux support")

SSHCMD="ssh -t -o StrictHostKeyChecking=no -q"
home = str(Path.home())

def get_pubkeys(path=f"{home}/.ssh"):
    ret = ""
    try:
        for fname in glob.glob(f"{path}/*.pub"):
            f = open(fname, 'r')
            ret+=f.read()
    except Exception as e:
        pass
    return ret

def ssh_pty(args, cwc):
    user = None

    def handler(signum, frame):
        ssh.sendintr()

    def output_reader(proc):
        while True:
            try:
                s = proc.read()
                sys.stdout.write(s)
                sys.stdout.flush()
            except EOFError:
                proc.close()
                break

    if not 'ctrl_port' in cwc or not 'ctrl_host' in cwc:
        print (col.FAIL + "No host or port information on this path" + col.ENDC)
        return

    parts = args.split(" ")
    if len(parts) > 1 and parts[0] == "-l":
        user = parts[1]
    sshuser = user if user else cwc['container_user']
    ssh = ptyprocess.PtyProcessUnicode.spawn(["ssh", "-o", "StrictHostKeyChecking=no",
                                              cwc['ctrl_host'],
                                              "-p", cwc['ctrl_port'],
                                              "-l", sshuser], echo=False)
    signal.signal(signal.SIGINT, handler)
    
    t = threading.Thread(target=output_reader, args=(ssh,))
    t.start()
    
    while True:
        try:
            s = sys.stdin.read(1)
            if s == '':
                ssh.sendeof()
            if s == '\f':
                ssh.sendcontrol('l')
                continue
            if ssh.closed:
                break
            ssh.write(s)
        except IOError:
            break
    t.join()

def ssh_tmux(args, cwc):
    user = None

    def tpane(cmd):
        window = tsess.attached_window
        pane = window.split_window(attach=False)
        window.select_layout("even-vertical")
        pane.clear()
        pane.send_keys(cmd)

    if (args):
        parts = args.split(" ")
        sid = parts[0]
        if len(parts) > 2 and parts[1] == "-l":
            user = parts[2]
        try:
            res = cwc[sid]
            for k,v in res['services'].items():
                for s in v:
                    sshuser = user if user else s['container_user']
                    cmd = f"{SSHCMD} {s['ctrl_host']} -p {s['ctrl_port']} -l {sshuser}"
                    tpane(cmd)
        except:
            print (col.FAIL + f"No active Session \"{args}\"" + col.ENDC)
        return
        
    if not 'ctrl_port' in cwc or not 'ctrl_host' in cwc:
        print (col.FAIL + "No host or port information on this path" + col.ENDC)
        return

    sshuser = user if user else cwc['container_user']
    cmd = f"{SSHCMD} {cwc['ctrl_host']} -p {cwc['ctrl_port']} -l {sshuser}"
    tpane(cmd)

def handle_ssh(args, cwc):
    if tsess:
        ssh_tmux(args, cwc)
    else:
        ssh_pty(args, cwc)

def ssh_cmd_tmux_window(host, port, user, cmd):
    #print (host, port, user, cmd)
    win = tsess.new_window(attach=False)
    pane = win.attached_pane
    cmd = f"{SSHCMD} {host} -p {port} -l {user} {cmd}"
    pane.send_keys(cmd)
    return pane

def cmd_tmux_window(cmd):
    #print (host, port, user, cmd)
    win = tsess.new_window(attach=False)
    pane = win.attached_pane
    pane.send_keys(cmd)
    return pane
