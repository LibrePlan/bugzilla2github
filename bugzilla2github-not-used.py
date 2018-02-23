#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Bugzilla XML File to GitHub Issues Converter by Andriy Berestovskyy
# https://github.com/semihalf-berestovskyy-andriy/tools/blob/master/bugzilla2github
#
# Adapted to LibrePlan project by J. Baten d.d. februari 2018
# - Changed to use new GitHub Api
# - Solve file problem by linking to separate repository
#
# How to use the script:
# 1. Generate a GitHub access token:
#    - on GitHub select "Settings"
#    - select "Personal access tokens"
#    - click "Generate new token"
#    - type a token description, i.e. "bugzilla2github"
#    - select "public_repo" to access just public repositories
#    - save the generated token into the migration script
# 2. Export Bugzilla issues into an XML file:
#    - in Bugzilla select "Search"
#    - select all statuses
#    - at the very end click an XML icon
#    - save the XML into a file
# 3. Run the migration script and check all the warnings:
#    bugzilla2github -x bugzilla.xml -o berestovskyy -r test -t beefbeefbeef
# 4. Run the migration script again and force the updates:
#    bugzilla2github -x bugzilla.xml -o berestovskyy -r test -t beefbeefbeef -f
#

import json, getopt, os, pprint, re, requests, sys, time, xml.etree.ElementTree
from pprint import pprint,pformat

reload(sys)
sys.setdefaultencoding('utf-8')

# force_update = True
xml_file = "show_bug_tiny.cgi.xml"
github_url = "https://api.github.com"
github_owner = "kwoot"
github_repo = "bz2gh"
github_token = "eca81797f8574028556102d22f9b9517247e011c"

email2login = {
    "__name__": "email to GitHub login",
    "123@example.com": "login",
}
status2state = {
    "__name__": "status to GitHub state",
    "CONFIRMED": "open",
    "IN_PROGRESS": "open",
    "RESOLVED": "closed",
}
component2labels = {
    "__name__": "component to GitHub labels",
    "Administration / Management": ["Administration / Management"],
    "Community tools": ["Community tools"],
    "Other": ["Other"],
    "Reports": ["Reports"],
    "Resources": ["Resources"],
    "Scheduling": ["Scheduling"],
    "Web services": ["Web services"],
}

# default github labels:
#
# bug
# duplicate
# enhancement
# good first issue
# help wanted
# invalid
# question
# wontfix

priority2labels = {
    "__name__": "priority to GitHub labels",
    "P1": ["low priority"],
    "P2": ["low priority"],
    "P3": [],
    "P4": [],
    "P5": ["high priority"],
}

# <bug_severity>blocker</bug_severity>
# <bug_severity>critical</bug_severity>
# <bug_severity>enhancement</bug_severity>
# <bug_severity>major</bug_severity>
# <bug_severity>minor</bug_severity>
# <bug_severity>normal</bug_severity>
# <bug_severity>trivial</bug_severity>

severity2labels = {
    "__name__": "severity to GitHub labels",
    "enhancement": ["enhancement"],
    "trivial": ["minor", "bug"],
    "minor": ["minor", "bug"],
    "normal": ["bug"],
    "major": ["major", "bug"],
    "critical": ["major", "bug"],
    "blocker": ["major", "bug"],
}

# <resolution/>
# <resolution>DUPLICATE</resolution>
# <resolution>FIXED</resolution>
# <resolution>INVALID</resolution>
# <resolution>MOVED</resolution>
# <resolution>WONTFIX</resolution>
# <resolution>WORKSFORME</resolution>

resolution2labels = {
    "__name__": "resolution to GitHub labels",
    "FIXED": [],
    "INVALID": ["invalid"],
    "DUPLICATE": ["duplicate"],
}
bug_unused_fields = [
    "actual_time",
    "attachment.isobsolete",
    "attachment.ispatch",
    "attachment.isprivate",
    "cclist_accessible",
    "classification",
    "classification_id",
    "comment_sort_order",
    "estimated_time",
    "everconfirmed",
    "long_desc.isprivate",
    "op_sys",
    "product",
    "remaining_time",
    "reporter_accessible",
    "rep_platform",
    "target_milestone",
    "token",
    # "version",
]
comment_unused_fields = [
    "comment_count",
]
attachment_unused_fields = [
    "attacher",
    "attacher.name",
    "date",
    "delta_ts",
    "token",
]

