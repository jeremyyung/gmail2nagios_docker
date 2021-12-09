#!/usr/bin/env python3
import configparser
import os
import argparse
import logging
import json
import shutil

def main():
    """
    This script reads the json database file created by gmail2nag.py and creates custom nagios objects. Invoking it will
    purge all old settings and restart from scratch. (just for simplicity sake)
    """
    global template_text, address_map
    parser = argparse.ArgumentParser("Parses gmail2nag db file and creates nagios objects")
    parser.add_argument('--debug', dest='debug', default=False, action='store_true', help='Turn on debug output.')
    args = parser.parse_args()

    if args.debug:
        # Clearing out old handlers, ensures debug always prints out.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    try:
        #Read config files and load their data
        print("Generating nagios files...")
        curdir = os.path.dirname(os.path.realpath(__file__))
        logging.info("--Reading config files.")
        nconf = configparser.ConfigParser()
        nconf.read_file(open("%s/%s" % (curdir,'nobjtemplates.cfg')))
        template_text = nconf['OBJ_TEMPLATES']

        nconf.read_file(open("%s/%s" % (curdir,'nagmanager.cfg')))
        g2n_path = nconf['FILE_PATHS']['g2n_file']
        nagios_dir = nconf['FILE_PATHS']['nagios_dir']
        address_map = nconf.items('ADDRESS_MAPPING')

        #Start creating nagios obj files
        created_paths = makeSkeleton(nagios_dir)
        setCmdCfg(created_paths)
        g2n_json = deDupe(getG2N(g2n_path))
        makeObjects(g2n_json, created_paths)

        #Check if nagios.cfg file has correct cfg_dir param set
        checkConfig(nagios_dir,created_paths) 
        print("Files created, please restart Nagios.")

    except OSError as e:
        logging.error(e)

def deDupe(g2njson):
    '''Some hosts send emails from different sources. This trips up nagios, so I have to add --#-- postfixs.
    When a service calls hostpoll.py, it will remove this prefix.'''
    clean_g2n = g2njson
    host_src_list = {}
    for srcaddr in clean_g2n['Alerts']: #Make list of {hostname:[srcaddrs]}.
        hostdict = g2njson['Alerts'][srcaddr]['Hosts']
        for hostname in hostdict:
            if not host_src_list.keys().__contains__(hostname):
                host_src_list[hostname] = [srcaddr]
            elif not host_src_list[hostname].__contains__(srcaddr):
                host_src_list[hostname].append(srcaddr)
    for host in host_src_list: #Go through above list, if a host has > 1 source address, add --#-- postfix.
        if len(host_src_list[host]) > 1:
            #Deletes orignial host data and re-adds it with postfixed hostname.
            for index,srcaddr in enumerate(host_src_list[host]):
                hostnum = '%s--%s--' % (host,str(index))
                origdata = g2njson['Alerts'][srcaddr]['Hosts'][host]
                del clean_g2n['Alerts'][srcaddr]['Hosts'][host]
                clean_g2n['Alerts'][srcaddr]['Hosts'][hostnum] = origdata

    return clean_g2n

def getG2N(g2npath):
    logging.info("--Reading g2n.json file %s" % g2npath)
    with open(g2npath,'r') as rfile:
        g2njson = json.load(rfile)
        rfile.close()
    return g2njson

def makeSkeleton(nagdir):
    '''
    Create default files.
    :param nagdir: <nagios_dir> specified in nagmanager.cfg
    :return: List of paths created by makeSkeleton, referenced by other methods.
    '''
    obj_dir = nagdir + "/etc/services/icm_objects"
    wipeDir(obj_dir) #Wipes old config files.

    logging.info('--Creating base directories.')
    gen_paths = {} #Tracks generated directories
    base_structure = {
        '0_configs': ['custcontacts.cfg','hostgroups.cfg','icmtemplates.cfg'],
        '1_services': ['custservice.cfg','icmcommands.cfg']
    }

    logging.debug('Creating %s' % obj_dir)
    os.makedirs(obj_dir, exist_ok=True)
    gen_paths['nagios_directory'] = nagdir
    gen_paths['obj_directory'] = obj_dir

    for dirname in base_structure.keys():
        subpath = '%s/%s' % (obj_dir, dirname)
        logging.debug('Creating %s' % subpath)
        os.makedirs(subpath, exist_ok=True)
        gen_paths[dirname] = subpath

        file_list = base_structure[dirname]
        for fname in file_list:
            fpath = '%s/%s' % (subpath, fname)
            logging.debug('Creating file %s' % fpath)
            temp_text = template_text[fname]
            writeFile(fpath,temp_text)
            gen_paths[fname] = fpath
    return gen_paths

