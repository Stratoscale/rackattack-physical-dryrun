import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
import argparse
import threading
from rackattack.common import tftpboot
from rackattack.common import dnsmasq
from rackattack.common import inaugurate
from rackattack.physical import ipmi
from rackattack.physical import serialoverlan
from rackattack.dryrun.master import network
from rackattack.common import globallock

parser = argparse.ArgumentParser()
parser.add_argument("--hostID", required=True)
parser.add_argument("--macAddress", required=True)
parser.add_argument("--ipmiHost", required=True)
parser.add_argument("--ipmiUsername", required=True)
parser.add_argument("--ipmiPassword", required=True)
parser.add_argument("--osmosisServerIP", required=True)
parser.add_argument("--ipAddress", required=True)
parser.add_argument("--label", required=True)
args = parser.parse_args()


checkInEvent = threading.Event()
doneEvent = threading.Event()


def inaugurateCheckIn():
    logging.info("Inaugurator checked in")
    inaugurateInstance.provideLabel(ipAddress=args.ipAddress, label=args.label)
    checkInEvent.set()


def inaugurateDone():
    logging.info("Inaugurator done")
    doneEvent.set()


tftpbootInstance = tftpboot.TFTPBoot(
    netmask=network.netmask(),
    inauguratorServerIP=network.myIP(),
    osmosisServerIP=args.osmosisServerIP,
    rootPassword="dryrun",
    withLocalObjectStore=True)
dnsmasq.DNSMasq.eraseLeasesFile()
dnsmasq.DNSMasq.killAllPrevious()
dnsmasqInstance = dnsmasq.DNSMasq(
    tftpboot=tftpbootInstance,
    serverIP=network.myIP(),
    netmask=network.netmask(),
    firstIP=args.ipAddress,
    lastIP=args.ipAddress,
    gateway=network.gateway(),
    nameserver=network.myIP())
inaugurateInstance = inaugurate.Inaugurate(bindHostname=network.myIP())
with globallock.lock:
    dnsmasqInstance.add(args.macAddress, args.ipAddress)
    inaugurateInstance.register(
        ipAddress=args.ipAddress,
        checkInCallback=inaugurateCheckIn,
        doneCallback=inaugurateDone)
    tftpbootInstance.configureForInaugurator(args.macAddress, args.ipAddress, clearDisk=True)
sol = serialoverlan.SerialOverLan(args.ipmiHost, args.ipmiUsername, args.ipmiPassword, args.hostID)
ipmiInstance = ipmi.IPMI(args.ipmiHost, args.ipmiUsername, args.ipmiPassword)
ipmiInstance.powerCycle()
try:
    logging.info("Waiting for inaugurator to check in")
    checkInEvent.wait(4 * 60)
    if not checkInEvent.isSet():
        raise Exception("Timeout waiting for inaugurator to checkin")
    logging.info("Inaugurator checked in, waiting for inaugurator to complete")
    doneEvent.wait(7 * 60)
    if not doneEvent.isSet():
        raise Exception("timeout waiting for inaugurator to be done")
except:
    logging.info("Serial log was:\n%(log)s", dict(log=open(sol.serialLogFilename()).read()))
    raise
finally:
    ipmiInstance.off()
