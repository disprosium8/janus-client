#!/usr/bin/env python
# coding: utf-8

# ## Initialization
#  * Import Janus Client modules
#  * Setup client parameter (controller URL, user, ssh key, etc.)
#  * Create a client instance
#  * Create sessions for each demo job
#  * Attach services to each session (host/container/profile mapping)

# ### Profile definition example
#  * Testing with various profiles for bridge, host, sriov, and macvlan networks.
#  * These, along with other profiles, are maintained on the Janus controller node
#   
# ```yaml
# 
# ```

# In[1]:


# get_ipython().run_line_magic('load_ext', 'autoreload')
# get_ipython().run_line_magic('autoreload', '2')

import time
import json
from janus_client import Client, Session, Service
from ESCPeval import setup, run_job, stop_job

# Evaluation specific vars
SRC_HOST="nersc-tbn-10"
DST_HOST="nersc-dtnaas-1"
TAG="host"
ITERS=1

# Janus setup
JANUS_URL="https://nersc-srv-1.testbed100.es.net:5000"

user = 'admin'
passwd = 'admin'
keypath = '~/.ssh/id_rsa_jupyter'
mypubkey = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDcwroYazmGmq9zygqN0oUHri6WZf5StzK3WsNZ1ihrydjbwvGY0qX7jEHdNS7ujbQgUfRx0jLBmYjdRfTyWaz6kZbjxNgYWev54iSUNarEnRK1Egn8YC6NF/en9FtYwrBb7uKeQBu2lib4aufogUkTT6JUm3qzUaKY04ZfyVisC8/zICdQE9Yp4X6PywPHfzH7eq/KH7tKRtgStlGsDzB/KIE+USJnDOdkHuuqpV+5P81lmpRoDlR5IcA7Jt11RoWq4GKSwn73y5iWaOUpj2/CHmLO83Do2WTaPJjd3hS4o6e0nDpdMA/Q7UvvoSLcxka9frqdcBkeBoYZc2prCmp9HbHQWheXYnD9pxOMHvPkYdd3wTzg/NgOx4qUshiqq0Uz/aMuP852p1imvdvZ5lrhij15Bxavsf62Vc2EbPJ5BYK+b/YHlDlrj1UwXjAcmcQLUWflPcRkfy0rEA602Mzi6JOJdH2/LNVpevRH4bdCrTIgrZT+OoNT3ZYkM8TYpGc= lzhang9@lzhang9-m11'


client = Client(JANUS_URL, auth=(user, passwd))

print ("\nAvailable LBNL profiles:")
# print ([x for x in client.profiles().json().keys() if x.startswith("lbnl")])
print ([x['name'] for x in client.profiles().json() if x['name'].startswith("lbnl")])
print ("\n")

sess_escp = client.getSession()
srv1 = Service(instances=[DST_HOST], image='dtnaas/tools',
               profile=f'lbnl-{TAG}', username=user, public_key=mypubkey)
srv2 = Service(instances=[SRC_HOST], image='dtnaas/tools',
               profile=f'lbnl-{TAG}', username=user, public_key=mypubkey)
sess_escp.addService(srv1)
sess_escp.addService(srv2)


print (f"{sess_escp}\n")


# ## DTN Service Startup
#  * Start each session created in previous step
#  * Check status
#  * View endpoint information

# In[2]:


res = sess_escp.start()
# print (sess_escp.status())


# In[3]:


print (f"-- Sess Endpoints:\n{sess_escp.endpoints()}")


# ## Demo job setup and execution
#  * ESCPeval module to initialize and run jobs given provided Janus sessions

# In[4]:


# Perform some setup work on the remote containers
from ESCPeval import setup, run_job, stop_job
sess_escp.user = user
sess_escp.keypath = keypath
setup(sess_escp)


# In[121]:


from ESCPeval import setup, run_job, stop_job
# Run ESCPeval jobs
# EScp arguments will change depending on the Janus profile used for container networking
# TODO: parse this out of the Janus profile and node info
# prof = client.profiles().json().get(f"lbnl-macvlan")
# print (prof)

# Host network example below for tbn-6,7
escp_args = {"src": "10.10.2.21",
#             "src_port": 22,      # we can override EScp ssh port numbers learned from Janus session
             "dst": "10.10.2.20",
#             "dst_port": 22,      # we can override EScp ssh port numbers learned from Janus session
             "iters": 1,
             "tag": "host"}

ret = run_job(sess_escp, SRC_HOST, **escp_args)


# ## Janus stop and cleanup routines
#  * It is possible to stop/start containers or destroy the sessions once workflow is complete

# In[3]:


sess_escp.stop()


# In[4]:


sess_escp.destroy()


# In[ ]:




