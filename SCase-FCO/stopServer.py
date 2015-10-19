from fcoAPI.api import getToken
from fcoAPI.api import get_server_state
from fcoAPI.api import wait_for_server
from fcoAPI.api import change_server_status

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

# Method to stop the VM, the stop signal is sent to the VM and until the VM is stopped, this method does not return
def stop_server(auth_client, server_uuid):
    """Function to stop server"""
    # Check it's state first, as it is an error to stop it when it is already stopped (or in any other state
    # apart from running).
    server_state = get_server_state(auth_client, server_uuid)

    if (server_state == 'STARTING'):
        print("Server appears to be starting; waiting until it has completed before stopping")
        ret = wait_for_server(auth_client, server_uuid, 'RUNNING')
        if (ret != 0):
            raise Exception("Server not in RUNNING state, cannot be stopped")

        server_state = get_server_state(auth_client, server_uuid)

    if (server_state == 'RUNNING'):
        change_server_status(auth_client, server_uuid, 'STOPPED')

    if (server_state == 'NOT_FOUND'):
        return server_state

    # Check we actually made it to STOPPED state
    ret = wait_for_server(auth_client, server_uuid, 'STOPPED')
    if (ret != 0):
        raise Exception("Server failed to STOP")

    server_state = get_server_state(auth_client, server_uuid)
    return server_state

def StopVM(customerUUID, customerUsername, customerPassword, serverUUID, isVerbose=False):
    auth_client = api_session(customerUsername, customerUUID, customerPassword)
    print "authentication done"
    server_state = stop_server(auth_client, serverUUID)
    return server_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('customerUUID', nargs='*', help="The UUID of the Customer")
    parser.add_argument('customerUsername',  nargs=1, help="The Username of the Customer")
    parser.add_argument('customerPassword',  nargs=1, help="The password for the Customer")
    parser.add_argument('serverUUID', nargs=1, help="The UUID of the Server to be stopped")
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

    ret = StopVM(cmdargs.customerUUID[0],
                cmdargs.customerUsername[0],
                cmdargs.customerPassword[0],
                cmdargs.serverUUID[0],
                isVerbose)