def usage():
    print "Bugzilla XML file to GitHub Issues Converter"
    print "Usage: %s [-h] [-f]\n" \
        "\t[-x <src XML file>]\n" \
        "\t[-o <dst GitHub owner>] [-r <dst repo>] [-t <dst access token>]\n" \
            % os.path.basename(__file__)
    print "Example:"
    print "\t%s -h" % os.path.basename(__file__)
    print "\t%s -x bugzilla.xml -o dst_login -r dst_repo -t dst_token" \
            % os.path.basename(__file__)
    exit(1)


def XML2dict(parent):
    ret = {}

    for key in parent:
        # TODO: debug
        # print len(key), key.tag, key.attrib, key.text
        if len(key) > 0:
            val = XML2dict(key)
        else:
            val = key.text
        if key.text:
            if key.tag not in ret:
                ret[key.tag] = val
            else:
                if isinstance(ret[key.tag], list):
                    ret[key.tag].append(val)
                else:
                    ret[key.tag] = [ret[key.tag], val]
        # Parse attributes
        for name, val in key.items():
            ret["%s.%s" % (key.tag, name)] = val

    return ret


def str2list(map, str):
    if str not in map:
        print "WARNING: unable to convert %s: %s" % (map["__name__"], str)
        # Suppress further reports
        map[str] = []

    return map[str]


def str2str(map, str):
    if str not in map:
        print "WARNING: unable to convert %s: %s" % (map["__name__"], str)
        # Suppress further reports
        map[str] = None

    return map[str]


def ids_convert(ids):
    ret = []

    if not ids:
        return ""
    if isinstance(ids, list):
        for id in ids:
            ret.append("#" + id)
    else:
        ret.append("#" + ids)

    return ", ".join(ret)


def email_convert(email, name):
    ret = str2str(email2login, email)
    if ret:
        return "@" + ret
    else:
        if name and not name.find("@") >= 0:
            return "%s &lt;<%s>&gt;" % (name, email)
        else:
            return email


def emails_convert(emails):
    ret = []
    if isinstance(emails, list):
        for email in emails:
            ret.append(email_convert(email, None))
    else:
        ret.append(email_convert(emails, None))

    return ret


def fields_ignore(obj, fields):
    # Ignore some Bugzilla fields
    for field in fields:
        obj.pop(field, None)


def fields_dump(obj):
    # Make sure we have converted all the fields
    for key, val in obj.items():
        print " " * 8 + "%s[%d] = %s" % (key, len(val), val)


def attachment_convert(idx, attach):
    ret = []

    id = attach.pop("attachid")
    ret.append("> Attached file: %s (%s, %s bytes)" % (attach.pop("filename"),
                                        attach.pop("type"), attach.pop("size")))
    ret.append("> Description:   " + attach.pop("desc"))

    # Ignore some fields
    global attachment_unused_fields
    fields_ignore(attach, attachment_unused_fields)
    # Make sure we have converted all the fields
    if attach:
        print "WARNING: unconverted attachment fields:"
        fields_dump(attach)

    idx[id] = "\n".join(ret)


def attachments_convert(attachments):
    ret = {}
    if isinstance(attachments, list):
        for attachment in attachments:
            attachment_convert(ret, attachment)
    else:
        attachment_convert(ret, attachments)

    return ret


