import datetime
import time
import socket
import errno
import argparse
import subprocess

import sys
sys.path.append("../")

from api import add_nic_to_server
from api import attach_disk
from api import attach_ssh_key
from api import change_server_status
from api import create_nic
from api import create_sshkey
from api import create_vdc
from api import getToken
from api import get_first_vdc_in_cluster
from api import get_prod_offer_uuid
from api import get_server_state
from api import list_image
from api import list_resource_by_uuid
from api import list_sshkeys
from api import rest_create_disk
from api import rest_create_server
from api import wait_for_install
from api import wait_for_job
from api import wait_for_resource

IMAGE_UUID = "e682f044-c919-329f-b07a-b9b245406b50"
ENDPOINT = "https://cp.sd1.flexiant.net:4442/" 
NETWORKTYPE = "IP"
DEFAULT_EXTRA_DISK_SIZE = "20"
DEFAULT_RAM_SIZE = 512
DEFAULT_CPU_COUNT = 1
CONTEXTSCRIPT = ""
    
# Method to create a VDC for the customer
def create_vdc_in_cluster(auth, cluster_uuid):
    ts = time.time()
    vdc_name = "VDC " + datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    vdc_ret = create_vdc(auth, cluster_uuid, vdc_name)

    print("=== VDC Creation job ===")
    print vdc_ret
    print("========================")

    return vdc_ret['itemUUID']

# Create a SSH key (on the FCO) using the public key and attach it to the user only if it does not already exists
def AddKey(auth_parms, server_uuid, customerUUID, publicKey):

    print("AddKey Args: server:" + server_uuid + " customer: " + customerUUID + " publicKey:")
    print publicKey
    print("== end AddKey Args ==\n")

    key_ret = list_sshkeys(auth_parms, customerUUID)

    # See how many keys are there extract number of Servers from result set
    create = True
    key_item_uuid = ""
    if (key_ret['totalCount'] == 0):
        create = True
    else:
        # Key's exist; check if the one we are about to add is one of them
        print key_ret
        for x in range(0, key_ret['totalCount']):
            print("---")
            print key_ret['list'][x]
            print("----")
            if (key_ret['list'][x]['publicKey'] == publicKey):
                print "Customer already has key attached to their account"
                key_item_uuid = key_ret['list'][x]['resourceUUID']
                create = False
    if (create):
        print("===== Customer needs SSH key added =====")
        public_key_name = ''
        add_ret = create_sshkey(auth_parms, publicKey, public_key_name)
        print add_ret
        key_item_uuid = add_ret['itemUUID']

    # Attach the key (be it existing or newly created) to the server
    attach_ret = attach_ssh_key(auth_parms, server_uuid=server_uuid, sshkey_uuid=key_item_uuid)
   
    return attach_ret

# Gets the UUID of the product offer and creates a disk on the FCO
def create_disk(auth_parms, prod_offer, disk_size, disk_name, vdc_uuid):
    """ Function to create disk """

    # get product offer uuid for the disk in question
    prod_offer_uuid = get_prod_offer_uuid(auth_parms, prod_offer)

    disk_job = rest_create_disk(auth_parms, vdc_uuid, prod_offer_uuid, disk_name, disk_size)

    disk_uuid = disk_job['itemUUID']
    print("New disk UUID=" + disk_uuid)

    # Check the job completes
    status = wait_for_job(auth_parms, disk_job['resourceUUID'], "SUCCESSFUL", 90)
    if (status != 0):
        raise Exception("Failed to add create disk (uuid=" + disk_uuid + ")")

    return disk_uuid

