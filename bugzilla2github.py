#!/usr/bin/env python
# -*- coding: utf-8 -*
#
# Program to migrate Bugzilla to github
# - first connect to database
# - retrieve all bug reports
# - export all attachments: bug_id, filename
#
# How to use the script:
# 0. Create a virtual environment containing modules mentioned in freeze.txt
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
from urlparse import urljoin

reload(sys)
sys.setdefaultencoding('utf-8')

path_to_dir="./attachments/"

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
    BUGZILLA_URL = config.get('settings', 'bugzilla_url')
    FILEREPO_URL = config.get('settings', 'filerepo_url')
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
    """
    Read bug data
    :param conn: database connection object
    :return: object with all bugs found, list of column names
    """
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT * from bugs where bug_id=1295 """,)
        colnames = [desc[0] for desc in cur.description]
        results = cur.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        results = None
        colnames = None
    return results,colnames

def read_comments(conn,bug_id):
    """
    Read bug comments data
    :param conn: database connection object
    :param bug_id: id of bug to retrieve
    :return: object with all comments found, list of column names
    """
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT * from longdescs where bug_id=%s """ % bug_id,)
        colnames = [desc[0] for desc in cur.description]
        results = cur.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        results = None
        colnames = None
    return results,colnames

def read_attachment(conn,attach_id):
    """
     Read attachment data
    :param conn: database connection object
    :param attach_id: id of attachment
    :return: Single object with record, list of column names
    """
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        #query=""" SELECT * from attachments where attach_id=%i  """ % (attach_id,)
        #print query
        cur.execute(""" SELECT * from attachments where attach_id=%s  """ % attach_id, )
        colnames = [desc[0] for desc in cur.description]
        result = cur.fetchone()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        result=None
        colnames=None
    return result,colnames

def save_attachment(conn,attach_id,bug_id,comment_id,filename):
    """
     Read BLOB data from a table and save to local disc
    :param conn: database connection object
    :param attach_id: id of attachment to save
    :param bug_id: id of bug to use in filename
    :param comment_id: if of comment to use in filename
    :param filename: Original filename of attachment
    :return: None
    """
    #conn = None
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT thedata FROM attach_data WHERE id=%s """,(attach_id,))
        blob = cur.fetchone()
        open(path_to_dir + str(bug_id) + '_' +  str(comment_id) + "_"+ filename, 'wb').write(blob[0])
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return

def get_reporters(conn):
    """
    Retrieve all users from Bugzilla database
    :param conn:  database connection object
    :return: object with all results
    """
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT * FROM profiles """)
        results = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    reporters={}
    for result in results:
        reporters[result["userid"]]=result
    return reporters,colnames


def get_reporter(reporters,reporter_id):
    """
    routine to find username+email for userid
    :param reporters: dictionary with all reporters, indexed on userid
    :param reporter_id: id of reporter to find
    :return: string username+email
    """
    # ['userid', 'login_name', 'cryptpassword', 'realname', 'disabledtext', 'disable_mail', 'mybugslink', 'extern_id']
    reporterobj=reporters[reporter_id]
    reporterstr=reporterobj["realname"]+" \<<"+reporterobj["login_name"]+">\>"
    return reporterstr


def create_body(reporters,bug):
    """
    Routine to create issue body text
    :param bug: object containing bug record
    :return: string with body text
    """
    # Note: the issue was created automatically with bugzilla2github.py tool
    # Bugzilla Bug ID: 246
    #
    # Date: 2010-01-16 19:15:00 +0000
    # From: Oscar González <ogonzalez@igalia.com>
    # To: Javier Morán <jmoran@igalia.com>
    # Version: navalplan-1.1 (1.1.x)
    # CC: iluvsap@gmail.com
    #
    # Last updated: 2012-09-10 05:56:17 +0000
    body=""

    # ret["body"].append("# Bugzilla Bug ID: %d" % ret["number"])
    # also build link to original issue like: http://bugs.libreplan.org/show_bug.cgi?id=1295
    body+="(Original Bugzilla Bug ID: [" + str(bug["bug_id"])+"]("+BUGZILLA_URL+"show_bug.cgi?id="+str(bug["bug_id"])+"))\n\n"

    # ret["body"].append("Date: " + ret["created_at"])
    body+="Date: " + str(bug["creation_ts"])+"\n"

    # ret["body"].append("From: " + ret["user.login"])
    reporterstr=get_reporter(reporters,bug["reporter"])
    body+="From: " + reporterstr+"\n"

    # ret["body"].append("To:   " + ", ".join(ret["assignees"]))
    if bug["assigned_to"] is not None:
        reporterstr = get_reporter(reporters, bug["assigned_to"])
        body += "To: " + reporterstr+"\n"

    # ret["body"].append("Version: " + ret["version"])
    body+="Version: " + str(bug["version"])+"\n"

    # [I'm an inline-style link](https://www.google.com)
    body+="\n---\n"
    body+="(Note: this issue was migrated automatically with [bugzilla2github.py tool](https://github.com/LibrePlan/bugzilla2github) )\n"


    # if "cc" in bug:
    #     ret["body"].append("CC:   " + ", ".join(emails_convert(bug.pop("cc"))))
    # TODO: chose not to support this. Use Link to original issue to find info
    # # Extra information
    # ret["body"].append("")
    # if "dup_id" in bug:
    #     ret["body"].append("Duplicates:   " + ids_convert(bug.pop("dup_id")))
    # TODO: chose not to support this. Use Link to original issue to find info
    # if "dependson" in bug:
    #     ret["body"].append("Depends on:   " + ids_convert(bug.pop("dependson")))
    # TODO: chose not to support this. Use Link to original issue to find info
    # if "blocked" in bug:
    #     ret["body"].append("Blocker for:  " + ids_convert(bug.pop("blocked")))
    # TODO: chose not to support this. Use Link to original issue to find info
    # if "see_also" in bug:
    #     ret["body"].append("See also:     " + bug.pop("see_also"))
    # TODO: chose not to support this. Use Link to original issue to find info
    # ret["body"].append("Last updated: " + ret["updated_at"])
    # ret["body"].append("")
    return body

