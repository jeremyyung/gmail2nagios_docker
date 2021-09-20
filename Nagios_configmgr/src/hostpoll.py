#!/usr/bin/env python3
import json
import sys
import datetime
import os
import re
'''
Main script used by Nagios services; reads g2n.json and updates status in GUI.
Useage: ./hostpoll.py $SOURCE_ADDRESS $SERVER_NAME $SCRIPT_NAME
'''
src_addr = sys.argv[1]
hostname = sys.argv[2]
hostname = (re.sub(r'--.*--', '', hostname)) #Strip out postfix if present
svc_name = sys.argv[3]
exit_codes = {'OK':0,'ok':0,'WARNING':1,'warning':1,'CRITICAL':2,'critical':2,'UNKNOWN':3,'unknown':3}

#Default g2n.json file location can be overwritten with $G2N_FILE environment variable.
if os.getenv('G2N_FILE') != None:
  g2n_file = os.getenv('G2N_FILE')
else:
  #Just a default path.
  g2n_file = '/home/jeremy/Desktop/RC2GD/Projects/nagiosmon/Nagios_configmgr/testdir/g2n.json'

with open(g2n_file, 'r') as rfile:
    g2n_json = json.load(rfile)
    rfile.close()
host_block = g2n_json['Alerts'][src_addr]['Hosts'][hostname]
pgm_block = host_block['Programs'][svc_name]
timestamp = datetime.datetime.strptime(pgm_block['date'], "%a, %d %b %Y %H:%M:%S")

#If an entry has not been updated for more than 5 days, return 'critical' status.
time_delta_days = (datetime.datetime.now() - timestamp).days
if time_delta_days > 5:
    print("Last email from %s received %d days ago. (limit = 5)" % (src_addr,time_delta_days))
    sys.exit(2)

#Otherwise, print status text and use the right exit code.
print(pgm_block['status_text'])
ecode = exit_codes[pgm_block['status']]
sys.exit(ecode)