def comment_convert(comment, attachments):
    ret = []

    ret.append("## Bugzilla Comment ID: " + comment.pop("commentid"))
    ret.append("Date: " + comment.pop("bug_when"))
    ret.append("From: " + email_convert(comment.pop("who"),
                        comment.pop("who.name", None)))
    ret.append("")
    ret.append(comment.pop("thetext", ""))
    ret.append("")
    # Convert attachments if any
    if "attachid" in comment:
        ret.append(attachments.pop(comment.pop("attachid")))
        ret.append("")
    ret.append("")

    # Syntax: convert "bug id" to "bug #id"
    for i, val in enumerate(ret):
        ret[i] = re.sub(r"(?i)(bug)\s+([0-9]+)", r"\1 #\2", val)

    # Ignore some comment fields
    global comment_unused_fields
    fields_ignore(comment, comment_unused_fields)
    # Make sure we have converted all the fields
    if comment:
        print "WARNING: unconverted comment fields:"
        fields_dump(comment)

    return "\n".join(ret)


def comments_convert(comments, attachments):
    ret = []
    if isinstance(comments, list):
        for comment in comments:
            ret.append(comment_convert(comment, attachments))
    else:
        ret.append(comment_convert(comments, attachments))

    return ret


def bug_convert(bug):
    ret = {}
    ret["body"] = []
    # ret["body"].append("Note: the issue was created automatically with %s tool"
    #                     % os.path.basename(__file__))
    ret["body"].append("")
    ret["labels"] = []
    ret["assignees"] = []
    ret["comments"] = []
    attachments = {}

    # Convert bug_id to number
    ret["number"] = int(bug.pop("bug_id"))
    # Convert attachments if any
    if "attachment" in bug:
        attachments = attachments_convert(bug.pop("attachment"))
    # Convert long_desc and attachment to comments
    ret["comments"].extend(comments_convert(bug.pop("long_desc"), attachments))
    # Convert short_desc to title
    ret["title"] = bug.pop("short_desc")
    # Convert creation_ts to created_at
    ret["created_at"] = bug.pop("creation_ts")
    # Convert version to version
    ret["version"] = bug.pop("version")
    # Convert delta_ts to updated_at
    ret["updated_at"] = bug.pop("delta_ts")
    # Convert reporter to user login
    ret["user.login"] = email_convert(bug.pop("reporter"),
                        bug.pop("reporter.name", None))
    # Convert assigned_to to assignees
    ret["assignees"].append(email_convert(bug.pop("assigned_to"),
                        bug.pop("assigned_to.name", None)))
    # Convert component to labels
    ret["labels"].extend(str2list(component2labels, bug.pop("component")))
    # Convert bug_status to state
    ret["state"] = str2str(status2state, bug.pop("bug_status"))
    # Convert priority to labels
    ret["labels"].extend(str2list(priority2labels, bug.pop("priority")))
    # Convert severity to labels
    ret["labels"].extend(str2list(severity2labels, bug.pop("bug_severity")))
    # Convert resolution to labels
    if "resolution" in bug:
        ret["labels"].extend(str2list(resolution2labels, bug.pop("resolution")))

    # Create the bug description
    ret["body"].append("# Bugzilla Bug ID: %d" % ret["number"])
    ret["body"].append("Date: " + ret["created_at"])
    ret["body"].append("From: " + ret["user.login"])
    ret["body"].append("To:   " + ", ".join(ret["assignees"]))
    ret["body"].append("Version: " + ret["version"])
    if "cc" in bug:
        ret["body"].append("CC:   " + ", ".join(emails_convert(bug.pop("cc"))))
    # Extra information
    ret["body"].append("")
    if "dup_id" in bug:
        ret["body"].append("Duplicates:   " + ids_convert(bug.pop("dup_id")))
    if "dependson" in bug:
        ret["body"].append("Depends on:   " + ids_convert(bug.pop("dependson")))
    if "blocked" in bug:
        ret["body"].append("Blocker for:  " + ids_convert(bug.pop("blocked")))
    if "see_also" in bug:
        ret["body"].append("See also:     " + bug.pop("see_also"))
    ret["body"].append("Last updated: " + ret["updated_at"])
    ret["body"].append("")

    # Put everything togather
    ret["body"] = "\n".join(ret["body"]) + "\n\n" + "\n".join(ret["comments"])
    ret["assignees"] = [a[1:] for a in ret["assignees"] if a[0] == "@"]

    # Ignore some bug fields
    global bug_unused_fields
    fields_ignore(bug, bug_unused_fields)
    # Make sure we have converted all the fields
    if bug:
        print "WARNING: unconverted bug fields:"
        fields_dump(bug)
    # Make sure we have converted all the attachments
    if attachments:
        print "WARNING: unconverted attachments:"
        fields_dump(attachments)

    return ret