# Start connection to database
try:
    conn = psycopg2.connect(host=HOST, database=DATABASE, user=USER, password=PASSWORD)
except:
    print "I am unable to connect to the database."
    sys.exit(1)

# read all bug reporters
reporters,colnames=get_reporters(conn)
# read all bug reports
bugs,colnames=read_bugs(conn)
#pprint(bugs)
#pprint(colnames)
issue={}
for bug in bugs:
    bug_id=bug['bug_id']
    for field in colnames:
       print str(field) + " -> " + str(bug[str(field)])
    print "bug_id",bug_id
    #print "bug_severity",bug['bug_severity']
    #print "bug_status", bug['bug_status']
    #print "short_desc", bug['short_desc']
    #print "priority",bug['priority']
    #print "version",bug['version']
    #print "resolution",bug['resolution']

    body=create_body(reporters,bug)

    # Create issues object to send to GitHub
    # And an issue with a comment only needs the comment body added:
    #
    # {
    #   "issue": {
    #     "title": "Imported from some other system",
    #     "body": "..."
    #   },
    #   "comments": [
    #     {
    #       "body": "talk talk"
    #     }
    #   ]
    # }

    issue={"issue":   {"title":bug['short_desc'],
                       "body":body}}

    issuecomments=[]
    pprint(issuecomments)
    comments,colnames=read_comments(conn,bug_id)
    pprint(colnames)
    for comment in comments:
        # ['comment_id', 'bug_id', 'who', 'bug_when', 'work_time', 'thetext', 'isprivate', 'already_wrapped', 'type', 'extra_data']
        comment_id=comment["comment_id"]
        attach_id=comment["extra_data"]
        issuecomment=""
        # pprint(comment)
        print " comment_id", comment["comment_id"]
        print " text:", comment["thetext"]

        # ret.append("## Bugzilla Comment ID: " + comment.pop("commentid"))
        issuecomment += "Bugzilla Comment ID: " + str(comment["comment_id"]) + "\n"
        # ret.append("Date: " + comment.pop("bug_when"))
        issuecomment += "Date: " + str(comment["bug_when"]) + "\n"
        # ret.append("From: " + email_convert(comment.pop("who"),
        issuecomment += "From: " + get_reporter(reporters, comment["who"]) + "\n"
        #                     comment.pop("who.name", None)))
        # ret.append("")
        # ret.append(comment.pop("thetext", ""))
        issuecomment += comment["thetext"] + "\n\n"


        if attach_id is not None:
            print " attach_id",attach_id
            # check attachment record for this comment
            attachment,colnames=read_attachment(conn,attach_id)
            #for activity in activities:
            #pprint(colnames)
            # 'attach_id', 'bug_id', 'creation_ts', 'modification_time', 'description', 'mimetype', 'ispatch', 'filename',
            #  'submitter_id', 'isobsolete', 'isprivate', 'isurl']
            #pprint(attachment)
            #attachment=attachment.pop
            filename=attachment["filename"]
            #filesize=attachment[""]
            print " We have an attachment:",filename
            result=save_attachment(conn,attach_id,bug_id,comment_id,filename)
            # ret.append("> Attached file: %s (%s, %s bytes)" % (attach.pop("filename"),
            #                       attach.pop("type"), attach.pop("size")))
            # ret.append("> Description:   " + attach.pop("desc"))
            # TODO: create link to repo file as: https://github.com/LibrePlan/bugzilla2githubattachments/blob/master/LICENSE
            issuecomment += "\n---\n\nAttached file: [" + filename + "](" + FILEREPO_URL + str(bug_id) + '_' +  str(comment_id) + "_" + filename + ")\n"
            issuecomment += "Description: " + attachment["description"] + "\n---\n"

        # add stuff to issuecomments list
        issuedict = dict()
        issuedict["body"] = issuecomment
        issuecomments.append(issuedict)


    #issue["issue"].append(issuecomments)
    #commentsdict={ "comments", issuecomments }
    #commentsdict=dict()
    #commentsdict.setdefault("comments", issuecomments)
    issue["comments"]=issuecomments
    # What have we created?
    pprint(issue)

    # Now let's try to add this issue to a github repo
    # https://api.github.com/repos/${GITHUB_USERNAME}/foo/import/issues
    urlparts=(str(GITHUB_URL),"repos" ,str(GITHUB_OWNER) , str(GITHUB_REPO) , "import/issues")
    url="/".join(urlparts)
    # if url[0] == "/":
    #     u = "%s%s" % (GITHUB_URL, url)
    # else:
    #     u = "%s/repos/%s/%s/%s" % (GITHUB_URL, GITHUB_OWNER, GITHUB_REPO, url)
    pprint(url)
    d=issue
    #sys.exit(4)
    #result = requests.post(u, params={"access_token": GITHUB_TOKEN,
    headers={"Authorization": "token "+ GITHUB_TOKEN,
             "Accept": "application/vnd.github.golden-comet-preview+json" }
    result=requests.post(url, headers=headers, data = json.dumps(d))

    pprint(result)
    print result.json()
# The end of handling all bugs

# close the communication with the PostgresQL database
if conn is not None:
    conn.close()
