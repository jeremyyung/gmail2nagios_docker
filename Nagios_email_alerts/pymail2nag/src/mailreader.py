import imaplib
import logging
import email
from mailsifter import GWorker

class GMailer:
    def __init__(self,url,mbname,tstat,uname,pw):
        """
        Sets GMail connection parameters and searches for emails.
        :param url: Gmail / mailserver URL
        :param mbname: Name of the mailbox you want to target. (e.g. monitor_spam)
        :param tstat: Searches for emails that match this target status. (e.g. UNSEEN)
        :param uname: Login username
        :param pw: Login password
        """
        self.gmail_url = url
        self.mailbox_name = mbname
        self.target_status = tstat
        self.username = uname
        self.password = pw

        # Stores the IDs of all emails that match search criteria.
        self.msg_ids = []

    def login(self):
        logging.info("Logging into Gmail.")
        self.imap = imaplib.IMAP4_SSL(self.gmail_url)
        try:
            self.imap.login(self.username, self.password)
            logging.debug("Login successful: %s" % self.imap.socket())
        except imaplib.IMAP4.error as e:
            logging.error('Error at login: %s' % e)

    def logout(self):
        logging.info("Logging out of Gmail.")
        self.imap.close()
        self.imap.logout()

    def getEmails(self):
        try:
            # Begin email search.
            logging.info("Starting email search...")
            status, errortxt = self.imap.select(self.mailbox_name, readonly=False)
            if status != 'OK':
                raise ValueError(errortxt[0].decode('utf-8'))
            self.response, messages = self.imap.search(None,self.target_status)

            # Store mail IDs in msg_ids list.
            self.msg_ids = messages[0].split()
            logging.debug("---Found %s emails in target mailbox for processing---" % len(self.msg_ids))
        except imaplib.IMAP4.error as i:
            logging.error("Encountered IMAP error, mailbox may not exist: %s" % i)
        except ValueError as v:
            raise

    def dumpEmails(self, jspath, limiter=0):
        """
        Main method for iterating through emails and dumping their data into json DB file.
        :param jspath: Path to json DB file
        :param limiter: Number of emails to process, usually specified with "-m". Does all emails if set to 0.
        :return:
        """
        gw = GWorker(jspath)
        if limiter == 0:
            ID_list = self.msg_ids
        else:
            logging.debug("Limiting search to %s emails." % limiter)
            ID_list = self.msg_ids[:limiter]
        try:
            # Convert each email ID from byte to string, then fetch the email.
            for i in ID_list:
                logging.debug("Processing email_ID %s" % i)
                m_id = i.decode('UTF-8')
                f_reply, f_msg = self.imap.fetch(m_id, "(RFC822)")
                # Strip out important information from email data.
                for entry in f_msg:
                    if isinstance(entry, tuple):
                        msg = email.message_from_bytes(entry[1])
                        self.fieldSort(gw, msg)

                #Delete the email thread
                self.imap.store(i, '+FLAGS', '\\Deleted')
        except:
            logging.warning("Something went wrong while processing email.")
            raise

    def dumpFile(self,jspath,email_file):
        """
        Same as dumpEmails, but it pulls data from a files specified with the '-e' flag.
        :param jspath: Path to json DB file
        :param email_file: File to *.eml file
        :return:
        """
        gw = GWorker(jspath)
        f = open(email_file, 'r')
        msg = email.message_from_file(f)
        self.fieldSort(gw, msg)

    def fieldSort(self, sifter_obj, msg_data):
        """Converts raw email into json data structure, then sends it off for processing."""
        jsonMsg = {}
        received_trail = []
        # Dumps each header field into a json object <jsonMsg>
        for field in msg_data.items():
            # <received_trail> should contain the last 2 'Received' headers
            if field[0] == 'Received':
                received_trail.append(field[1])
                if len(received_trail) >= 3:
                    received_trail.pop(0)
            else:
                jsonMsg[field[0]] = field[1]
        jsonMsg['received_trail'] = received_trail
        # Find & decode body text
        for part in msg_data.walk():
            if part.get_content_type() == "text/plain":
                jsonMsg['Body'] = (part.get_payload(decode=True)).decode("UTF-8")
        # Use mailsifty.py to format and dump json data into DB file
        sifter_obj.processEmail(jsonMsg)
        return jsonMsg

    def getMsgCount(self):
        return len(self.msg_ids)

    def getMBInfo(self):
        #List all available mailboxes, can be used in imap.select() method.
        print(self.imap.list())
        #Prints status of particular mailbox (# of messages, recent msgs, unseen msgs)
        print(self.imap.status(self.mailbox_name, '(MESSAGES RECENT UNSEEN)'))

if __name__ == '__main__':
    print("Usually called by gmail2nag.py")