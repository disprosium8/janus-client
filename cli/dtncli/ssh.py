import glob
from pathlib import Path

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
