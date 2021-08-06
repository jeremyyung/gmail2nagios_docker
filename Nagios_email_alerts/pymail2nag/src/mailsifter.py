import re
import json
import os
import logging

class GWorker:
    def __init__(self,json_file_path):
        self.out_file = json_file_path

    def processEmail(self,msgjson):
        headerjson = self.reduceHeader(msgjson)
        bodyjson = self.reduceBody(msgjson['Body'])
        id_chain, info_payload = self.getIDChain(headerjson,bodyjson)
        dbtext = self.getDBJSON()
        self.updateDB(id_chain, info_payload, dbtext)
        logging.info("ID Chain:\n%s\nWritten to json db:\n%s" %
                     (json.dumps(id_chain, indent=2), json.dumps(info_payload, indent=2))
        )

    def reduceHeader(self,emailjson):
        header_dict = {}
        header_dict['date'] = self.trimTimeStr(emailjson['Date'])
        header_dict['subject'] = emailjson['Subject']
        header_dict['origin_address'] = self.recTracker(emailjson)
        return header_dict

    def trimTimeStr(self,tstr):
        return re.search(r'^.*(?= [\-\+].*)',tstr).group(0).strip(" \'")

    def recTracker(self,emjs):
        """"""
        sd = ''
        targetblock = emjs['received_trail'][0]
        sender_domain = re.search('(\w*\.)*com',targetblock).group()
        if sender_domain != None and not (sender_domain.__contains__('icmanage.com')):
            sd = sender_domain
        else:
            sd = emjs['From']
        return sd

    def reduceBody(self,btext):
        body_dict = {}
        regex_dict = self.getRegexStr()
        search_chart = {
            'host':r'(?<=Host:).*',
            'user':r'(?<=User:).*',
            'program':r'(?<=Program:).*',
            'status':regex_dict['status_regex'],
            'status_text':regex_dict['text_regex']
        }
        for key in search_chart.keys():
            body_substr = re.search(search_chart[key], btext)
            if(body_substr) == None:
                if key == 'status':
                    body_dict['status'] = 'UNKNOWN'
                elif key == 'status_text':
                    body_dict['status_text'] = re.search('(.*)', btext).group(0).strip(" \'\r")
                else:
                    body_dict[key] = 'UNDEFINED'
            else:
                body_dict[key] = body_substr.group(0).strip(" \'\r")

        body_dict = self.doubleCheck(body_dict,btext)

        return body_dict

    def doubleCheck(self, body_dict, body_text):
        """
        For certain programs, you need to process the body text in a different way.
        :param body_dict:
        :param body_text:
        :return:
        """
        if body_dict['program'] == "check_sqlrep":
            #check_sqlrep doesn't have a 'status:' section, so check "IO Thread / SQL Thread" columns on each line.
            #If one of them does not equal 'Yes', set status to CRITICAL and return text as one long string.
            all_svr_status = re.findall('(\d+\..*)', body_text,flags=re.MULTILINE)
            body_dict['status'] = 'OK'
            for svrline in all_svr_status:
                nospace_status = (re.sub(r'(\s+)','*',svrline)).split('*')
                if nospace_status[3] != 'Yes' or nospace_status[4] != 'Yes':
                    body_dict['status'] = 'CRITICAL'
            if all_svr_status:
                body_dict['status_text'] = ' ** '.join(all_svr_status)
        return body_dict

    def getRegexStr(self):
        status_list = ['WARNING', 'OK', 'CRITICAL', 'warning', 'ok', 'critical']
        templates = {
            'status_regex' : '(%s)(?=:)',
            'text_regex' : '(%s)(.*)'
        }

        for key in templates.keys():
            bucket = []
            grp_str = ''
            template_str = templates[key]
            for t in status_list:
                if key == 'status_regex':
                    grp_str = '(%s)' % t
                if key == 'text_regex':
                    grp_str = '(?<=%s:)' % t
                bucket.append(grp_str)
            regx_select_str = str.join('|',bucket)
            templates[key] = template_str % regx_select_str
        return templates

    def getIDChain(self,header,body):
        hdict = header
        bdict = body
        id_chain = {
            'origin_email':hdict['origin_address'],
            'hostname':bdict['host'],
            'program':bdict['program']
        }
        info_payload = {
            'date':hdict['date'],
            'user':bdict['user'],
            'status':bdict['status'],
            'status_text':bdict['status_text'],
            'program':bdict['program']
        }
        return (id_chain,info_payload)

    def writeDBJSON(self,jsonobj):
        with open(self.out_file, 'w+') as ofile:
            json.dump(jsonobj, ofile)
            ofile.close()

    def getDBJSON(self):
        if not os.path.exists(self.out_file):
            self.writeDBJSON({'Alerts': {}})
        with open(self.out_file, 'r') as rfile:
            try:
                output = json.load(rfile)
                rfile.close()
                return output
            except:
                logging.warning("Invalid JSON in g2n.json file. Might be corrupt, try erasing and start again.")

    def updateDB(self, idchain, jsonpayload, filejson):
        try:
            orig_block = filejson['Alerts'][idchain['origin_email']]
            try:
                host_block = orig_block['Hosts'][idchain['hostname']]
                try:
                    filejson['Alerts'][idchain['origin_email']]["Hosts"][idchain['hostname']]['Programs'][idchain['program']] = jsonpayload
                except KeyError as k:
                    logging.info("Couldn't find program %s, may be an issue with json file." % k)
            except KeyError as k:
                #Generate hostblock, add to tempjson
                logging.info("Couldn't find host %s, creating program block" % k)
                filejson['Alerts'][idchain['origin_email']]["Hosts"][idchain['hostname']] = {
                    'Programs': {
                        idchain['program']:jsonpayload
                    }
                }
        except KeyError as k:
            #Generate whole block and add to tempjson
            logging.info("Couldn't find origin email %s, creating host block." % k)
            filejson['Alerts'][idchain['origin_email']] = {
                'Hosts': {
                    idchain['hostname']:{
                        'Programs':{
                            idchain['program']:jsonpayload
                        }
                    }
                }
            }
        self.writeDBJSON(filejson)
        return 0

if __name__ == '__main__':
    print("Usually imported by mailreader.py")
