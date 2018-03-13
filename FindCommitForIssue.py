#!/usr/bin/env python
# -*- coding: utf-8 -*
#
# Program to List Issues from a Project
# - retrieve first comment
# - retrieve original Bugzilla ID
# - check if Bugzilla ID is mentioned in a git commit log.
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
# 3. Copy bugzilla2github.conf.sample to FindCommitsForIssue.conf
#    - Well, no, I just used the AddIssuesToProject.conf again.
#    - Change all settings to fit your setup
# 4. Run the script. Good luck....

import json, requests, sys, os
import ConfigParser
from pprint import pprint, pformat
from dateutil.tz import tzlocal
import subprocess

reload(sys)
sys.setdefaultencoding('utf-8')

destination_project_name = "Cleanup"
destination_column_name = "To do"
#destination_column_name = "In progress"
page_size=100
page_size=30 # 30 seems to be the GitHub maximum
my_page=1

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


def get_projects_from_github(repo, token):
    # GET /repos/:owner/:repo/projects
    urlparts = (str(GITHUB_URL), "repos", str(GITHUB_OWNER), str(GITHUB_REPO), "projects")
    url = "/".join(urlparts)

    # pprint(url)
    # d=issue
    headers = {"Authorization": "token " + GITHUB_TOKEN,
               "Accept": "application/vnd.github.inertia-preview+json"}
    #         "Accept": "application/vnd.github.golden-comet-preview+json" }
    # result=requests.get(url, headers=headers, data = json.dumps(d))
    result = requests.get(url, headers=headers)
    return result


def get_columns_from_github(repo, token, project_id):
    # GET /projects/:project_id/columns
    urlparts = (str(GITHUB_URL), "projects", str(project_id), "columns")
    url = "/".join(urlparts)

    #pprint(url)
    # d=issue
    headers = {"Authorization": "token " + GITHUB_TOKEN,
               "Accept": "application/vnd.github.inertia-preview+json"}
    #         "Accept": "application/vnd.github.golden-comet-preview+json" }
    # result=requests.get(url, headers=headers, data = json.dumps(d))
    result = requests.get(url, headers=headers)
    return result


def get_open_issues_from_github(repo, token, project_id, page=1):
    # GET /repos/:owner/:repo/issues
    urlparts = (str(GITHUB_URL), "repos", str(GITHUB_OWNER), str(GITHUB_REPO), "issues")
    url = "/".join(urlparts)
    url += "?per_page="+str(page_size)+"&page=" + str(page)
    #pprint(url)

    headers = {"Authorization": "token " + GITHUB_TOKEN,
               "Accept": "application/vnd.github.inertia-preview+json"}
    #         "Accept":  "application/vnd.github.symmetra-preview+json"}
    # result=requests.get(url, headers=headers, data = json.dumps(d))
    result = requests.get(url, headers=headers)
    return result

def get_issue_from_content_url(issue_url):
    headers = {"Authorization": "token " + GITHUB_TOKEN,
               "Accept": "application/vnd.github.inertia-preview+json"}
    #         "Accept":  "application/vnd.github.symmetra-preview+json"}
    # result=requests.get(url, headers=headers, data = json.dumps(d))
    result = requests.get(issue_url, headers=headers)
    return result

def get_project_cards_from_github(repo, token, column_id,page=1):
    # GET /projects/columns/:column_id/cards
    urlparts = (str(GITHUB_URL), "projects", "columns", str(column_id), "cards")
    url = "/".join(urlparts)
    url += "?per_page="+str(page_size)+"&page=" + str(page)
    #pprint(url)

    headers = {"Authorization": "token " + GITHUB_TOKEN,
               "Accept": "application/vnd.github.inertia-preview+json"}
    #         "Accept":  "application/vnd.github.symmetra-preview+json"}
    # result=requests.get(url, headers=headers, data = json.dumps(d))
    result = requests.get(url, headers=headers)
    return result



