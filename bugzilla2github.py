#!/usr/bin/env python
# -*- coding: utf-8 -*
#
# Program to migrate Bugzilla to github
# - first connect to database
# - retrieve all bug reports
# - export all attachments: bug_id, filename

import json, getopt, os, pprint, re, requests, sys, time, xml.etree.ElementTree, psycopg2
from pprint import pprint,pformat

reload(sys)
sys.setdefaultencoding('utf-8')

# force_update = True
xml_file = "show_bug_tiny.cgi.xml"
github_url = "https://api.github.com"
github_owner = "kwoot"
github_repo = "bz2gh"
github_token = "eca81797f8574028556102d22f9b9517247e011c"
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
        cur = conn.cursor()
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
        cur = conn.cursor()
        # execute the SELECT statement
        cur.execute(""" SELECT * from bugs limit 10 """,)

        results = cur.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return results

# Start connection to database
conn = psycopg2.connect(host=dbhost,database=database, user=dbuser, password=dbpassword)
# read all bug reports
bugs=read_bugs(conn)
for bug in bugs:
    pprint(bug)

# close the communication with the PostgresQL database
if conn is not None:
    conn.close()
