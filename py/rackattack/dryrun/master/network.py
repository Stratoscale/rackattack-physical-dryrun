import re
import socket
import subprocess


def myIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 1000))
        return s.getsockname()[0]
    finally:
        s.close()


def netmask():
    output = subprocess.check_output(['ifconfig'])
    return re.search(r"inet\s+%s\s+netmask\s+(\S+)\s" % myIP(), output).group(1)


def gateway():
    output = subprocess.check_output(['ip', 'route', 'show'])
    return re.search(r"default\s+via\s+(\S+)\s", output).group(1)
