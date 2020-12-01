#!/usr/bin/env python3

'''
Usage:
dtncli [<url> <user> <password>]
'''

from docopt import docopt
import re
import sys
import cmd
import json
import shlex
import pprint
import socket
import requests
from dtnaas_client import Client, Session, Service

from .util import Util, col
from .ssh import get_pubkeys, handle_ssh
from .transfer import transfer, MuxTransfer
from .service import handle_service

SHOW_ITEMS = ["keys", "transfers"]
SYNC_ITEMS = ["active", "nodes"]

class ConfigurationError(Exception):
    def __init__(self, num, key, dir_list):
        self.num = num
        self.key = key
        self.dir = "/" + "/".join(dir_list)

    def __str__(self):
        return "No such path through config at pos: %d %s in %s" %\
            (self.num, self.key, self.dir)

class DTNCmd(cmd.Cmd):
    def __init__(self, url, user, passwd):
        self.prompt = col.PROMPT + "dtncli> " + col.ENDC
        self.config = {"active": dict(),
                       "nodes": dict()}
        self.cwc = self.config
        self.cwd_list = []
        self.curr = None
        self.dtn = Client(url, auth=(user, passwd))
        self.util = Util()
        self.node = None
        self.table = None
        self.pp = pprint.PrettyPrinter(indent=1, width=80, depth=None, stream=None)
        self.tcount = 1
        self.xfers = dict()
        cmd.Cmd.__init__(self)

    def _cleanup(self):
        for k,v in self.xfers.items():
            v.stop()

    def _profiles(self, args):
        try:
            ret = self.dtn.profiles().json()
            print ("profiles OK")
            self.config["profiles"] = ret
        except Exception as e:
            print (f"Error: {e}")

    def _active(self, args):
        try:
            if len(args):
                self.pp.pprint(self.dtn.active(args[0]).json())
            else:
                ret = self.dtn.active().json()
                print ("active OK")
                self.config["active"] = ret
        except Exception as e:
            print (f"Error: {e}")

    def _nodes(self, args):
        try:
            refresh = True if "refresh" in args else False
            nodes = self.dtn.nodes(refresh=refresh).json()
            self.config["nodes"] = nodes
            self._set_cwc()
            print ("nodes OK")
        except Exception as e:
            print (f"Error: {e}")
            #import traceback
            #traceback.print_exc()

    def do_sync(self, args):
        if args.startswith("nodes"):
            self._nodes(args)
        elif args.startswith("active"):
            self._active(args)
        elif args.startswith("profiles"):
            self._profiles(args)
        else:
            self._nodes(args)
            self._active(args)
            self._profiles(args)
            self.do_cd("")

    def complete_sync(self, text, l, b, e):
        return [ x[b-5:] for x in SYNC_ITEMS if x.startswith(l[5:])]
    
    def emptyline(self):
        pass

    def do_session(self, args):
        ret = handle_service(self.dtn, args, self.config)
        try:
            if ret and self.cwd_list[-1] == "active":
                self._set_cwc()
        except:
            pass
    
    def do_ssh(self, args):
        handle_ssh(args, self.cwc)

    def do_show(self, args):
        if not len(args):
            return
        parts = args.split(" ")
        if parts[0] == "keys":
            print (get_pubkeys())
        if parts[0] == "transfers":
            if len(parts) < 2:
                for k,v in self.xfers.items():
                    print (col.ITEM + f"{k}:\t({v})" + col.ENDC)
            elif len(parts) >= 2:
                if parts[1] == "log":
                    if len(parts) >= 3:
                        try:
                            dst = False if len(parts) == 4 and parts[3] == "src" else True
                            print (self.xfers[int(parts[2])].getlog(dst))
                        except:
                            import traceback
                            traceback.print_exc()
                            print (f"Transfer not found: {parts[2]}")
                            return
                    else:
                        print ("No transfer specified")
                else:
                    try:
                        print (parts[1], self.xfers[parts[1]])
                    except:
                        print (f"Transfer not found: {parts[1]}")

    def complete_show(self, text, l, b, e):
        return [ x[b-5:] for x in SHOW_ITEMS if x.startswith(l[5:])]
    
    def do_transfer(self, args):
        t = transfer(self.config, self.dtn, args)
        if not t:
            return
        self.xfers[self.tcount] = t
        self.tcount += 1

    def do_net(self, args):
        print (args)

    def do_rm(self, key):
        if key.startswith("transfer"):
            parts = key.split(" ")
            if len(parts) < 2:
                print (col.FAIL + "Specify active transfer by number" + col.ENDC)
                return
            try:
                xnum = int(parts[1])
            except:
                print (col.FAIL + "Specify active transfer by number" + col.ENDC)
                return
            if xnum in self.xfers:
                print (col.WARNING + f"Removing transfer {xnum}" + col.ENDC)
                self.xfers[xnum].stop()
                del self.xfers[xnum]
            else:
                print (col.FAIL + f"Transfer not found: {xnum}" + col.ENDC)
            return

        if not key:
            print (col.FAIL + "Specify active session by number" + col.ENDC)
            return
        if not len(self.cwd_list) or self.cwd_list[-1] != "active":
            print (col.FAIL + "No active sessions in current path, check /active" + col.ENDC)
            return
        if key not in self.cwc:
            print (col.FAIL + f"{key} is not an active session" + col.ENDC)
        else:
            yn = self.util.query_yes_no(f"Really remove session {key}")
            if yn:
                print (col.WARNING + f"Removing session {key}" + col.ENDC)
                self.dtn.delete(key)
                res = next((a for a in self.config['active'] if next(iter(a)) == key), None)
                if res:
                    self.config['active'].remove(res)
                self._set_cwc()
        
    def do_cd(self, path):
        '''Change the current level of view of the config to be at <key>
        cd <key>'''
        if path=="" or path[0]=="/":
            new_wd_list = path[1:].split("/")
        else:
            new_wd_list = self.cwd_list + path.split("/")
        try:
            cwc, new_wd_list = self._conf_for_list(new_wd_list)
        except ConfigurationError as e:
            print (col.FAIL + str(e) + col.ENDC)
            return
        self.cwd_list = new_wd_list
        self.cwc = cwc

    def complete_cd(self, text, l, b, e):
        return [ x[b-3:] for x,y in self.cwc.items() if x.startswith(l[3:])]

    def do_ls(self, key):
        '''Show the top level of the current working config, or top level of config under [key]
        ls [key]'''
        conf = self.cwc
        if key:
            try:
                conf = conf[key]
            except KeyError:
                print ("No such key %s" % key)
                return
            self.pp.pprint(conf)
            return

        try:
            for k,v in conf.items():
                scol = col.ITEM
                if isinstance(v, dict) or isinstance(v, list):
                    if "name" in v:
                        disp = f"{k}:\t({v['name']})"
                    elif "request" in v:
                        r = v['request'][0]
                        inst = ','.join(map(str, r['instances']))
                        err = False
                        for s,sv in v['services'].items():
                            for svc in sv:
                                if svc['errors']:
                                    err = True
                        if err:
                            scol = col.FAIL
                            state = f"{v['state']} (ERR)"
                        else:
                            state = f"{v['state']}"
                        disp = f"{k}: {state: <20}| {inst: <25} | {r['image']: <30} | {r['profile']}"
                    else:
                        disp = f"{k}"
                    print (scol + disp + col.ENDC)
                elif not v:
                    print (f"{k}")
                else:
                    print (f"{k}: {v}")
        except:
            #import traceback
            #traceback.print_exc()
            print ("%s" % conf)

    def complete_ls(self, text, l, b, e):
        return [ x[b-3:] for x,y in self.cwc.items() if x.startswith(l[3:]) ]

    def do_lsd(self, key):
        '''Show all config from current level down... or all config under [key]
        lsd [key]'''
        
        conf = self.cwc
        if conf and hasattr(conf, "json"):
            conf = conf.json()
        if key:
            try:
                conf = next((sub for sub in conf if sub['name'] == key), None) 
            except KeyError:
                print ("No such key %s" % key)
        self.pp.pprint(conf)

    def complete_lsd(self, text, l, b, e):
        return [ x for x,y in self.cwc.iteritems()
                 if isinstance(y, dict) and x.startswith(text) ]

    def do_pwd(self, key):
        '''Show current path in config separated by slashes
        pwd'''
        print ("/" + "/".join(self.cwd_list))

    def do_exit(self, line):
        '''Exit'''
        self._cleanup()
        return True
    
    def do_EOF(self, line):
        '''Exit'''
        r = input("\nReally quit? (y/N) ")
        if r.lower() == "y":
            self._cleanup()
            return True
        else:
            return False

    def _set_cwc(self):
        '''Set the current working configuration to what it should be
        based on the cwd_list. If the path doesn't exist, set cwc to
        the top level and clear the cwd_list.
        '''
        try:
            self.cwc, self.cwd_list = self._conf_for_list()
            #self.pp.pprint(self.cwc)
        except ConfigurationError:
            self.cwc = self.config
            self.cwd_list = []

    def _conf_for_list(self, cwd_list=None):
        '''Takes in a list representing a path through the config
        returns a tuple containing the current working config, and the
        "collapsed" final path (meaning it has no .. entries.
        '''
        if not cwd_list:
            cwd_list = self.cwd_list
        cwc_stack = []
        cwc = self._ep_to_dict(self.config, None)
        num = 0
        for kdir in cwd_list:
            if kdir == "":
                continue
            num += 1
            if kdir == ".." and cwc_stack:
                cwc = cwc_stack.pop()[0]
                continue
            elif kdir == "..":
                continue
            try:
                ocwc = cwc
                cwc = self._ep_to_dict(cwc[kdir], kdir)
                cwc_stack.append((ocwc, kdir))
            except KeyError:
                #import traceback
                #traceback.print_exc()
                raise ConfigurationError(num, kdir, cwd_list)
        return (cwc, [ x[1] for x in cwc_stack ])

    def _ep_to_dict(self, cfg, k):
        if k and hasattr(cfg, "json"):
            if isinstance(cfg, Service):
                self.active = cfg
            cfg = cfg.json()
        
        if isinstance(cfg, list):
            new = {}
            for d in cfg:
                if "id" in d:
                    new[str(d['id'])] = d
                elif type(d) is dict:
                    for k, v in d.items():
                        new[str(k)] = v
                else:
                    new[d] = None
            cfg = new
        return cfg

def main(args=None):
    args = docopt(__doc__, version='dtncli 0.1')
    url = args.get("<url>")
    if not url:
        url = "http://localhost:5050"

    user = args.get("<user>")
    if not user:
        user = "admin"

    pw = args.get("<password>")
    if not pw:
        pw = "admin"

    info =\
"""Server\t: %s
User\t: %s
Passwd\t: %s\n""" % (url, user, "*****" if pw != "admin" else pw)
    print (info)
    
    dtn = DTNCmd(url, user, pw)
    while True:
        try:
            dtn.cmdloop()
            break
        except KeyboardInterrupt:
            print("Press control-c again to quit")
            try:
                input()
            except KeyboardInterrupt:
                break
            except:
                pass

if __name__ == '__main__':
    main()
