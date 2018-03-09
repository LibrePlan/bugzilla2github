#!/usr/bin/env python
# -*- coding: utf-8 -*
#
# Program to Add Issues to Project
# - retrieve project info, column id's
# - retrieve all issues
# - check if issue already in project
# - else add issue to project column todo
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
import ConfigParser
from pprint import pprint,pformat
from dateutil.tz import tzlocal

reload(sys)
sys.setdefaultencoding('utf-8')

destination_project_name="Cleanup"
destination_column_name="To do"

# read config file
configFile = "AddIssuesToProject.conf"
config = ConfigParser.RawConfigParser()
try:
    config.read(configFile)
    # Read GitHub vars
    GITHUB_TOKEN = config.get('settings', 'github_token')
    GITHUB_URL = config.get('settings', 'github_url')
    GITHUB_OWNER = config.get('settings', 'github_owner')
    GITHUB_REPO = config.get('settings', 'github_repo')
    

except:
    print "Error reading configfile '" + configFile + "'."
    print "Program aborted."
    sys.exit(1)

def get_projects_from_github(repo,token):
    # GET /repos/:owner/:repo/projects
    urlparts=(str(GITHUB_URL),"repos" ,str(GITHUB_OWNER) , str(GITHUB_REPO) , "projects")
    url="/".join(urlparts)

    pprint(url)
    #d=issue
    headers={"Authorization": "token "+ GITHUB_TOKEN,
             "Accept": "application/vnd.github.inertia-preview+json" }
    #         "Accept": "application/vnd.github.golden-comet-preview+json" }
    #result=requests.get(url, headers=headers, data = json.dumps(d))
    result=requests.get(url, headers=headers)
    return result

def get_columns_from_github(repo,token,project_id):
    # GET /projects/:project_id/columns
    urlparts=(str(GITHUB_URL), "projects", str(project_id), "columns")
    url="/".join(urlparts)

    pprint(url)
    #d=issue
    headers={"Authorization": "token "+ GITHUB_TOKEN,
             "Accept": "application/vnd.github.inertia-preview+json" }
    #         "Accept": "application/vnd.github.golden-comet-preview+json" }
    #result=requests.get(url, headers=headers, data = json.dumps(d))
    result=requests.get(url, headers=headers)
    return result


def get_open_issues_from_github(repo,token,project_id):
    # GET /repos/:owner/:repo/issues
    urlparts=(str(GITHUB_URL),"repos" ,str(GITHUB_OWNER) , str(GITHUB_REPO) , "issues")
    url="/".join(urlparts)

    pprint(url)

    headers={"Authorization": "token "+ GITHUB_TOKEN,
             "Accept": "application/vnd.github.inertia-preview+json" }
    #         "Accept":  "application/vnd.github.symmetra-preview+json"}
    #result=requests.get(url, headers=headers, data = json.dumps(d))
    result=requests.get(url, headers=headers)
    return result

    

# Find all defined projects
projects=get_projects_from_github(GITHUB_REPO,GITHUB_TOKEN)
#pprint(projects)
if projects.status_code==200:
    #pprint(projects.json())
    for project in projects.json():
        print "Project " + project["name"]+" has id: " + str(project["id"])


    # Find all defined columns
    #my_project_id=1327353
    #print my_project_id
    my_project_id=[ project["id"] for project in projects.json() if project["name"]==destination_project_name ][0]
    print "My project id is " + str(my_project_id)
    #print my_project_id
    
    columns=get_columns_from_github(GITHUB_REPO,GITHUB_TOKEN,my_project_id)
    # pprint(columns)
    # pprint(columns.json())
    if columns.status_code==200:
        for column in columns.json():
            print "Column " + column["name"]+" has id: " + str(column["id"])
        my_column_id=[ column["id"] for column in columns.json() if column["name"]==destination_column_name ][0]
        print "My column id is " + str(my_column_id)

        # Read all issues from GitHub
        issues=get_open_issues_from_github(GITHUB_REPO,GITHUB_TOKEN,my_project_id)
        if issues.status_code==200:
            file = open("testfile.txt","w") 
            file.write(pformat(issues.json())) 
            file.close() 
        

    # The end of handling all issue

print "Done"