# Method to create a server on the FCO, server will include the SSH key, NIC and a disk
def build_server(auth_parms, customer_uuid, image_uuid, vdc_uuid, server_po_uuid, boot_disk_po_uuid,
                server_name, ram_amount, cpu_count, networkType, cluster_uuid, public_key, context_script):
   
    create_server_job = rest_create_server(auth_parms, server_name, server_po_uuid, image_uuid,
                                             cluster_uuid, vdc_uuid, cpu_count,
                                             ram_amount, boot_disk_po_uuid, context_script)

    server_uuid = create_server_job['itemUUID']
    print "--- createServer done with UUID " + server_uuid + " -----"
    
    # The public_key arg might be a list of public keys, separated by cr/lf. So split
    # the list and process each key individually
    for single_key in public_key.splitlines():
        print("Processing key: " + single_key)
        add_ret = AddKey(auth_parms, server_uuid, customer_uuid, single_key)
        print("== AddKey Result ==")
        print add_ret
        print("====")

    wait_for_install(auth_parms, server_uuid=server_uuid)

    # Add NIC to server
    print "Calling create_nic for network " + networkType
    nic_uuid = create_nic(auth_parms=auth_parms, nic_count='0', network_type=networkType,
                          cluster_uuid=cluster_uuid, vdc_uuid=vdc_uuid)
    print "create_nic returned nic_uuid: " + nic_uuid
    wait_for_resource(auth_parms=auth_parms, res_uuid=nic_uuid, state='ACTIVE', res_type='nic')
    print "nic uuid: " + nic_uuid

    add_nic_response = add_nic_to_server(auth_parms=auth_parms, server_uuid=server_uuid, nic_uuid=nic_uuid, index='1')

    # Wait on the addNic job completing
    status = wait_for_job(auth_parms, add_nic_response['resourceUUID'], "SUCCESSFUL", 90)
    if (status != 0):
        raise Exception("Failed to add NIC to server")

    # Lookup server properties to get UUID, and password, that have been assigned to it
    server_resultset = list_resource_by_uuid(auth_parms, uuid=server_uuid, res_type='SERVER')
    server = server_resultset['list'][0]
    server_uuid = server['resourceUUID']
    server_pw = server['initialPassword']
    server_user = server['initialUser']
    server_data = [server_uuid, server_pw, server_user]
    return server_data


def is_ssh_port_open(server_ip, max_wait):
    ok = 0
    poll_interval = 5
    limit = max_wait / poll_interval  # number of times to retry (approximately)
    while ok == 0 and limit > 0:
        try:
            s = socket.create_connection((server_ip, 22), poll_interval)
            s.close()
            ok = 1
            print str(time.time()) + " Connected\n"
        except socket.error, msg:
            limit = limit - 1
            print str(time.time()) + " fail: '" + str(msg[0]) + "'"  # + " " + msg[1]
            # ECONNREFUSED is good, because it means the machine is likely on it's way up. Of course,
            # that could be the permanent state of affairs, but we only care if the machine is booted
            # - by the time the real connection happens, ssh should be in a state where it can accept
            # connections.
            if (str(msg[0]) == str(errno.ECONNREFUSED)):
                ok = 1

    print("SSH probe complete with " + str(limit) + " tries left (ok=" + str(ok) + ")")

# This method starts the required server, and makes sure that it is in a accessible state before returning.
def start_server(auth_parms, server_data):
    """Function to start server, uuid in server_data"""
    server_uuid = server_data[0]
    server_state = get_server_state(auth_parms, server_uuid)
    if server_state == 'STOPPED':
        rc = change_server_status(auth_parms=auth_parms, server_uuid=server_uuid, state='RUNNING')
        # change_server_status() waits on the server getting to the requested state, so we don't
        # need to call wait_for_server() here. However, we do (1) need to check the status and (2)
        # wait on the server actually being accessible (as opposed to having a RUNNING state in
        # FCO, which really just means that the underlying kvm process has started).
        #
        # 1. Check rc (0 is good)
        if (rc != 0):
            raise Exception("Failed to put server " + server_uuid + " in to running state")

    server_resultset = list_resource_by_uuid(auth_parms, uuid=server_uuid, res_type='SERVER')
    print("Server result set is:")
    print server_resultset

    server_ip = server_resultset['list'][0]['nics'][0]['ipAddresses'][0]['ipAddress']  # yuk
    print("server IP=" + server_ip)

    # Step 2. Wait on it being accessible. It is possible that the server doesn't have ssh installed,
    # or it is firewalled, so don't fail here if we can't connect, just carry on and let
    # the caller deal with any potential issue. The alternative is a hard-coded sleep, or
    # trying a ping (platform specific and/or root privs needed).
    is_ssh_port_open(server_ip, 30)

    server_data.append(server_ip)
    return server_data

# Method to add the remote to the local repo of the user
def add_remote_git(ip, local_repo_dir):
    url = "ssh://" + ip + "/webservice.git"
    print ("Adding remote git: " + url + " to the local repo: " + local_repo_dir)
    subprocess.check_call(["git", "remote", "add", "origin", url], cwd = local_repo_dir)