print "Start"
print "====="
# Find all defined projects
projects = get_projects_from_github(GITHUB_REPO, GITHUB_TOKEN)
# pprint(projects)
if projects.status_code == 200:
    # pprint(projects.json())
    for project in projects.json():
        print "Project " + project["name"] + " has id: " + str(project["id"])

    # Find all defined columns
    # my_project_id=1327353
    # print my_project_id
    my_project_id = [project["id"] for project in projects.json() if project["name"] == destination_project_name][0]
    print "My project id is " + str(my_project_id)
    # print my_project_id

    columns = get_columns_from_github(GITHUB_REPO, GITHUB_TOKEN, my_project_id)
    # pprint(columns)
    # pprint(columns.json())

    my_column_id = [column["id"] for column in columns.json() if column["name"] == destination_column_name][0]
    print "My column id is " + str(my_column_id)

    cards=get_project_cards_from_github(GITHUB_REPO,GITHUB_TOKEN,my_column_id,my_page)
    #pprint(cards.json())

    for card in cards.json():
        if card.get("content_url") is not None:
            github_issue_url=card.get("content_url")
            #print "card references issue "+issue_url
            github_issue_id=github_issue_url.split("/")[-1]
            #print "GitHub (not Bugzilla!) issue we are looking for is "+str(issue)
            # Now get first message from url and get original Bugzilla id
            github_issue=get_issue_from_content_url(github_issue_url)
            #pprint(issue.json())
            body=github_issue.json().get("body")
            #print body
            bugzillastring=body.split('\n', 1)[0]
            # Let's skip issues originally not form bugzilla
            if "Original Bugzilla Bug ID" in bugzillastring:
                start = bugzillastring.index("[") + 1
                end = bugzillastring.index("]", start)
                bugzilla_id=bugzillastring[start:end]
                #print "Looking for bugzilla ID: " + str(bugzilla_id)
                print ".",

                #print "Is there a commit message referencing issue "+str(bugzilla_id)+"?"
                #print "issue url= https://github.com/LibrePlan/libreplan/issues/"+str(issue)
                #print "issue url= "  + issue_url
                mydir="/home/jeroen/libreplan"
                cmd="git log --all --grep='#"+str(bugzilla_id)+"' "
                #cmd = "git log --all --grep='#" + str(bugzilla_id) + "' | grep '^commit'  "

                #cmd = "git log --all --grep='#" + str(issue) + "'"
                #print cmd
                os.chdir("/home/jeroen/libreplan")
                p=subprocess.Popen(cmd,
                                        cwd=mydir,
                                        stdout=subprocess.PIPE,
                                        shell=True)
                out, err = p.communicate()
                #output=subprocess.check_output([cmd,])
                # if "commit" in output:
                #pprint(out)
                if "commit" in out:
                    print "\n"
                    print "=" * 80
                    outs=out.split("\n")
                    for commitstr in outs:
                        print commitstr
                    print "-" * 80
                    print "issue url= https://github.com/LibrePlan/libreplan/issues/"+str(github_issue_id)
                    #print "issue url= " + github_issue_url
                    cmd = "git log --all --grep='#" + str(bugzilla_id) + "' | grep '^commit'  "
                    #print cmd
                    os.chdir("/home/jeroen/libreplan")
                    p=subprocess.Popen(cmd,
                                            cwd=mydir,
                                            stdout=subprocess.PIPE,
                                            shell=True)
                    out, err = p.communicate()
                    #output=subprocess.check_output([cmd,])
                    # if "commit" in output:
                    #pprint(out)
                    outs=out.split("\n")
                    for commitstr in outs:
                        print commitstr


                #os.system(cmd)
                #sys.exit(1)
            else:
                print "Not an original Bugzilla issue."

    print "\n"


print "Done checking " + str(len(cards.json())) + " cards of page " + str(my_page)+ "."