#!/usr/bin/env python3

'''
Usage:
janus [<url> <user> <password>]
'''

from docopt import docopt
import re
import sys
import cmd
import json
import shlex
import pprint
import socket
from janus_client import Client, Session, Service

from .util import Util, col, CText
from .ssh import get_pubkeys, handle_ssh
from .transfer import transfer, MuxTransfer
from .service import handle_service


SHOW_ITEMS = ["keys", "transfers"]
SYNC_ITEMS = ["active", "nodes"]

cout = CText()

class ConfigurationError(Exception):
    def __init__(self, num, key, dir_list):
        self.num = num
        self.key = key
        self.dir = "/" + "/".join(dir_list)

    def __str__(self):
        return "No such path through config at pos: %d %s in %s" %\
            (self.num, self.key, self.dir)

class JanusCmd(cmd.Cmd):
    def __init__(self, url, user, passwd):
        self.prompt = "janus> "
        self.config = {"active": list(),
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
            refresh = True if "refresh" in args else False
            ret = self.dtn.profiles(refresh=refresh)
            if ret.error():
                cout.error(str(ret))
                return
            else:
                self.config["profiles"] = ret.json()
                self._set_cwc()
                cout.info("profiles OK")
        except Exception as e:
            cout.error(f"Error: {e}")

    def _active(self, args):
        try:
            if len(args):
                self.dtn.active(args[0]).json()
            else:
                ret = self.dtn.active().json()
                # convert active sessions list into dict
                new = list()
                for a in ret:
                    if "id" in a:
                        new.append({str(a['id']): a})
                self.config["active"] = new
            cout.info("active OK")
        except Exception as e:
            cout.error(f"Error: {e}")

    def _nodes(self, args):
        try:
            refresh = True if "refresh" in args else False
            ret = self.dtn.nodes(refresh=refresh)
            if ret.error():
                cout.error(str(ret))
                return
            else:
                self.config["nodes"] = ret.json()
                self._set_cwc()
                cout.info("nodes OK")
        except Exception as e:
            cout.error(f"Error: {e}")
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
            cout.info(get_pubkeys())
        if parts[0] == "transfers":
            if len(parts) < 2:
                for k,v in self.xfers.items():
                    cout.item(f"{k}:\t({v})")
            elif len(parts) >= 2:
                if parts[1] == "log":
                    if len(parts) >= 3:
                        try:
                            dst = False if len(parts) == 4 and parts[3] == "src" else True
                            cout.info(self.xfers[int(parts[2])].getlog(dst))
                        except:
                            import traceback
                            traceback.print_exc()
                            cout.info(f"Transfer not found: {parts[2]}")
                            return
                    else:
                        cout.info("No transfer specified")
                else:
                    try:
                        cout.info(parts[1], self.xfers[parts[1]])
                    except:
                        cout.info(f"Transfer not found: {parts[1]}")

    def complete_show(self, text, l, b, e):
        return [ x[b-5:] for x in SHOW_ITEMS if x.startswith(l[5:])]

    def do_transfer(self, args):
        t = transfer(self.config, self.dtn, args)
        if not t:
            return
        self.xfers[self.tcount] = t
        self.tcount += 1

    def do_net(self, args):
        cout.info(args)

    def do_rm(self, key):
        if key.startswith("transfer"):
            parts = key.split(" ")
            if len(parts) < 2:
                cout.error("Specify active transfer by number")
                return
            try:
                xnum = int(parts[1])
            except:
                cout.error("Specify active transfer by number")
                return
            if xnum in self.xfers:
                cout.warn(f"Removing transfer {xnum}")
                self.xfers[xnum].stop()
                del self.xfers[xnum]
            else:
                cout.error(f"Transfer not found: {xnum}")
            return

        if not key:
            cout.error("Specify active session by number")
            return
        if not len(self.cwd_list) or self.cwd_list[-1] != "active":
            cout.error("No active sessions in current path, check /active")
            return
        if key not in self.cwc:
            cout.error(f"{key} is not an active session")
        else:
            yn = self.util.query_yes_no(f"Really remove session {key}")
            if yn:
                cout.warn(f"Removing session {key}")
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
            cout.error(str(e))
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
                cout.error("No such key %s" % key)
                return
            self.pp.pprint(conf)
            return

        try:
            # leaf item case
            if not isinstance(conf, dict):
                print (f"{conf}")
                return
            # print a nice header for the active session list
            if len(self.cwd_list) and self.cwd_list[-1] == "active":
                cout.header(f"{'ID': <3}: {'Status': <20}| {'Nodes/Services': <45} | {'Image': <40} | Profile")
            for k,v in conf.items():
                scol = col.ITEM
                if isinstance(v, dict) or isinstance(v, list):
                    if "request" in v:
                        servcs = list()
                        cports = list()
                        profiles = set()
                        images = set()
                        err = False
                        for s,sv in v['services'].items():
                            for svc in sv:
                                if svc['errors']:
                                    err = True
                                cports.append(svc.get('ctrl_port', 'N/A'))
                                servcs.append(s)
                                profiles.add(svc.get('profile', 'N/A'))
                                images.add(svc.get('image', 'N/A'))
                        if err:
                            scol = col.FAIL
                            state = f"{v['state']} (ERR)"
                        else:
                            state = f"{v['state']}"
                        profs = ','.join(profiles)
                        imgs = ','.join(images)
                        inst = ','.join(list(map(lambda x,y: f"{x} [{y}]", servcs, cports)))
                        disp = f"{k: <3}: {state: <20}| {inst: <45} | {imgs: <40} | {profs}"
                    else:
                        scol = col.DIR if len(v) else col.EDIR
                        disp = f"{k}"
                    cout._color(scol, disp)
                else:
                    print (f"{k}: {v}")
        except:
            import traceback
            traceback.print_exc()
            cout.info("%s" % conf)

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
                cout.info("No such key %s" % key)
        self.pp.pprint(conf)

    def complete_lsd(self, text, l, b, e):
        return [ x for x,y in self.cwc.iteritems()
                 if isinstance(y, dict) and x.startswith(text) ]

    def do_pwd(self, key):
        '''Show current path in config separated by slashes
        pwd'''
        cout.info("/" + "/".join(self.cwd_list))

    def do_exit(self, line):
        '''Exit'''
        self._cleanup()
        return True

    def do_EOF(self, line):
        '''Exit'''
        try:
            r = input("\nReally quit? (y/N) ")
            if r.lower() == "y":
                self._cleanup()
                return True
        except:
            print ("\n")
            pass
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
                if "name" in d:
                    new[d['name']] = d
                elif type(d) is dict:
                    for k, v in d.items():
                        new[str(k)] = v
                else:
                    new[d] = None
            cfg = new
        return cfg

def main(args=None):
    args = docopt(__doc__, version='janus cli 0.1')
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
    cout.info(info)

    jan = JanusCmd(url, user, pw)
    while True:
        try:
            # perform initial sync to controller at start
            jan.do_sync("")
            jan.cmdloop()
            break
        except KeyboardInterrupt:
            cout.warn("Press control-c again to quit")
            try:
                input()
            except KeyboardInterrupt:
                break
            except:
                pass

if __name__ == '__main__':
    main()