# Method that puts together all the methods required to create a VM
def MakeVM(customerUUID, customerUsername, customerPassword, publicKey, vmName, localRepoDir, isVerbose):
 
    ramAmount = DEFAULT_RAM_SIZE
    cpuCount = DEFAULT_CPU_COUNT
    diskSize = DEFAULT_EXTRA_DISK_SIZE
    
    print customerUUID 
    print customerUsername
    print customerPassword
    print publicKey
    print cpuCount
    print ramAmount
    print vmName
    print isVerbose
    # Authenticate to the FCO API, getting a token for furture use
    token = getToken(ENDPOINT, customerUsername, customerUUID, customerPassword)

    auth = dict(endpoint=ENDPOINT, token=token)

    print("Details for image_uuid " + IMAGE_UUID + ":\n");

    img_ret = list_image(auth, IMAGE_UUID)
    vdc_uuid_for_image = img_ret['vdcUUID']
    if (isVerbose):
        print("vdc_uuid_for_image is " + vdc_uuid_for_image)

    cluster_uuid_for_image = img_ret['clusterUUID']
    print("cluster_uuid_for_image is " + cluster_uuid_for_image)

    customer_vdc_uuid = get_first_vdc_in_cluster(auth, cluster_uuid_for_image)
    if (isVerbose):
        print("The VDC to use is: " + customer_vdc_uuid)

    # Setup VDC in this cluster if user doesn't have one
    if (customer_vdc_uuid == ''):
        vdc_uuid = create_vdc_in_cluster(auth, cluster_uuid_for_image)
        if (isVerbose):
            print("VDC we created is " + vdc_uuid)
        customer_vdc_uuid = vdc_uuid

    # Sanity check that we have a VDC to work with
    if (customer_vdc_uuid == ''):
        raise Exception("No VDC to create the server in !")

    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    if vmName == None:
        server_name = "VM " + current_time
    else:
        server_name = vmName

    # Get the Product Offer UUID of the Standard Server product
    product_offer = 'Standard Server'
    server_po_uuid = get_prod_offer_uuid(auth, product_offer)
    if (server_po_uuid == ""):
        raise Exception("No '" + product_offer + "' Product Offer found")

    # Base the boot disk on the PO of the same size storage disk as the Image must have been; that way
    # we can be reasonably sure it will exist.
    image_disk_po_name = str(img_ret['size']) + " GB Storage Disk"
    boot_disk_po_uuid = get_prod_offer_uuid(auth, image_disk_po_name)
    if (boot_disk_po_uuid == ""):
        raise Exception("No suitable disk product offer found  (expected a '" + image_disk_po_name + "' PO)")

    # Create the additional disk (if any). We'll attach it later.
    disk_name = "Disk " + current_time + " #2"
    extra_disk_uuid = create_disk(auth, 'Standard Disk', diskSize, disk_name, customer_vdc_uuid)

    server_data = build_server(auth_parms=auth, customer_uuid=customerUUID,
                               image_uuid=IMAGE_UUID,
                               vdc_uuid=customer_vdc_uuid,
                               server_po_uuid=server_po_uuid, boot_disk_po_uuid=boot_disk_po_uuid,
                               server_name=server_name,
                               ram_amount=ramAmount, cpu_count=cpuCount,
                               networkType=NETWORKTYPE,
                               cluster_uuid=cluster_uuid_for_image,
                               public_key=publicKey,
                               context_script=CONTEXTSCRIPT)

    if (isVerbose):
        print "Return from build_server() is:"
        print server_data
        print "==== End build_server() details ===="

    # If we created an extra disk, attach it now
    if (extra_disk_uuid != ""):
        attach_disk(auth_parms=auth, server_uuid=server_data[0], disk_uuid=extra_disk_uuid, index='2')

    server_data = start_server(auth_parms=auth, server_data=server_data)

    ret = dict(server_uuid=server_data[0],
             ip=server_data[3],
             password=server_data[1],
             login=server_data[2]
            )

    add_remote_git(server_data[3], localRepoDir)
    
    print ret

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('customerUUID', nargs='*', help="The UUID of the Customer")
    parser.add_argument('customerUsername',  nargs=1, help="The Username of the Customer")
    parser.add_argument('customerPassword',  nargs=1, help="The password for the Customer")
    parser.add_argument('publicKey', nargs=1, help="SSH public key")
    parser.add_argument('serverName', nargs=1, help="Server name")
    parser.add_argument('localRepoDir', nargs=1, help="The local repository where the code generated has been committed")
    parser.add_argument('--verbose', dest='isVerbose', action='store_true',
                            help="Whether to print diagnostics as we go")
    
    cmdargs = parser.parse_args()
    
    isVerbose = cmdargs.isVerbose
    if (isVerbose):
        # We can turn on debugging by explicitly importing http_client and setting it's debug level
        try:
            import http.client as http_client
        except ImportError:
            import httplib as http_client
    
        http_client.HTTPConnection.debuglevel = 1
  
    ret = MakeVM(cmdargs.customerUUID[0],
                cmdargs.customerUsername[0],
                cmdargs.customerPassword[0],
                cmdargs.publicKey[0],
                cmdargs.serverName[0],
                cmdargs.localRepoDir[0],
                isVerbose)
    
    