def bugs_convert(xml_root):
    issues = {}
    for xml_bug in xml_root.iter("bug"):
        bug = XML2dict(xml_bug)
        issue = bug_convert(bug)
        # Check for duplicates
        #id = issue["number"]
        id=len(issues)+1
        if id in issues:
            print("Error checking for duplicates: bug #%d is duplicated in the '%s'"
                            % (id, xml_file))
        issue["myid"]=id
        issues[id] = issue
    pprint(issues)
    return issues


def github_get(url, avs = {}):
    global xml_file, github_url, github_owner, github_repo, github_token

    if url[0] == "/":
        u = "%s%s" % (github_url, url)
    elif url.startswith("https://"):
        u = url
    elif url.startswith("http://"):
        u = url
    else:
        u = "%s/repos/%s/%s/%s" % (github_url, github_owner, github_repo, url)

    # TODO: debug
    # print "GET: " + u

    avs["access_token"] = github_token
    return requests.get(u, params = avs)


def github_post(url, avs = {}, fields = []):
    # global force_update
    global xml_file, github_url, github_owner, github_repo, github_token

    if url[0] == "/":
        u = "%s%s" % (github_url, url)
    else:
        u = "%s/repos/%s/%s/%s" % (github_url, github_owner, github_repo, url)

    d = {}
    # Copy fields into the data
    for field in fields:
        if field not in avs:
            print "Error posting field %s to %s" % (field, url)
            exit(1)
        d[field] = avs[field]

    # TODO: debug
    # print "POST: " + pformat(u)
    # print "DATA: " + pformat(json.dumps(d))

    # if force_update:
    result=requests.post(u, params = { "access_token": github_token },
                            data = json.dumps(d))
    return result
    # else:
    # if not github_post.warn:
    #     print "Skipping POST... (use -f to force updates)"
    #     github_post.warn = True
    # return True
    # github_post.warn = False


def github_label_create(label):
    if not github_get("labels/" + label):
        print "\tcreating label '%s' on GitHub..." % label
        r = github_post("labels", {
            "name": label,
            "color": "0"*6,
        }, ["name", "color"])
        if not r:
            print "Error creating label %s: %s" % (label, r.headers)
            exit(1)


def github_labels_check(issues):
    global force_update

    labels_set = set()
    for id in issues:
        for label in issues[id]["labels"]:
            labels_set.add(label)

    for label in labels_set:
        if github_get("labels/" + label):
            print "\tlabel '%s' exists on GitHub" % label
        else:
            if force_update:
                github_label_create(label)
            else:
                print "WARNING: label '%s' does not exist on GitHub" % label


# def github_assignees_check(issues):
#     a_set = set()
#     for id in issues:
#         for assignee in issues[id]["assignees"]:
#             a_set.add(assignee)
#
#     for assignee in a_set:
#         if not github_get("/users/" + assignee):
#             print "Error checking user '%s' on GitHub" % assignee
#             exit(1)
#         else:
#             print "Assignee '%s' exists" % assignee


def github_issue_exist(number):
    if github_get("issues/%d" % number):
        return True
    else:
        return False


def github_issue_get(number):
    req = github_get("issues/%d" % number)
    if not req:
        print "Error getting GitHub issue #%d: %s" % (number, req.headers)
        exit(1)

    return req.json()


def github_issue_update(issue):
    #id = issue["number"]
    id = issue["myid"]

    print "\tupdating issue #%d on GitHub..." % id
    r = github_post("issues/%d" % id, issue,
            ["title", "body", "state", "labels", "assignees"])
    if not r:
        print "Error updating issue #%d on GitHub:\n%s" % (id, r.headers)
        exit(1)


def github_issue_append(issue):
    print "\tappending a new issue on GitHub..."
    r = github_post("issues", issue, ["title", "body", "labels", "assignees"])
    if not r:
        print "Error appending an issue on GitHub:\n%s" % r.headers
        exit(1)
    return r


