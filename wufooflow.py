#!/usr/bin/env python

import calendar
import ConfigParser
import json
import requests
import os
import time
from optparse import OptionParser #use optparse because running on python 2.6 

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MAX_RETRIES = 10

wf_user = None
wf_apikey = None
wf_url = None
db_user = None
db_pass = None
db_url = None


def getLatestEntryInCloudant():
    
    r = requests.get(os.path.join(wf_url, 'users.json'), auth=(wf_apikey, 'foo'))
    print json.dumps(json.loads(r.text), indent=1)

def getEntriesFromWufoo( fromEntry=0):
    pass

def postEntriesToCloudant( docs ):
    pass

def main():
    global wf_user, wf_apikey, db_user, db_pass, db_url, wf_version

    current_run = calendar.timegm(time.gmtime())
    optparser = OptionParser()
    optparser.add_option(
        '-c',
        dest='config_file',
        help='config file path',
        default='./wufoo.ini'
    )
    
    (options, args) = optparser.parse_args()
    config = ConfigParser.RawConfigParser()
    config.read(options.config_file)
    wf_user = config.get('Wufoo', 'wf_user')
    wf_apikey = config.get('Wufoo', 'wf_apikey')
    wf_url = config.get('Wufoo', 'wf_url')
    db_url = config.get("Cloudant", 'db_url')
    db_user = config.get("Cloudant", 'db_user')
    db_pass = config.get("Cloudant", 'db_pass')

    entryNum = getLatestEntryInCloudant()

    formEntries = getEntriesFromWufoo( fromEntry = entryNum )

    postEntriesToCloudant(formEntries)
    

if __name__ == '__main__':
    main()