def setCmdCfg(created_paths):
    ppath = created_paths['nagios_directory'] + '/libexec'
    temptext = template_text['icmcommands.cfg'] % ppath
    cfgpath = created_paths['1_services'] + '/icmcommands.cfg'
    writeFile(cfgpath,temptext)

def makeObjects(g2njson, fpaths):
    obj_dict = {} #Files that go in "/0_configs"
    svc_dict = {} #Data that goes in "/1_services/custservice.cfg"
    for srcaddr in g2njson['Alerts']:
        #Match source address with customer name, stores in obj_dict.
        customer_name = getAddrCust(srcaddr)
        if not obj_dict.keys().__contains__(customer_name):
            obj_dict[customer_name] = {'servers':{}}

        src_host_dict = g2njson['Alerts'][srcaddr]['Hosts']
        for host in src_host_dict.keys():
            if not obj_dict[customer_name]['servers'].keys().__contains__(host):
                obj_dict[customer_name]['servers'][host] = {'source': [srcaddr]}
            else:
                obj_dict[customer_name]['servers'][host]['source'].append(srcaddr)

            #Create program-to-script list and stores it in svc_dict
            program_names = [prg for prg in src_host_dict[host]['Programs'].keys()]
            for prg in program_names:
                if not svc_dict.keys().__contains__(prg):
                    svc_dict[prg] = [host]
                if not svc_dict[prg].__contains__((host)):
                    svc_dict[prg].append(host)

    genService(svc_dict,fpaths)
    genHostFiles(obj_dict,fpaths)
    return

def genService(svc_dict, fpaths):
    text_stack = []
    fname = 'custservice.cfg'
    fpath = "%s/%s" % (fpaths['1_services'], fname)
    for svc in svc_dict.keys():
        hlist_str = ','.join(svc_dict[svc])
        if svc in ['check_file_rep', 'check_change_counter', 'check_sqlrep']:
            temp_text = template_text['svc-send-notice.cfg'] % (hlist_str,svc)
        else:
            temp_text = template_text['svc-no-notice.cfg'] % (hlist_str,svc)
        text_stack.append(temp_text)
    writeFile(fpath,"\n\n".join(text_stack))

def genHostFiles(obj_dict,fpaths):
    pdir = fpaths['obj_directory']
    hgrp_cfg_file_path = fpaths['0_configs'] + "/hostgroups.cfg"
    hgrp_stack = ""

    for cust in obj_dict.keys():
        ppath = "%s/%s" % (pdir,cust)
        os.makedirs(ppath, exist_ok=True)
        svrdicts = obj_dict[cust]['servers']
        svrlist = svrdicts.keys()
        temp_text = template_text['hostgroups.cfg'] % (cust, ','.join(svrlist))
        hgrp_stack = hgrp_stack + temp_text + '\n\n'

        for host in svrdicts.keys():
            src_list = svrdicts[host]['source']
            if len(src_list) == 1:
                cfgfile = "%s/%s.cfg" % (ppath, host)
                t_text = template_text['hostobj.cfg'] % (host, src_list[0])
                writeFile(cfgfile,t_text)
            else:
                for index,saddr in enumerate(src_list):
                    enum_name = "%s<%s>" % (host,index)
                    cfgfile = "%s/%s.cfg" % (ppath, enum_name)
                    t_text = template_text['hostobj.cfg'] % (host, saddr)
                    writeFile(cfgfile, t_text)

    writeFile(hgrp_cfg_file_path,hgrp_stack)
    return

def getAddrCust(addrstr):
    match = 'UNKNOWN'
    for cust,elist in address_map:
        if elist.split(',').__contains__(addrstr):
            match = cust
    if match == 'UNKNOWN':
        print("%s marked as UNKNOWN customer, double-check nagmanager.cfg under [ADDRESS_MAPPING]." % addrstr)
    return match

def writeFile(fpath,text):
    logging.debug('Writing to file %s' % fpath)
    file = open(fpath, 'w+')
    file.write(text)
    file.close()
    return

def checkConfig(nagios_dir,created_paths):
    cfg_file = "%s/etc/%s" % (nagios_dir,'nagios.cfg')
    obj_dir = created_paths['obj_directory']
    with open(cfg_file) as f:
      if obj_dir not in f.read():
        logging.error("Double check %s, make sure it has 'cfg_dir=%s'." % (cfg_file,obj_dir))

def wipeDir(dir_path):
    if os.path.exists(dir_path):
        logging.info('Erasing old config files in %s' % dir_path)
        shutil.rmtree(dir_path)

if __name__ == '__main__':
    main()
