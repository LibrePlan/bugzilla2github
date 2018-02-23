# bugzilla2github
Code to migrate Bugzilla (version 4.0.2) to GitHub issues

# Introduction
For years all bugs have been managed using Bugzilla on bugs.libreplan.org
For several reasons this however is coming to an end.

The succesor is going to be GitHub Issues.

This means all current issues need to be transfered to GitHub Issues.

For this GitHub has a special REST API

# How to go from Bugzilla to GitHub Issues
There are several steps to consider
- How to retrieve from Bugzilla: we chose to use a direct database connection
- How to upload issues to GitHub: we chose to use a special GitHub API
- How to handle assignees: Chosen to reset to empty
- How to handle attachments: Since the GitHub API does not support adding attachments there are several options:
  - It is possible to manually upload attachments to issues. At over 500 attachments this was not a really an option.
  - There is an unmaintained ruby script to upload files to GitHub. Decided not to use it.
  - Since the migration is only done once we can dump all attachments to a subdirectory, upload that to a repo and generate a link to the file in the issue comments. So that is what we will do.
- Yes, we could do fancy "if already exist..."  etc, but this is a one off, so we simply add issues.

# Sources of inspiration
GitHub description of API: https://gist.github.com/jonmagic/5282384165e0f86ef105

Inspired by the work of Andriy Berestovskyy
who wrote Bugzilla XML File to GitHub Issues Converter
https://github.com/semihalf-berestovskyy-andriy/tools/blob/master/bugzilla2github
Elaborate description
https://www.theozimmermann.net/2017/10/bugzilla-to-github


example: http://bugs.libreplan.org/attachment.cgi?id=212
hoort bij ticket 635

moet handmatig geupload naar github.com en attachment toevoegen aan notitie.

