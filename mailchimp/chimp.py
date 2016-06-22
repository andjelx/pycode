#!/usr/bin/env python
from __future__ import print_function, unicode_literals
from mailchimp3 import MailChimp
from config import CHIMP_USER, CHIMP_KEY
import pprint
from collections import defaultdict
import sys

LEAD_FIELD = 'LSTATUS'
STATUSES = [ 'ice cold', 'cold', 'cool', 'tepid', 'lukewarm', 'warm' ]

# Make connection
client = MailChimp(CHIMP_USER, CHIMP_KEY)

# Client statuses
cl_status = {}
cl_ids = {}

def uniq_list(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]

def get_status_id(status):
    # Get status ID from STATUSSES if not found return 0 == ice cold
    return STATUSES.index(status) if status in STATUSES else 0

def if_ignored(status):
    return { 
        status < get_status_id('cool'): get_status_id('ice cold'),
        get_status_id('cool') <= status < get_status_id('warm'): get_status_id('cold'),
         get_status_id('warm') <= status : get_status_id('cool'),

    } [True]


def new_status_id(status, actions):
    cur = get_status_id(status)
    uact = uniq_list(actions)
    # If no actions i.e. Ignored
    if not uact:
        return STATUSES[if_ignored(cur)]

    if 'open' in uact and cur < get_status_id('lukewarm'):
        cur += 1
    if 'click' in uact and cur < get_status_id('warm'):
        cur += 1
    # Prevent getting status higher then max
    if cur > len(STATUSES)-1:
        cur = len(STATUSES)-1
    return STATUSES[cur]

# Main

ti = client.campaign.all()['total_items']
campaigns = client.campaign.all(count=ti)['campaigns']
sc = {} # Sorted campaigns
# Make sorted list of campaigns based on send_time and status == sent
for i,cam in enumerate(sorted(campaigns, key=lambda x: x['send_time'], reverse=True)):
    if cam['status'] == 'sent':
        sc[i] = cam

# Check if argv supplied
if len(sys.argv) >= 2:
    if sys.argv[1].lower() == '--last':
        c = sc[0]
    else:
        print("Suppply --last to the scipt to process last campaign or no parameters")
        quit()
else:
    print("Found %s campaigns" % len(sc))
    print("Select campaign to process:")
    for i, cam in sc.items()[0:10]:
        print("[%s] %s sent on %s" %(i, cam['settings']['title'], cam['send_time']))
    inp = int(raw_input("Provide campaign number: ").strip())
    if inp not in sc.keys():
        print("Prease provide correct campaign")
        quit()
    else:
        c = sc[inp]

# Campaign process part
if c:
    cl_actions = defaultdict(list) # All statuses for current campaign
    c_id = c['id']
    print("\nCampaign: %s [%s] sent on %s" % (c['settings']['title'], c_id, c['send_time']))
    list_id = c['recipients']['list_id']

    # Filling 2 dicts with data about clients
    ti = client.member.all(list_id)['total_items']
    for cl in client.member.all(list_id, count=ti)['members']:
        cl_status[cl['email_address']] = cl['merge_fields'][LEAD_FIELD]
        cl_ids[cl['email_address']] = cl['id']
  
    for a in client.reportactivity.all(c_id)['emails']:
        rcpt = a['email_address']
        status = cl_status[rcpt]
        print("\nRecipient: %s [%s]" % (rcpt, status))
        for act in a['activity']:
            action = act['action']
            cl_actions[rcpt].append(action)
            if action == 'click':
                print("\tClick on: %s at %s" % (act['url'], act['timestamp']))
            else:
                print("\tAction: %s at %s" % (act['action'], act['timestamp']))
        # Check for status change and bring new status
        #print("\tActions found: %s" % cl_actions[rcpt])
        new_status = new_status_id(status, cl_actions[rcpt])
        print("\tNew status: %s" % new_status)
        
        # Updating status on mailchimp
        m = client.member.get(list_id, cl_ids[rcpt]) 
        m['merge_fields'][LEAD_FIELD] = new_status
        client.member.update(list_id, cl_ids[rcpt], m)
        print("\tStatus updated to: %s" % new_status)
