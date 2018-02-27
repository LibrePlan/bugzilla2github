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
# 4. Please understand there is not API to delete issues. So test thoroughly before the final run!
# 5. Run the script. Good luck....

import json, requests, sys
import psycopg2, psycopg2.extras
import ConfigParser
from pprint import pprint
from dateutil.tz import tzlocal


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
        #cur.execute(""" SELECT * from bugs where bug_id=1284 """,)
        cur.execute(""" SELECT * from bugs order by bug_id  """, )
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

def get_components(conn):
    """
    Retrieve all components from Bugzilla database
    :param conn:  database connection object
    :return: object with all results
    """
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT * FROM components """)
        results = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    # Build indexed dictionary from results
    components={}
    for result in results:
        components[result["id"]]=result
    return components,colnames


def get_component(components,component_id):
    """
    routine to find componentname for componentid
    :param components: dictionary with all components, indexed on componentid
    :param component_id: id of component to find
    :return: string componentname
    """
    # ['userid', 'login_name', 'cryptpassword', 'realname', 'disabledtext', 'disable_mail', 'mybugslink', 'extern_id']
    componentobj=components[component_id]
    componentstr=componentobj["name"]
    return componentstr

def get_duplicates(conn):
    """
        Because we have relative few duplicates (55) compared to the total number of bugs (1709)
        we retrieve all duplicates from Bugzilla database into dictionary of lists for quick lookup
        :param conn:  database connection object
        :return: object with all results (a dictionary of lists)
        """
    duplicates=dict()
    reverse_duplicates=set()
    try:
        # create a new cursor object
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # execute the SELECT statement
        cur.execute(""" SELECT * FROM duplicates """ )
        results = cur.fetchall()

        for result in results:
            if duplicates.get(result["dupe_of"]) is None:
                duplicates[result["dupe_of"]]=list()
            duplicates[result["dupe_of"]].append(result["dupe"])
            reverse_duplicates.add(result["dupe"])

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    return duplicates,reverse_duplicates


def create_body(reporters,duplicates,bug):
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
    #
    # Example record info
    # bug_id -> 1295
    # assigned_to -> 6
    # bug_file_loc ->
    # bug_severity -> critical
    # bug_status -> RESOLVED
    # creation_ts -> 2011-12-14 18:05:08
    # delta_ts -> 2012-01-13 10:31:16
    # short_desc -> TaskSource is null for some TaskElements
    # op_sys -> All
    # priority -> P5
    # product_id -> 2
    # rep_platform -> All
    # reporter -> 6
    # version -> libreplan-1.2 (1.2.x)
    # component_id -> 10
    # resolution -> FIXED
    # target_milestone -> ---
    # qa_contact -> None
    # status_whiteboard ->
    # votes -> 0
    # lastdiffed -> 2012-01-13 10:31:16
    # everconfirmed -> 1
    # reporter_accessible -> 1
    # cclist_accessible -> 1
    # estimated_time -> 0.00
    # remaining_time -> 0.00
    # deadline -> None
    # alias -> None
    # cf_browser -> ---
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

    # if "cc" in bug:
    #     ret["body"].append("CC:   " + ", ".join(emails_convert(bug.pop("cc"))))
    # TODO: chose not to support this. Use Link to original issue to find info

    # # Extra information
    # ret["body"].append("")
    # if "dup_id" in bug:
    #     ret["body"].append("Duplicates:   " + ids_convert(bug.pop("dup_id")))
    if duplicates.get(bug["bug_id"]) is not None:
        for duplicate in duplicates[bug["bug_id"]]:
            body+="Duplicate: [" + str(duplicate) +"]("+BUGZILLA_URL+"show_bug.cgi?id="+str(bug["bug_id"])+"))\n"

    # if "dependson" in bug:
    #     ret["body"].append("Depends on:   " + ids_convert(bug.pop("dependson")))
    # TODO: chose not to support this. Use Link to original issue to find info
    # if "blocked" in bug:
    #     ret["body"].append("Blocker for:  " + ids_convert(bug.pop("blocked")))
    # TODO: chose not to support this. Use Link to original issue to find info
    # if "see_also" in bug:
    #     ret["body"].append("See also:     " + bug.pop("see_also"))

    # ret["body"].append("Last updated: " + ret["updated_at"])
    body+="Last updated: " + str(bug["delta_ts"]) +"\n"
    # ret["body"].append("")
    # [I'm an inline-style link](https://www.google.com)
    body+="\n---\n"
    body+="(Note: this issue was migrated automatically with [bugzilla2github.py tool](https://github.com/LibrePlan/bugzilla2github) )\n"

    return body

# Start connection to database
try:
    conn = psycopg2.connect(host=HOST, database=DATABASE, user=USER, password=PASSWORD)
except:
    print "I am unable to connect to the database."
    sys.exit(1)

# read all bug reporters
reporters,colnames=get_reporters(conn)

# read all components
components,colnames=get_components(conn)

# Create a duplicates lookup dictionary of lists
duplicates,reverse_duplicates=get_duplicates(conn)

# read all bug reports
bugs,colnames=read_bugs(conn)

#pprint(bugs)
#pprint(colnames)
issue={}
for bug in bugs:
    bug_id=bug['bug_id']
    # for field in colnames:
    #    print str(field) + " -> " + str(bug[str(field)])
    print "bug_id",bug_id

    # Check for duplicates
    #duplicates = find_duplicates(conn,bug_id)

    body=create_body(reporters,duplicates,bug)

    # Create issues object to send to GitHub: only title and body are needed.
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

    # Complete info:
    # "title": "Imported from some other system",
    # "body": "...",
    # "created_at": "2014-01-01T12:34:58Z",
    # "closed_at": "2014-01-02T12:24:56Z",
    # "updated_at": "2014-01-03T11:34:53Z",
    # "assignee": "jonmagic",
    # "milestone": 1,
    # "closed": true,
    # "labels": [
    #     "bug",
    #     "low"
    # ]

    if bug["bug_status"]=="RESOLVED":
        closed=True
    else:
        closed=False

    # Let's create some labels
    # NOTE to self: An empty label means issue not added to GitHub!
    labels=[]
    if bug["bug_severity"]:
        labels.append(bug["bug_severity"])
    if bug["priority"]:
        labels.append(bug["priority"])
    if bug["resolution"]:
        labels.append(bug["resolution"].lower())
    bug_component=get_component(components,bug["component_id"])
    if bug_component:
        labels.append(bug_component)
    # If this issue is a duplicate of another issue, then add label "duplicate"
    if bug_id in reverse_duplicates:
        labels.append("duplicate")

    # TODO We currently do not know WHEN an issue was closed, so do not store it in the issue.
    # Well, we could find it through bug_activity table but too much hassle actually.
    # Good news is, that we do close an issue when it is closed
    # "closed_at":str(bug["delta_ts"].replace(tzinfo=tzlocal()).isoformat()),
    issue={"issue":   {"title":bug['short_desc'],
                       "body":body,
                       "created_at": str(bug["creation_ts"].replace(tzinfo=tzlocal()).isoformat()),
                       "closed": closed,
                       "labels": labels,
                       }
           }

    #pprint(issue)

    issuecomments=[]
    pprint(issuecomments)
    comments,colnames=read_comments(conn,bug_id)
    for comment in comments:
        # ['comment_id', 'bug_id', 'who', 'bug_when', 'work_time', 'thetext', 'isprivate', 'already_wrapped', 'type', 'extra_data']
        comment_id=comment["comment_id"]
        attach_id=comment["extra_data"]
        comment_type=comment["type"] # Very important: 5=attachment

        issuecomment=""
        # pprint(comment)
        print " comment_id", comment["comment_id"]
        print " text:", comment["thetext"]

        # ret.append("## Bugzilla Comment ID: " + comment.pop("commentid"))
        issuecomment += "Bugzilla Comment ID: " + str(comment["comment_id"]) + "\n"
        # ret.append("Date: " + comment.pop("bug_when"))
        issuecomment += "Date: " + str(comment["bug_when"]) + "\n"
        # ret.append("From: " + email_convert(comment.pop("who"),
        issuecomment += "From: " + get_reporter(reporters, comment["who"]) + "\n\n"
        #                     comment.pop("who.name", None)))
        # ret.append(comment.pop("thetext", ""))
        issuecomment += comment["thetext"] + "\n\n"


        if comment_type==5 and attach_id is not None:
            print " attach_id",attach_id
            # check attachment record for this comment
            attachment,colnames=read_attachment(conn,attach_id)
            #for activity in activities:
            #pprint(colnames)
            # 'attach_id', 'bug_id', 'creation_ts', 'modification_time', 'description', 'mimetype', 'ispatch', 'filename',
            #  'submitter_id', 'isobsolete', 'isprivate', 'isurl']
            #pprint(attachment)
            filename=attachment["filename"]
            #filesize=attachment[""]
            print " We have an attachment:",filename
            result=save_attachment(conn,attach_id,bug_id,comment_id,filename)
            # ret.append("> Attached file: %s (%s, %s bytes)" % (attach.pop("filename"),
            #                       attach.pop("type"), attach.pop("size")))
            # ret.append("> Description:   " + attach.pop("desc"))
            # TODO: create link to repo file as: https://github.com/LibrePlan/bugzilla2githubattachments/blob/master/LICENSE
            issuecomment += "\n---\nAttached file: [" + filename + "](" + FILEREPO_URL + str(bug_id) + '_' +  str(comment_id) + "_" + filename + ")\n"
            issuecomment += "File description: " + attachment["description"] + "\n"

        # add stuff to issuecomments list
        issuedict = dict()
        issuedict["body"] = issuecomment
        issuecomments.append(issuedict)

    issue["comments"]=issuecomments
    # What have we created?
    print "*" * 40 + " Final issue object " + "*" * 40
    pprint(issue)

    # Now let's try to add this issue to a github repo
    # https://api.github.com/repos/${GITHUB_USERNAME}/foo/import/issues
    urlparts=(str(GITHUB_URL),"repos" ,str(GITHUB_OWNER) , str(GITHUB_REPO) , "import/issues")
    url="/".join(urlparts)

    pprint(url)
    d=issue
    headers={"Authorization": "token "+ GITHUB_TOKEN,
             "Accept": "application/vnd.github.golden-comet-preview+json" }
    result=requests.post(url, headers=headers, data = json.dumps(d))
    # Should be added, but we do need an extra check to find errors.
    print result.status_code
    # Check if something went wrong
    if result.status_code==202:
        print result.json()
        result_dict=result.json()
        # Let's check if it all worked
        result_id=result_dict["id"]
        import_issues_url=result_dict["import_issues_url"]
        print "Result ID = "+str(result_id)
        print "import_issues_url = " + str(result_dict["import_issues_url"])
        # First get ID of issue added
        # Next request result
        # curl -H "Authorization: token ${GITHUB_TOKEN}" \
        #-H "Accept: application/vnd.github.golden-comet-preview+json" \
        #https://api.github.com/repos/#{GITHUB_USERNAME}/foo/import/issues/7
        complete_import_issue_url= import_issues_url + "/" + str(result_id)
        print "Complete import_issues_url = " + str(complete_import_issue_url)

        result2=requests.get(complete_import_issue_url, headers=headers, data = json.dumps(d))
        pprint(result2)
        print result2.json()

        print json.dumps(result2.json(), indent=4, sort_keys=True)
        # Bail out on error, this means when status=failed
        #print result2.json["status"]
        result2_dict=result2.json()
        # Let's check if it all worked
        result2_status=result2_dict["status"]
        print "Final verdict for this issue = " + result2_status
        if result2_status == "failed":
            print "***Bailing out!!!!"
            sys.exit(2)
    else:
        # some error occured so we bail out!
        sys.exit(3)

# The end of handling all bugs

# close the communication with the PostgresQL database
if conn is not None:
    conn.close()
