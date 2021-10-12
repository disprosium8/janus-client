import requests, json, getpass
from yaml import load as yload

output = {}
filename = 'auth.yaml' 
with open(filename, 'r') as fd:
    output = yload(fd.read())

token_url = output['AUTH_ENDPOINT']
api_url = output['API_ENDPOINT']
RO_user = output['USERNAME']
RO_password = output['PASSWORD']

client_id = output['CLIEND_ID']
client_secret = output['SECRET']

data = {'grant_type': 'password','username': RO_user, 'password': RO_password}
#data = {'grant_type': 'client_credentials'}

print (token_url)

access_token_response = requests.post(token_url, data=data, verify=False, allow_redirects=False, auth=(client_id, client_secret))
print (data, client_id, client_secret)
tokens = json.loads(access_token_response.text)
print (tokens)
print ('-'*100)
## Step C - now we can use the access_token to make as many calls as we want.
#
api_call_headers = {'Authorization': 'Bearer ' + tokens['access_token']}

for endpoint in ['/service/89239501-d8c0-4f14-97fa-2c0a9afc0dce/status']:
#for endpoint in ['/sense/service/1f77c284-c43b-42bf-ab7b-f783e0297c9b/status', '/sense/discovery/edgepoints/urn:ogf:network:ultralight.org:2013']:
    test_api_url = '%s/%s' % (api_url, endpoint)
    api_call_response = requests.get(test_api_url, headers=api_call_headers, verify=False)
    print (test_api_url)
    print (api_call_headers)
    print (api_call_response.text)
    print ('='*100)


intent = {
    "service_type": "Multi-Path P2P VLAN",
    "service_alias": "DTNaaS-CERN-3989-API",
    "ip_ranges": [
        {
            "start": "10.4.44.101/24",
            "end": "10.4.44.102/24"
        }
    ],
    "connections": [
        {
            "bandwidth": {
                "qos_class": "guaranteedCapped",
                "capacity": "1000"
            },
            "name": "Connection 1",
            "terminals": [
                {
                    "label": "3989",
                    "assign_ip": False,
                    "uri": "urn:ogf:network:cern.ch:2013:s0:1_1:production7"
                },
                {
                    "label": "3989",
                    "assign_ip": False,
                    "uri": "urn:ogf:network:cern.ch:2013:cixp-surfnet-dtn.cern.ch"
                }
            ]
        }
    ]
}


endpoint = '/sense/service'
url = f"{api_url}{endpoint}"
api_call_headers.update({"Content-type": "application/json"})
res = requests.post(url, headers=api_call_headers, verify=False, data=json.dumps(intent))
print (res.text, res.status_code)
print ('='*100)

exit(1)

endpoint = '/sense/service/89239501-d8c0-4f14-97fa-2c0a9afc0dce'
url = f"{api_url}/{endpoint}"
res = requests.post(url, headers=api_call_headers, verify=False)
print (res.text, res.status_code)
print ('='*100)

exit(1)

endpoint = '/sense/service/89239501-d8c0-4f14-97fa-2c0a9afc0dce/reserve'
url = f"{api_url}/{endpoint}"
res = requests.put(url, headers=api_call_headers, verify=False)
print (res.text, res.status_code)
print ('='*100)

exit(1)

endpoint = '/sense/service/89239501-d8c0-4f14-97fa-2c0a9afc0dce/release'
url = f"{api_url}/{endpoint}"
res = requests.put(url, headers=api_call_headers, verify=False)
print (res.text)
print ('='*100)

endpoint = '/sense/service/89239501-d8c0-4f14-97fa-2c0a9afc0dce/terminate'
url = f"{api_url}/{endpoint}"
res = requests.put(url, headers=api_call_headers, verify=False)
print (res.text)
print ('='*100)
