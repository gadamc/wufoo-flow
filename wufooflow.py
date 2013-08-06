#!/usr/bin/env python

import calendar
import ConfigParser
import json
import requests
import os
import time
import copy
from optparse import OptionParser #use optparse because running on python 2.6 


wf_user = None
wf_apikey = None
wf_url = None
db_user = None
db_pass = None
db_url = None
wf_formid = None

good_status_codes = (200,201)
overwriteable_fields = ('Location', 'Number_of_new_DB_Nodes', 'Date_of_Expected_Delivery',  'Notes')

class WuFooFlowError(Exception):
  pass

def parseDoc(doc):
  
  for k,v in doc.items():
    

    #strips off any spaces found in the keys.
    del doc[k]
    kk = k.strip(' ') 
    doc[kk] = v  

    # is this recursive code correct?
    if isinstance(v, dict):
      doc[kk] = parseDoc(v)

    else:
      # see if this string is really an int or a float
      if (isinstance(v,str) or isinstance(v, unicode)):

        if v.isdigit()==True: #int
          doc[kk] = int(v)
        else: #try a float
          try:
            if math.isnan(float(v))==False:
              doc[kk] = float(v) 
          except:
            pass      

  return doc

def getWuFoo(apicall = ''):
  '''
    returns requests.get object.

  '''
  wufoocall = os.path.join(wf_url, apicall)  #should probably use urlparse
  r =  requests.get(wufoocall, auth=(wf_apikey, 'foo'))
  if r.status_code  not in good_status_codes:
    raise WuFooFlowError('bad status code (%d) making wufoo call (%s)' %  (r.status_code, wufoocall))
  return r


def getCloudant(apicall = ''):
  '''
    returns reqeusts.get object
  '''

  cloudantcall = os.path.join(db_url, apicall) #should probably use urlparse
  r = requests.get(cloudantcall , auth=(db_user, db_pass))
  if r.status_code  not in good_status_codes:
    raise WuFooFlowError('bad status code (%d) making cloudant call (%s)' %  (r.status_code, cloudantcall))
  return r



def testWuFooUser():
  '''
    prints to screen wufoo user info
  '''
  r = getWuFoo('users.json')
  print json.dumps(json.loads(r.text), indent=1)


def testCloudantUser():
  '''
    prints to screen cloudant user info
  '''
  r = getCloudant()
  print json.dumps(json.loads(r.text), indent=1)


def getWufooFields():
  '''
    returns a list of Field objects for the wufoo form specified in the configuration.

  '''
  return json.loads(getWuFoo( '/'.join( ('forms', wf_formid,  'fields.json') ) ).text)['Fields']

def getEntriesFromWufoo( fromEntry=0):
  '''
    returns a list of entry objects for the wufoo form specified in the configuration

  '''
  return json.loads(getWuFoo( '/'.join( ('forms', wf_formid,  'entries.json?Filter1=EntryId+Is_greater_than+%d' % fromEntry) ) ).text)['Entries']


def getLatestEntryInCloudant():
  '''
    returns the largest value of EntryId for docs in cloudant.

  '''
  vr = json.loads(getCloudant( '_design/app/_view/byentryid?limit=1&descending=true').text)['rows']
  if len(vr) is 0: return 0
  return vr[0]['key']


def getFieldTitle(FieldID, fields):
  '''
    brute force find and build a title for this FieldID

  '''

  for afield in fields:
    if afield.has_key('SubFields'):
      for subfield in afield['SubFields']:
        if subfield['ID'] == FieldID:
          return ('%s %s' % (afield['Title'], subfield['Label'])).replace(' ', '_')
    if afield['ID'] == FieldID:
      return afield['Title'].replace(' ', '_')


def createDoc(entry, fields):
  
  doc = {}

  for key in entry:
    if key.startswith('Field'):
      title = getFieldTitle(key, fields)

      if title in overwriteable_fields:
        #print title, entry[key]
        if doc.get(title, '') == '':  #assume that we want to overwrite certain fields in the wufoo form
          #however, this assumes that only one of the instances of overwriteable_fields are not empty.
          # try:
          #   print 'replacing', doc[title], 'with', entry[key]
          # except: 
          #   pass
          #print 'replacing:', title, entry[key]
          doc[ title ] = entry[key]
      else: 
        doc[ title ] = entry[key]

    else:
      doc[key] = entry[key]


  #clean the doc
  clean_doc = copy.deepcopy(doc)

  if doc['Service_Provider'] is not 'AWS':
    for key in doc.iterkeys():
      if key.startswith('AWS'):
        del clean_doc[key]


  return parseDoc(clean_doc)

def postDocsToCloudant( docs ):

  headers = {'content-type': 'application/json'}
  url = os.path.join(db_url, '_bulk_docs') #should probably use urlparse

  r = requests.post(url, auth=(db_user, db_pass), data=json.dumps(docs), headers=headers)

  if r.status_code  not in good_status_codes:
    raise WuFooFlowError('bad status code (%d) POST to (%s)' %  (r.status_code, url))
  return r


def loadConfigFile(config_file):

  global wf_user, wf_url, wf_apikey, db_user, db_pass, db_url, wf_formid

  config = ConfigParser.RawConfigParser()
  config.read(config_file)
  wf_user = config.get('Wufoo', 'wf_user')
  wf_apikey = config.get('Wufoo', 'wf_apikey')
  wf_url = config.get('Wufoo', 'wf_url')
  wf_formid = config.get('Wufoo', 'wf_formid')
  db_url = config.get("Cloudant", 'db_url')
  db_user = config.get("Cloudant", 'db_user')
  db_pass = config.get("Cloudant", 'db_pass')

def main():

  current_run = calendar.timegm(time.gmtime())
  optparser = OptionParser()
  optparser.add_option(
    '-c',
    dest='config_file',
    help='config file path',
    default='./wufoo.ini'
  )
  
  optparser.add_option(
    '--tw', dest="test_wufoo",
    help='If set, just test for WuFoo user info and quit.',
    action="store_true"
  )

  optparser.add_option(
    '--tc', dest="test_cloudant",
    help='If set, get the Cloudant database info and quit.',
    action="store_true"
  )

  (options, args) = optparser.parse_args()

  loadConfigFile(options.config_file)

  if options.test_cloudant or options.test_wufoo:
    if options.test_wufoo:
      testWuFooUser()
    if options.test_cloudant:
      testCloudantUser()

    return

  wufoo_entries = getEntriesFromWufoo( getLatestEntryInCloudant() )
  wufoo_fields = getWufooFields()
  docs = {'docs':[]}
  
  for an_entry in wufoo_entries:
    docs['docs'].append( createDoc(an_entry, wufoo_fields) )

  postDocsToCloudant(docs)
    
if __name__ == '__main__':
  main()