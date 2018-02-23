#!/usr/bin/env python
# -*- coding: utf-8 -*
#
# Program to migrate Bugzilla to github
# - first connect to database
# - retrieve all bug reports
# - export all attachments: bug_id, filename
#
# How to use the script:
# 1. Generate a GitHub access token:
#    - on GitHub select "Settings"
#    - select "Personal access tokens"
#    - click "Generate new token"
#    - type a token description, i.e. "bugzilla2github"
#    - select "public_repo" to access just public repositories
#    - save the generated token into the migration script
# 2. Create a separate repo for testing purposes. THERE IS NO UNDO!
# 3. Copy bugzilla2github.conf.sample to bugzilla2github.conf
#    - Change all settings to fit your setup
# 4. Run the script. Good luck....

import json, getopt, os, pprint, re, requests, sys, time, xml.etree.ElementTree
import psycopg2, psycopg2.extras
import ConfigParser
from pprint import pprint,pformat

reload(sys)
sys.setdefaultencoding('utf-8')

# read config file
configFile = "bugzilla2github.conf"
config = ConfigParser.RawConfigParser()
try:
    config.read(configFile)
    # Read GitHub vars
    GITHUB_TOKEN = config.get('settings', 'github_token')
    GITHUB_URL = config.get('settings', 'github_url')
    GITHUB_OWNER = config.get('settings', 'github_owner')
    GITHUB_REPO = config.get('settings', 'github_repo')
    # read database vars
    ENGINE = config.get('settings', 'engine')
    HOST = config.get('settings', 'dbhost')
    DATABASE = config.get('settings', 'database')
    USER = config.get('settings', 'dbuser')
    PASSWORD = config.get('settings', 'dbpassword')
    PORT = config.get('settings', 'port')

except:
    print "Error reading configfile '" + configFile + "'."
    print "Program aborted."
    sys.exit(1)

# force_update = True

def read_bugs(conn):
    """ read bug data"""
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT * from bugs where bug_id=1295 """,)
        colnames = [desc[0] for desc in cur.description]
        results = cur.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return results,colnames

def read_comments(conn,bug_id):
    """ read bug comments data"""
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT * from longdescs where bug_id=%s limit 1""" % bug_id,)
        colnames = [desc[0] for desc in cur.description]
        results = cur.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return results,colnames

def read_attachment(conn,attach_id):
    """ read attachment data"""
    print type(attach_id)
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        #query=""" SELECT * from attachments where attach_id=%i  """ % (attach_id,)
        #print query
        cur.execute(""" SELECT * from attachments where attach_id=%s  """ % attach_id, )
        colnames = [desc[0] for desc in cur.description]
        results = cur.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return results,colnames

def save_attachment(conn,attach_id,filename):
    """ read BLOB data from a table """
    #conn = None
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT thedata FROM atatch_data WHERE id=%s """,(attach_id,))
        blob = cur.fetchone()
        open(path_to_dir + blob[0] + '.' + blob[1], 'wb').write(blob[2])
        # close the communication with the PostgresQL database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

# Start connection to database
conn = psycopg2.connect(host=HOST,database=DATABASE, user=USER, password=PASSWORD)
# read all bug reports
bugs,colnames=read_bugs(conn)
#pprint(bugs)
#pprint(colnames)
for bug in bugs:
    bug_id=bug['bug_id']
    #for field in colnames:
    #    print str(field) + " -> " + str(bug[str(field)])
    print "bug_id",bug_id
    print "bug_severity",bug['bug_severity']
    print "bug_status", bug['bug_status']
    print "short_desc", bug['short_desc']
    print "priority",bug['priority']
    print "version",bug['version']
    print "resolution",bug['resolution']

    comments,colnames=read_comments(conn,bug_id)
    #pprint(colnames)
    for comment in comments:
        comment_id=comment["comment_id"]
        attach_id=comment["extra_data"]
        if attach_id>0:
            print " attach_id",attach_id
            # check attachment record for this comment
            attachment,colnames=read_attachment(conn,attach_id)
            #for activity in activities:
            pprint(attachment)
            result=save_attachment(attach_id,bug_id,comment_id)

        #pprint(comment)
        print " comment_id",comment["comment_id"]
        print " text:",comment["thetext"]

# close the communication with the PostgresQL database
if conn is not None:
    conn.close()
