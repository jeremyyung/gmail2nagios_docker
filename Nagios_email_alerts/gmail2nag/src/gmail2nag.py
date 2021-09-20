#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import atexit
import subprocess
import json
from mailreader import GMailer

global pid_file
pid_file = '/tmp/p2n.pid'

def main():
    """
    This script searches a GMail mailbox for monitoring emails and builds a json database.
    Nagios then uses xxxx.py to examine this file and updates itself accordingly.
    All configurables come from environment variables, see loadDefEnv() for reference.
    """
    parser = argparse.ArgumentParser("Scrapes info from ICM monitoring emails and condenses them into a json file.")
    parser.add_argument('--debug', dest='debug', default=False, action='store_true', help='Turn on debug output.')
    parser.add_argument('-d', '--defaults', dest='def_env', default=False, action='store_true', help='Set default environment variables.')
    parser.add_argument('-L', '--log', dest='log_file', default="", required=False, help='File will log all stdout.')
    parser.add_argument('-m', '--limit', dest='email_limit', default=0, type=int, required=False, help='Limit the number of emails processed in one go.')
    parser.add_argument('-j', '--jsonfile', dest='json_db_file', required=False, default=os.curdir + "/g2n.json",
                        help='JSON formatted file that stores information scraped from emails. Put in current directory by default.')
    parser.add_argument('-e', '--emlfile', dest='email_file', required=False, default="", help='Process an .eml file, usually for testing purposes.')
    parser.add_argument('--rm', dest='rm_cust', required=False, default="", help='Remove a cusomter from the json db file.')
    parser.add_argument('-o', '--output', dest='outdb', default=False, action='store_true',help='Pretty print contents of json db file.')

    args = parser.parse_args()

    os.environ['GM_JSON_DB_FILE'] = args.json_db_file

    if args.debug:
        # Clearing out old handlers, ensures debug always prints out.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        if args.log_file:
            logging.basicConfig(filename=args.log_file,format='%(levelname)s:%(message)s', level=logging.DEBUG)
        else:
            logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    checkPID()
    if args.def_env:
      loadDefEnv()
    else:
      loadEnvFile()
    envConfig()

    if args.outdb:
        printG2N(args.json_db_file)
        sys.exit(0)

    if args.rm_cust == "":
        checkEmails(args.email_limit, args.json_db_file,args.email_file)
    else:
        delCustomer(args.rm_cust,args.json_db_file)


def loadDefEnv():
    """
    Loads default environment variables.
    """
    logging.info("Using default environment variables.")
    envjson = {
      "GM_URL":"imap.gmail.com",
      "GM_MAILBOX_NAME":"monitor_spam",
      "GM_MAIL_STATUS":"UNSEEN",
      "GM_USERNAME":"jeremy.yung@icmanage.com",
      "GM_API_PW":"zeilvzlgjqiozsxx",
    } 
    setEnv(envjson)

def loadEnvFile():
    """
    Loads environment variables in /tmp/g2n.env. Workaround for using this in a docker container.
    """
    logging.info("Using environment variables set in /tmp/g2n.env.")
    envjson = {"GM_URL":"","GM_MAILBOX_NAME":"","GM_MAIL_STATUS":"","GM_USERNAME":"","GM_API_PW":""}
    ejkeys = list(envjson.keys())
    
    f = open("/tmp/g2n.env")
    for index,line in enumerate(f):
      envjson[ejkeys[index]] = line.split()[0]
    
    setEnv(envjson)

def setEnv(envjson):
    logging.info("Setting environment variables.")
    for key in envjson.keys():
      os.environ[key] = envjson[key]

def envConfig():
    """
    Fetches environment variables and stores them in globals.
    """
    setGlobalVars(os.getenv('GM_URL'),
                  os.getenv('GM_MAILBOX_NAME'),
                  os.getenv('GM_MAIL_STATUS'),
                  os.getenv('GM_USERNAME'),
                  os.getenv('GM_API_PW')
                  )

def setGlobalVars(url,mbname,tstat,uname,pw):
    global gmail_url, mailbox_name, target_status, gm_username, gm_password, envlist
    gmail_url = url
    mailbox_name = mbname
    target_status = tstat
    gm_username = uname
    gm_password = pw
    envlist = [gmail_url, mailbox_name, target_status, gm_username, gm_password]

    logging.debug("Loaded configs:\n"
                  "*gmail_url=%s\n"
                  "*mailbox_name=%s\n"
                  "*target_status=%s\n"
                  "*gm_username=%s\n"
                  "*gm_password=%s" % (gmail_url, mailbox_name, target_status, gm_username, gm_password)
                  )

    if None in envlist:
        logging.error("Required environment variable(s) unset or empty, aborting!")
        sys.exit(1)

def checkEmails(lim,jsfilepath,emlfile):
    print("Checking emails...")
    emailer = GMailer(*envlist)
    if emlfile == "":
        emailer.login()
        emailer.getEmails()
        if lim > 0:
            emailer.dumpEmails(jspath=jsfilepath,limiter=lim)
        else:
            tracker = emailer.getMsgCount()
            while tracker != 0:
                try:
                    if emailer.dumpEmails(jspath=jsfilepath):
                        print("All emails processed, stopping until next run.")
                        break
                except:
                    logging.error("Email parser error, retrying...")
                    emailer.login()
                    emailer.getEmails()
                    tracker = emailer.getMsgCount()
        emailer.logout()
    else:
        if os.path.exists(emlfile):
            emailer.dumpFile(jspath=jsfilepath,email_file=emlfile)
        else:
            logging.warning("EML file not found.")
            sys.exit(1)

def delCustomer(srcemail, jsfilepath):
    """
    Removes source email specified in the '--rm' flag, from the g2n.json file.
    """
    with open(jsfilepath) as dbfile:
        jsondata = json.load(dbfile)
        del jsondata['Alerts'][srcemail]
    with open(jsfilepath,'w') as dbfile:
        json.dump(jsondata,dbfile)

def printG2N(jsfilepath):
    with open(jsfilepath) as dbfile:
        print(json.dumps(json.load(dbfile),indent=2))


def checkPID():
    """
    Records PID to /tmp/p2n.pid; helps determine if another instance of this script is still running.
    If so, then immediately stop the script to avoid any weird race conditions. File should be deleted on exit.
    """
    mypid = os.getpid()
    if not os.path.exists(pid_file):
        writePID(mypid)
    else:
        f = open(pid_file, "r")
        filepid = f.readline()
        process_search = subprocess.check_output(['ps', '-f', '--pid', str(filepid)]).decode('utf-8')
        is_running = process_search.__contains__('gmail2nag.py')
        if is_running:
            logging.warning("Previous instance still running, exiting without wiping PID file.")
            os._exit(1)
        else:
            logging.info("Found PID but it's not running this script. Recreating PID file before continuing.")
            os.remove(pid_file)
            writePID(mypid)

def writePID(pid):
    logging.info("Generating PID file.")
    file = open(pid_file, 'w+')
    file.write("%s" % pid)
    file.close()

@atexit.register
def rmPIDFile():
    logging.info('Running atexit() cleanup.')
    if os.path.exists(pid_file):
        logging.info('Removing p2n.pid')
        os.remove(pid_file)

if __name__ == '__main__':
    main()
