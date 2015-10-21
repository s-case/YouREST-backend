
m fcoAPI.api import getToken
from fcoAPI.api import get_server_state
from fcoAPI.api import change_server_status
from fcoAPI.api import list_resource_by_uuid
from createServer import is_ssh_port_open

import logging
#REST logging # you can change INFO to DEBUG for (a lot) more information)
logging.getLogger("requests").setLevel(logging.WARNING)

import argparse

ENDPOINT = "https://cp.sd1.flexiant.net:4442/"

def api_session(customerUsername, customerUUID, customerPassword):
    """Function to set up api session, import credentials etc."""
    token = getToken(ENDPOINT, customerUsername, customerUUID, customerPassword)
    auth_client = dict(endpoint=ENDPOINT, token=token)
    return auth_client

# This method starts the required server, and makes sure that it is in a accessible state before returning.
def start_server(auth_parms, server_uuid):
    """Function to start server, uuid in server_data"""
    server_state = get_server_state(auth_parms, server_uuid)
    if server_state == 'STOPPED':
        rc = change_server_status(auth_parms=auth_parms, server_uuid=server_uuid, state='RUNNING')
        if (rc != 0):
            raise Exception("Failed to put server " + server_uuid + " in to running state")

    server_resultset = list_resource_by_uuid(auth_parms, uuid=server_uuid, res_type='SERVER')
    server_ip = server_resultset['list'][0]['nics'][0]['ipAddresses'][0]['ipAddress']
    is_ssh_port_open(server_ip, 30)

def StartVM(customerUUID, customerUsername, customerPassword, serverUUID, isVerbose=False):

    auth_client = api_session(customerUsername, customerUUID, customerPassword)
    server_state = get_server_state(auth_client, serverUUID)
    if (server_state == 'RUNNING'):
        print "Server is already running"
        return
    if (server_state == 'STOPPED' or server_state == 'STOPPING'):
        start_server(auth_client, serverUUID)
        print "Server is now RUNNING "
    else:
        print "Server could not be started because it is - %s " %server_state
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('customerUUID', nargs='*', help="The UUID of the Customer")
    parser.add_argument('customerUsername',  nargs=1, help="The Username of the Customer")
    parser.add_argument('customerPassword',  nargs=1, help="The password for the Customer")
    parser.add_argument('serverUUID', nargs=1, help="The UUID of the Server to be started")
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

    ret = StartVM(cmdargs.customerUUID[0],
                cmdargs.customerUsername[0],
                cmdargs.customerPassword[0],
                cmdargs.serverUUID[0],
                isVerbose)
