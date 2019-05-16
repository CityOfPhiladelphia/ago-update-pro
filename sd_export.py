import arcpy
import os
import glob
from arcgis.gis import GIS
from configparser import ConfigParser
import logging
import smtplib
from email.mime.text import MIMEText
import socket

config = ConfigParser()
config.read('sd_export_config.ini')

# Logging variables
MAX_BYTES = config.get('logging', 'max_bytes')  # in bytes
# Max number appended to log files when MAX_BYTES reached
BACKUP_COUNT = config.get('logging', 'file_count')

# Create file logger (change logging level from default ERROR with the 'level' variable, i.e. DEBUG, INFO, WARN, ERROR, CRITICAL)
logging.basicConfig(filename='sd_export_log.txt', level=logging.INFO, format=('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
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


def checks(mp):
    # Get record count and schema of table to update
    fc = mp.listLayers()[0].dataSource
    count = int(arcpy.GetCount_management(fc)[0])
    field_names = [f.name for f in arcpy.ListFields(fc)]
    shapes = [f.name for f in arcpy.ListFields(fc, 'shape*')]
    tbl_fields = sorted(set(field_names) - set(shapes))
    # Get schema of table in AGO
    fsItem = gis.content.search("title:{} AND owner:{}".format(mp.name, user), item_type="Feature Service")[0]
    layer = fsItem.layers[0]
    ago_fields = []
    for f in layer.properties.fields:
        if 'Shape' not in f['name']:
            ago_fields.append(f['name'])
    # If everything matches up, return True, else False
    if sorted(ago_fields) == sorted(tbl_fields) and count > 0:
        return True
    else:
        return False


def create_sd(table):
    # Create a new SDDraft and stage to SD
    sddraft = str(table) + '.sddraft'
    sd = str(table) + '.sd'
    arcpy.mp.CreateWebLayerSDDraft(prj_mp, sddraft, prj_mp.name, "MY_HOSTED_SERVICES", "FEATURE_ACCESS")
    arcpy.StageService_server(sddraft, sd)
    os.remove(sddraft)

# Set email alert options
email_sender = config.get('email', 'sender')
email_recipients = config.get('email', 'recipients').split(',')
email_subject = 'AGO Update Failure'

# Set AGO connection options
portal = config.get('ago', 'portal')
user = config.get('ago', 'user')
password = config.get('ago', 'password')
proxy = config.get('ago', 'proxy')

# Set arcpy options
arcpy.SetLogHistory(False)
arcpy.env.workspace = os.getcwd()
arcpy.env.overwriteOutput = True

# Define where the .aprx files are located
prjPath = config.get('local', 'prjPath')

# Get a list of the .aprx files to stage the services
aprx_files = glob.glob(prjPath)

# For some reason SDDraft tool needs an explicit arcpy AGO login now
arcpy.SignInToPortal(portal, user, password)

# Define the AGO organization to connect to
gis = GIS(portal, user, password, proxy_host=proxy, proxy_port=8080)

# Files have to be created sequentially because ArcGIS Pro doesn't like multiprocessing
for aprx in aprx_files:
    prj = arcpy.mp.ArcGISProject(aprx)
    prj_mp = prj.listMaps()[0]
    try:
        if checks(prj_mp):
            print(prj_mp.name)
            create_sd(prj_mp.name)
            logger.info('{} service definition successfully created.'.format(prj_mp.name))
        else:
            logger.error('{} schema did not match or record count was 0.'.format(prj_mp.name))
            email_body = "{} service failed to update in ArcGIS Online. Please see the log for details on server {}.".format(prj_mp.name, socket.gethostbyname(socket.gethostname()))
            sendemail(email_sender, email_subject, email_body, email_recipients)
    except Exception as e:
        logger.error(prj_mp.name, e)
        email_body = "{} service failed to update in ArcGIS Online. Please see the log for details on server {}.".format(prj_mp.name, socket.gethostbyname(socket.gethostname()))
        sendemail(email_sender, email_subject, email_body, email_recipients)
        continue
