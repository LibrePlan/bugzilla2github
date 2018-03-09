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

def get_project_cards_from_github(repo,token,column_id):
    # GET /projects/columns/:column_id/cards
    urlparts=(str(GITHUB_URL),"projects" , "columns", str(column_id),"cards")
    url="/".join(urlparts)

    pprint(url)

    headers={"Authorization": "token "+ GITHUB_TOKEN,
             "Accept": "application/vnd.github.inertia-preview+json" }
    #         "Accept":  "application/vnd.github.symmetra-preview+json"}
    #result=requests.get(url, headers=headers, data = json.dumps(d))
    result=requests.get(url, headers=headers)
    return result

def create_project_card(repo,token,my_column_id,my_issue_id):
    # Create a project card
    # POST /projects/columns/:column_id/cards
    # Parameters
    # Name 	Type 	Description
    # note 	string 	The card's note content. Only valid for cards 
    #               without another type of content, so this must be omitted 
    #               if content_id and content_type are specified.
    # content_id 	integer 	The id of the issue to associate with this card.
    # content_type 	string 	Required if you specify a content_id. 
    #               The type of content to associate with this card. 
    #               Can only be "Issue" at this time.
    urlparts=(str(GITHUB_URL),"projects" , "columns", str(my_column_id),"cards")
    url="/".join(urlparts)

    pprint(url)

    headers={"Authorization": "token "+ GITHUB_TOKEN,
             "Accept": "application/vnd.github.inertia-preview+json" }

    card=dict()
    card["content_id"]=my_issue_id
    card["content_type"]="Issue"

    # print "url:     " + url
    # print "headers: " + pformat(headers)
    # print "data:    " + pformat(card)
    # print "payload: " + json.dumps(card)

    # sys.exit(1)
    result=requests.post(url, headers=headers, data = json.dumps(card))
    # pprint(result.json())
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
        print "Retrieving all current issues from GitHub"
        issues=get_open_issues_from_github(GITHUB_REPO,GITHUB_TOKEN,my_project_id)
        if issues.status_code==200:
            file = open("issues.txt","w") 
            file.write(pformat(issues.json())) 
            file.close() 
        
        # Read all project cards from GitHub
        # print "Retrieving all current cards from GitHub"
        # cards=get_project_cards_from_github(GITHUB_REPO,GITHUB_TOKEN,my_column_id)
        # if cards.status_code==200:
        #     file = open("cards.txt","w") 
        #     file.write(pformat(cards.json())) 
        #     file.close() 
        
        # We now have everything to find out what needs to be done.

        # create temporary index for easy of use
        print 80 * "*"
        print "Creating temporary index of existing cards"
        card_index=set()
        for column in columns.json():
            cards=get_project_cards_from_github(GITHUB_REPO,GITHUB_TOKEN,column["id"])
            for card in cards.json():
                #pprint(card)
                if card.get("content_url") is not None:
                    id=card.get("content_url").split("/")[-1]
                    print "Issue with number " + str(id) + " already in cards"
                    card_index.add(id)
        
        #pprint(card_index)

        print "About to start adding " + str(len(issues.json())) + " issues to the project."
        print "Adding cards linked to issues"
        issue_counter=0
        #file = open("AddIssuesToProject.log","a") 
        for issue in issues.json():
            issue_counter+=1
            print "Doing issue: " + str(issue_counter)
            # if issue already in cards do nothing
            if str(issue["number"]) in card_index:
                print "Card for issue " + str(issue["number"]) + " exists"
            else:
                print "Creating card for issue " + str(issue["number"]) + " (\""+ issue["title"]  + "\")"
                # else add card in correct column linking to issue
                # create card in desired project and desired column
                # Note that you have to send the id of the issue, not the number!
                result=create_project_card(GITHUB_REPO,GITHUB_TOKEN,my_column_id,issue["id"])
                # And try this ONLY ONCE!
                #pprint(result)
                pprint(result.json())
                with open("AddIssuesToProject.log", "a") as logfile:
                    logfile.write(pformat(result.json()))
                #file.write(pformat(result.json())) 
                #sys.exit(1)
        
        file.close() 

    # The end of handling all issue

print "Done"