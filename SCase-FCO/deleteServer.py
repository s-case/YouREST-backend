from fcoAPI.api import getToken
from fcoAPI.api import change_server_status
from fcoAPI.api import rest_delete_resource
from fcoAPI.api import list_resource_by_uuid
from stopServer import StopVM

import argparse
import time
import logging
# you can change INFO to DEBUG for (a lot) more information)
logging.getLogger("requests").setLevel(logging.WARNING)

ENDPOINT = "https://cp.sd1.flexiant.net:4442/"
WAIT_TIME = 30 #seconds

# Get the API session
def api_session(customerUsername, customerUUID, customerPassword):
    """Function to set up api session, import credentials etc."""
    token = getToken(ENDPOINT, customerUsername, customerUUID, customerPassword)
    auth_client = dict(endpoint=ENDPOINT, token=token)
    return auth_client

def wait_for_vm_deletion(auth_client, serverUUID, state):
    result = change_server_status(auth_client, serverUUID, state)
    if (result != 0):
        print "Could not delete the VM"
    else:
        print "The VM is deleting ..."
        count = 0
        # Maximum amount of time we would wait - 2 minutes. Check every 30 seconds
        if (count < 4):
            # 30 seconds should be enough for the VM to be destroyed
            time.sleep(WAIT_TIME)
            server = list_resource_by_uuid(auth_client, serverUUID, "SERVER")
            if(server['totalCount'] == 0):
                print "======================================================"
                print "The VM has been deleted"
                return
            count = count + 1

# This method puts together the stop and destroy APIs of the VM
def DestroyVM(customerUUID, customerUsername, customerPassword, serverUUID, isVerbose=False):
    # Actually just defines the global variables now (since all config bits are passed on the command line)
    print "Start of DestroyVM"
    auth_client = api_session(customerUsername, customerUUID, customerPassword)

    server_state = StopVM(customerUUID, customerUsername, customerPassword, serverUUID, isVerbose=False)
    if (server_state != 'NOT_FOUND'):
        rest_delete_resource(auth_client, serverUUID, "SERVER")
        wait_for_vm_deletion(auth_client, serverUUID, "DELETING")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('customerUUID', nargs='*', help="The UUID of the Customer")
    parser.add_argument('customerUsername',  nargs=1, help="The Username of the Customer")
    parser.add_argument('customerPassword',  nargs=1, help="The password for the Customer")
    parser.add_argument('serverUUID', nargs=1, help="The UUID of the Server to be deleted")
    parser.add_argument('--verbose', dest='isVerbose', action='store_true',
                            help="Whether to print diagnostics as we go")

    cmdargs = parser.parse_args()

    print cmdargs

    isVerbose = cmdargs.isVerbose
    if (isVerbose):
        # We can turn on debugging by explicitly importing http_client and setting it's debug level
        try:
            import http.client as http_client
        except ImportError:
            import httplib as http_client

        http_client.HTTPConnection.debuglevel = 1

    ret = DestroyVM(cmdargs.customerUUID[0],
                cmdargs.customerUsername[0],
                cmdargs.customerPassword[0],
                cmdargs.serverUUID[0],
                isVerbose)