def renumbering_comment_create(orig_id, new_id):
    body = []
    body.append("Note: the comment was created automatically with %s tool" \
                    % os.path.basename(__file__))
    body.append("")
    body.append("---")
    body.append("**Bugzilla bug ID:  %d**" % orig_id)
    body.append("**Renumbered to issue: #%d**" % new_id)
    comment = {
        "body": "\n".join(body)
    }
    return comment

def github_comment_add(issue):
    orig_id = issue["orig_number"]
    #new_id = issue["number"]
    new_id = issue["myid"]
    print "\tadding a comment to original issue #%d on GitHub..." % orig_id
    comment = renumbering_comment_create(orig_id, new_id)
    r = github_post("issues/%d/comments" % orig_id, comment, ["body"])
    if not r:
        print "Error adding new comment to issue #%d on GitHub:\n%s" \
                % (orig_id, r.headers)
        exit(1)


def github_comment_update(issue):
    orig_id = issue["orig_number"]
    #new_id = issue["number"]
    new_id = issue["myid"]
    print "\tupdating comment to original issue #%d on GitHub..." % orig_id
    r = github_get("issues/%d/comments" % orig_id)
    if r:
        comments = r.json()
        for comment in comments:
            if not re.search(os.path.basename(__file__), comment["body"]):
                continue
            if not re.search(r"(?ims).*#([0-9]+).*", comment["body"]):
                continue
            bugzilla_id = re.sub(r"(?ims).*#([0-9]+).*", r"\1",
                            comment["body"])
            if not bugzilla_id:
                continue
            bugzilla_id = int(bugzilla_id)
            if bugzilla_id != new_id:
                continue
            comment_id = comment["id"]
            print "\tupdating comment %d on GitHub..." % comment_id
            comment = renumbering_comment_create(orig_id, new_id)
            r = github_post("issues/comments/%d" % comment_id, comment, ["body"])
            if not r:
                print "Error updating comment %d to issue #%d on GitHub:\n%s" \
                        % (comment_id, orig_id, r.headers)
                exit(1)
            return
    print "\tcomment not found, adding a new one..."
    github_comment_add(issue)


def github_issues_add(issues):
    postponed = {}
    nb_postponed = 0
    # pprint(len(issues))
    # pprint(issues)
    # for i in xrange(len(issues)):
    #     id = i + 1
    #     issue = issues[id]
    for id in issues:
        issue=issues.get(id)
        pprint(issue)
        #id=issue{id}
        github_issue = github_get("issues/%d" % id)
        if github_issue:
            # Check if the issue was imported from the Bugzilla
            github_issue = github_issue.json()
            if ("bugzilla bug id: %d\n" % id).lower() in github_issue["body"].lower():
                print "Issue #%d already imported, updating..." % id
                github_issue_update(issue)
            else:
                # print "Issue #%d already exists, postponing..." % id
                print "Issue #%d already exists..." % id
                postponed[id] = issue
                nb_postponed += 1
        else:
            print "Creating issue #%d..." % id
            # Make sure the previous issue already exist
            # if force_update and id > 1 and not github_issue_exist(id - 1):
            #    print "Error adding issue #%d on GitHub: previous issue does not exists" \
            #            % id
            #    exit(1)
            req = github_issue_append(issue)

            new_issue = github_get(req.headers["location"]).json()
            if new_issue["number"] != id:
                print "Error adding issue #%d: assigned unexpected issue id #%d" \
                    % (id, new_issue["number"])
                exit(1)
            # Update issue state
            if issue["state"] != "open":
                github_issue_update(issue)
    print "Done adding with %d issues postponed." % nb_postponed

    return postponed


def issue_renumber(orig_issue, new_id):
    orig_issue["orig_number"] = orig_issue["number"]
    orig_issue["number"] = new_id


