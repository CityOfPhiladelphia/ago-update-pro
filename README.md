# ago-update-pro

These scripts utilize ArcGIS Pro and Python 3.x.

sd_export.py - exports a series of ArcGIS Online and ArcGIS Enterprise compatible service defintions from a folder of staged ArcGIS Pro .aprx files, requires Esri licensing

ago_upload_sd.py - uploads the exported service defition files to user defined portal (AGO or AGE) using multiprocessing, does not require Esri licensing

These scripts currently run sequentially, but can be run independently of each other

These user defined in the config file for the service definition upload must be the owner of the feature servcies.
