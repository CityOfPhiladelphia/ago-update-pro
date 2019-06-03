from arcgis.gis import GIS
import os
import glob
import multiprocessing
from datetime import datetime
from configparser import ConfigParser
import logging
import smtplib
from email.mime.text import MIMEText
import socket

config = ConfigParser()
config.read('ago_upload_config.ini')

# Logging variables
MAX_BYTES = config.get('logging', 'max_bytes')  # in bytes
# Max number appended to log files when MAX_BYTES reached
BACKUP_COUNT = config.get('logging', 'file_count')

# Create file logger (change logging level from default ERROR with the 'level' variable, i.e. DEBUG, INFO, WARN, ERROR, CRITICAL)
logging.basicConfig(filename='ago_upload_log.txt', level=logging.INFO, format=('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()


def sendemail(sender, subject, text, recipientslist):
    relay = config.get('email', 'relay')
    commaspace = ', '
    msg = MIMEText(text, 'html')
    msg['To'] = commaspace.join(recipientslist)
    msg['From'] = sender
    msg['X-Priority'] = '2'
    msg['Subject'] = subject
    server = smtplib.SMTP(relay)
    server.sendmail(sender, recipientslist, msg.as_string())
    server.quit()


def sd_update(sd):
    name = sd.split('.')[0]
    sdItem = gis.content.search("title:{} AND owner:{}".format(name, user), item_type="Service Definition")[0]
    sdItem.update(data=sd)
    print(name)

    fs = sdItem.publish(overwrite=True)

    if shrOrg or shrEveryone or shrGroups:
        fs.share(org=shrOrg, everyone=shrEveryone, groups=shrGroups)

    os.remove(sd)
    print(str(name) + ' done.')

# Set email alert options
email_sender = config.get('email', 'sender')
email_recipients = config.get('email', 'recipients').split(',')
email_subject = 'AGO Update Failure'

# Set AGO connection options
portal = config.get('ago', 'portal')
user = config.get('ago', 'user')
password = config.get('ago', 'password')
proxy = config.get('ago', 'proxy')

# Set FS sharing options
shrOrg = config.getboolean('ago', 'shrOrg')
shrEveryone = config.getboolean('ago', 'shrEveryone')
shrGroups = config.get('ago', 'shrGroups')

# Get the list of service defintions to update in AGO
service_definitions = glob.glob('*.sd')

# Define the AGO organization to connect to
gis = GIS(portal, user, password, proxy_host=proxy, proxy_port=8080)


def main():
    workers = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(workers)
    pool.map(sd_update, service_definitions)
    pool.close()
    pool.join()

if __name__ == '__main__':
    start = datetime.now()
    try:
        main()
    except Exception as e:
        logger.error('AGO upload failed: ' + str(e))
        email_body = "AGO service definition upload failure. Please see the log for details on server {}.".format(socket.gethostbyname(socket.gethostname()))
        sendemail(email_sender, email_subject, email_body, email_recipients)
    finish = datetime.now() - start
    logger.info('AGO upload complete in ' + str(finish))
