import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
import yaml
import argparse
from rackattack import clientfactory
from rackattack import api
from rackattack.ssh import connection
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--rackYaml", required=True)
parser.add_argument("--targetNode", required=True)
parser.add_argument("--rackattackUser", required=True)
parser.add_argument("--ipAddress", required=True)
parser.add_argument("--osmosisServerIP", required=True)
args = parser.parse_args()

with open(args.rackYaml) as f:
    rackYaml = yaml.load(f)
targetNode = [n for n in rackYaml['HOSTS'] if n['id'] == args.targetNode][0]
client = clientfactory.factory()
logging.info("Allocating master node")
allocationInfo = api.AllocationInfo(user=args.rackattackUser, purpose="dryrun")
label = subprocess.check_output(["solvent", "printlabel", "--thisProject", "--product=rootfs"]).strip()
requirements = dict(master=api.Requirement(imageLabel=label, imageHint="rootfs-basic"))
allocation = client.allocate(requirements, allocationInfo)
allocation.wait(timeout=5 * 60)
logging.info("Allocation successful, waiting for ssh")
masterNode = allocation.nodes()['master']
ssh = connection.Connection(**masterNode.rootSSHCredentials())
ssh.waitForTCPServer()
ssh.connect()
logging.info("Connected to ssh")
ssh.ftp.putFile("/tmp/master.egg", "build/master.egg")
print ssh.run.script(
    "PYTHONPATH=/tmp/master.egg python -m rackattack.dryrun.master.main "
    "--hostID=%(targetNodeID)s --macAddress=%(macAddress)s "
    "--ipmiHost=%(ipmiHost)s --ipmiUsername=%(ipmiUsername)s "
    "--ipmiPassword=%(ipmiPassword)s --osmosisServerIP=%(osmosisServerIP)s "
    "--ipAddress=%(ipAddress)s --label=%(label)s" % dict(
        targetNodeID=targetNode['id'],
        macAddress=targetNode['primaryMAC'],
        ipmiHost=targetNode['ipmiLogin']['hostname'],
        ipmiUsername=targetNode['ipmiLogin']['username'],
        ipmiPassword=targetNode['ipmiLogin']['password'],
        osmosisServerIP=args.osmosisServerIP,
        ipAddress=args.ipAddress,
        label=label))
