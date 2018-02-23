#!/usr/bin/env python
# -*- coding: utf-8 -*
#
# Program to migrate Bugzilla to github
# - first connect to database
# - retrieve all bug reports
# - export all attachments: bug_id, filename

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
    HOST = config.get('settings', 'host')
    NAME = config.get('settings', 'database')
    USER = config.get('settings', 'user')
    PASSWORD = config.get('settings', 'password')
    PORT = config.get('settings', 'port')

except:
    print "Error reading configfile '" + configFile + "'."
    print "Program aborted."
    sys.exit(1)

# force_update = True
xml_file = "show_bug_tiny.cgi.xml"
github_url = "https://api.github.com"
github_owner = "kwoot"
github_repo = "bz2gh"
# database connection details
dbhost="localhost"
database="bugzilla2"
dbuser="bugzilla"
dbpassword="bugzilla"


def read_blob(conn,part_id, path_to_dir):
    """ read BLOB data from a table """
    #conn = None
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT part_name, file_extension, drawing_data
                        FROM part_drawings
                        INNER JOIN parts on parts.part_id = part_drawings.part_id
                        WHERE parts.part_id = %s """,
                    (part_id,))

        blob = cur.fetchone()
        open(path_to_dir + blob[0] + '.' + blob[1], 'wb').write(blob[2])
        # close the communication with the PostgresQL database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

def read_bugs(conn):
    """ read bug data"""
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT * from bugs limit 2 """,)
        colnames = [desc[0] for desc in cur.description]
        results = cur.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return results,colnames

# Start connection to database
conn = psycopg2.connect(host=dbhost,database=database, user=dbuser, password=dbpassword)
# read all bug reports
bugs,colnames=read_bugs(conn)
#pprint(bugs)
#pprint(colnames)
for bug in bugs:
    #pprint(bug)
    #pprint(bug['bug_id'])
    #print "or this"
    #print(bug['bug_id'])
    for field in colnames:
        print str(field) + " -> " + str(bug[str(field)])

# close the communication with the PostgresQL database
if conn is not None:
    conn.close()
