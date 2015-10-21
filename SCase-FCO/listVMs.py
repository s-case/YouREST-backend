
from fcoAPI.api import getToken
from fcoAPI.api import list_server

import argparse

ENDPOINT = "https://cp.sd1.flexiant.net:4442/"

# Get the API session
def api_session(customerUsername, customerUUID, customerPassword):
    """Function to set up api session, import credentials etc."""
    token = getToken(ENDPOINT, customerUsername, customerUUID, customerPassword)
    auth_client = dict(endpoint=ENDPOINT, token=token)
    return auth_client

def ListVM(customerUUID, customerUsername, customerPassword, isVerbose=False):
    auth_client = api_session(customerUsername, customerUUID, customerPassword)
    servers = list_server(auth_client, customerUUID)
    
    total = servers['totalCount']
    print "=============================================================================="
    print "Total %s VMs available for the account %s " %(total, customerUsername)
    count = 0
    while (count != total):
        server = servers['list'][count]
        print "=============================================================================="
        print "Server Name: %s \n Server UUID: %s \n Server Status: %s \n Server CPU count: %s \n Server RAM amount: %s" \
        %(server['resourceName'], server['resourceUUID'], server['status'], server['cpu'], server['ram'])
        count = count + 1
    print "=============================================================================="
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('customerUUID', nargs='*', help="The UUID of the Customer")
    parser.add_argument('customerUsername',  nargs=1, help="The Username of the Customer")
    parser.add_argument('customerPassword',  nargs=1, help="The password for the Customer")
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
  
    ret = ListVM(cmdargs.customerUUID[0],
                cmdargs.customerUsername[0],
                cmdargs.customerPassword[0],
                cmdargs.serverUUID[0],
                isVerbose)