# def github_postponed_issues_add(issues, postponed):
#     id = len(issues)
#     # First check existing GitHub issues
#     while True:
#         id += 1
#         print "Checking issue #%d on GitHub..." % id
#         if not github_issue_exist(id):
#             print "\tissue #%d does not exist, breaking..." % id
#             break
#         issue = github_issue_get(id)
#         if not re.search(os.path.basename(__file__), issue["body"]) \
#             or not re.search(r"(?ims).*Bugzilla Bug ID: ([0-9]+).*", issue["body"]):
#             print "\tissue #%d is not from the Bugzilla, skipping..." % id
#         else:
#             bugzilla_id = re.sub(r"(?ims).*Bugzilla Bug ID: ([0-9]+).*", r"\1", issue["body"])
#             if bugzilla_id:
#                 bugzilla_id = int(bugzilla_id)
#                 print "\tissue #%d was imported from Bugzilla (bug %d), updating..." % (id, bugzilla_id)
#                 if bugzilla_id not in postponed:
#                     print "Error adding postponed issue: Bugzilla bug %d is not postponed" % bugzilla_id
#                     exit(1)
#                 bugzilla_issue = postponed.pop(bugzilla_id)
#                 issue_renumber(bugzilla_issue, id)
#                 github_issue_update(bugzilla_issue)
#                 github_comment_update(bugzilla_issue)
#             else:
#                 print "\tissue #%d is not from the Bugzilla, skipping..." % id
#
#     # Now check the postponed issues and append them to the end of the issues
#     for i in xrange(len(issues)):
#         id = i + 1
#         if id not in postponed:
#             continue
#         issue = postponed.pop(id)
#         print "Appending postponed issue #%d on GitHub..." % id
#         req = github_issue_append(issue)
#         if force_update:
#             new_issue = github_get(req.headers["location"]).json()
#             issue_renumber(issue, new_issue["number"])
#             # Update issue state
#             if issue["state"] != "open":
#                 github_issue_update(issue)
#             github_comment_add(issue)


def args_parse(argv):
    global force_update
    global xml_file, github_owner, github_repo, github_token

    try:
        opts, args = getopt.getopt(argv,"hfo:r:t:x:")
    except getopt.GetoptError:
        usage()
    for opt, arg in opts:
        if opt == '-h':
            usage()
        elif opt == "-f":
            print "WARNING: the repo will be UPDATED! No backups, no undos!"
            print "Press Ctrl+C within next 5 secons to cancel the update:"
            time.sleep(5)
            force_update = True
        elif opt == "-o":
            github_owner = arg
        elif opt == "-r":
            github_repo = arg
        elif opt == "-t":
            github_token = arg
        elif opt == "-x":
            xml_file = arg

    # Check the arguments
    if (not xml_file or not github_owner or not github_repo or not github_token):
        print("Error parsing arguments: "
                "please specify XML file, GitHub owner, repo and token")
        usage()


def continuous_check(obj):
    for i in xrange(len(obj)):
        id = i + 1
        if id not in obj:
            return id
    return 0


def main(argv):
    global xml_file, github_owner, github_repo

    # Parse command line arguments
    args_parse(argv)
    print "===> Converting Bugzilla reports to GitHub Issues..."
    print "\tSource XML file:    %s" % xml_file
    print "\tDest. GitHub owner: %s" % github_owner
    print "\tDest. GitHub repo:  %s" % github_repo

    xml_tree = xml.etree.ElementTree.parse(xml_file)
    xml_root = xml_tree.getroot()
    issues = bugs_convert(xml_root)

    # print "===> Checking Bugzilla bug IDs are continuous..."
    # id = continuous_check(issues)
    # if id != 0:
    #    print("Error checking continuity: bug #%d is not found in the '%s'"
    #                        % (id, xml_file))
        #exit(1)

    print "===> Checking all the labels exist on GitHub..."
    github_labels_check(issues)
    # print "===> Checking all the assignees exist on GitHub..."
    # github_assignees_check(issues)

    print "===> Adding Bugzilla reports to GitHub..." # preserving IDs..."
    postponed = github_issues_add(issues)
    # print "===> Appending postponed Bugzilla reports on GitHub with new IDs..."
    # github_postponed_issues_add(issues, postponed)
    print "===> All done."


if __name__ == "__main__":
    main(sys.argv[1:])
