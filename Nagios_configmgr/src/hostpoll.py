#!/usr/bin/env python3
import json
import sys
import datetime
import os
#Main script used by Nagios services. Will read g2n DB file and update nagios allerts accordingly.
#Location of g2n.json database file specified by $G2N_FILE environment variable
#Useage: ./hostpoll.py $SOURCE_ADDRESS $SERVER_NAME $SCRIPT_NAME
src_addr = sys.argv[1]
hostname = sys.argv[2]
svc_name = sys.argv[3]
exit_codes = {'OK':0,'ok':0,'WARNING':1,'warning':1,'CRITICAL':2,'critical':2,'UNKNOWN':3,'unknown':3}

#Get email alert status (status, status_text,date) from g2n DB file.
if os.getenv('G2N_FILE') != None:
  g2n_file = os.getenv('G2N_FILE')
else:
  g2n_file = '/home/jeremy/Desktop/RC2GD/Projects/Nagios_configmgr/testdir/g2n.json'

with open(g2n_file, 'r') as rfile:
    g2n_json = json.load(rfile)
    rfile.close()
host_block = g2n_json['Alerts'][src_addr]['Hosts'][hostname]
pgm_block = host_block['Programs'][svc_name]
timestamp = datetime.datetime.strptime(pgm_block['date'], "%a, %d %b %Y %H:%M:%S")

#If alert entry has not been updated for more than 5 days, return 'critical' status.
time_delta_days = (datetime.datetime.now() - timestamp).days
if time_delta_days > 5:
    print("Last notice received %d days ago. (limit = 5)" % time_delta_days)
    sys.exit(2)

#Otherwise, print status text and use the right exit code.
print(pgm_block['status_text'])
ecode = exit_codes[pgm_block['status']]
sys.exit(ecode)
