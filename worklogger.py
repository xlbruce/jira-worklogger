import re
import json
import sys
from datetime import datetime

import requests

date = datetime.strptime(sys.argv[1], '%Y-%m-%d')

# Settings
administrative_task = 'API_176' # Don't use a hyphen
http_headers = {'Content-Type': 'application/json'}
toggl_user_agent = 'user@company.com'
toggl_api_key = '<api_key>'
toggl_workspace_id = '<workspace_id>'
toggl_base_url = 'https://toggl.com/reports/api/v2/details'
toggl_params = {
        'user_agent': '%s' % toggl_user_agent,
        'workspace_id': '%s' % toggl_workspace_id,
        'since': '%s' % str(date),
        'until': '%s' % str(date)
        }
toggle_credentials = (toggl_api_key, 'api_token')
jira_credentials = ('user@company.com', 'mypass')
jira_url_template = 'https://mycompany.com/rest/api/2/issue/%s/worklog'


def convert_to_jira_date(date):
    return date[:-6] + '.000-0300'


def create_jira_worklog(timespent, started, comment = ""):
    return {
        'timeSpentSeconds': '%d' % timespent,
        'started': '%s' % convert_to_jira_date(started),
        'comment': '%s' % comment
    }


r = requests.get(toggl_base_url, params=toggl_params, auth=toggle_credentials)
toggl_data = r.json()['data']

# Creating keys to group values
toggl_tasks = {}
for data in toggl_data:
    toggl_tasks[data['description']] = []

# Grouping tasks by description
map(lambda data: toggl_tasks[data['description']].append(data), toggl_data)

jira_worklogs = {}
for key, tasks in toggl_tasks.iteritems():
    totalDuration = 0
    for task in tasks:
       totalDuration += task['dur']

    m = re.search(r"^(API-\d{3,})", key)
    jira_key = administrative_task
    comment = key
    if not m == None:
        comment = ""
        jira_key = m.group(0)
        jira_key = jira_key.replace('-', '_')

    jira_worklogs.setdefault(jira_key, [])
    jira_worklogs[jira_key].append(create_jira_worklog(totalDuration // 1000, tasks[0]['start'], comment))


# Show a summary before do post
print "Tasks to be logged"
for key, worklogs in jira_worklogs.iteritems():
    print "Key: %s -> %s " % (key.replace('_', '-'), worklogs)

post = raw_input("Continue? (y/n)")
post = post.lower()

if not post == 'y':
    print "Aborting..."
    sys.exit(0)

for key, worklogs in jira_worklogs.iteritems():
    real_key = key.replace('_', '-')
    jira_url = jira_url_template % real_key

    for worklog in worklogs:
        try:
            r = requests.post(jira_url, headers=http_headers, data=json.dumps(worklog), auth=jira_credentials)
            if r.status_code == 201:
                print "Posted [%s: %s]" % (real_key, worklog['comment'])
            else:
                print "Response from server: [%s]" % r.content
        except requests.exceptions.RequestException as e:
            print "Error on posting [%s]" % worklog['comment']
