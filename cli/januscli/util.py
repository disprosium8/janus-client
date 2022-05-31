import sys


class col:
    HEADER = '\033[35m'# PINK
    DIR = '\033[34m' # BLUE
    EDIR = '\033[36m' # CYAN
    ITEM = '\033[39m' # DEFAULT BLK
    PROMPT = '\033[32m' # GREEN
    WARNING = '\033[33m' # YELLOW
    FAIL = '\033[31m' # RED
    ENDC = '\033[39m' # DEFAULT BLK

class CText():
    def _color(self, c, e):
        print (c + str(e) + col.ENDC)
    def warn(self, e):
        self._color(col.WARNING, e)
    def error(self, e):
        self._color(col.FAIL, e)
    def item(self, e):
        self._color(col.ITEM, e)
    def header(self, e):
        self._color(col.HEADER, e)
    def info(self, e):
        print (str(e))

class Util():
    def val_from_input(self, inp):
        '''Take user input, and try to convert it to JSON appropriate
        python values.
        '''
        val = inp
        try:
            val = int(inp)
            return val
        except Exception:
            val = inp
        if val == "false":
            return False
        if val == "true":
            return True
        if (val[0] == "'" and val[-1] == "'") or\
                (val[0] == '"' and val[-1] == '"'):
            return val[1:-1]
        return val

    def get_string(self, disp_str, dval):
        val = raw_input(disp_str)
        if len(str(val)):
            return str(val)
        else:
            return dval

    def get_int(self, disp_str, dval):
        val = raw_input(disp_str)
        try:
            rval = int(val)
            return rval
        except:
            return dval

    def get_real(self, disp_str, dval):
        val = raw_input(disp_str)
        try:
            rval = float(val)
            return rval
        except:
            return dval

    def query_yes_no(self, question, default="no"):
        """Ask a yes/no question via raw_input() and return their answer.
        "question" is a string that is presented to the user.
        "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

        The "answer" return value is one of "yes" or "no".
        """
        valid = {"yes":True,   "y":True,  "ye":True,
                 "no":False,     "n":False}
        if default == None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("invalid default answer: '%s'" % default)

        while True:
            choice = input(question + prompt)
            #sys.stdout.write(question + prompt)
            #choice = raw_input().lower()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' "\
                                 "(or 'y' or 'n').\n")
