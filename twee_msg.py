# -*- coding: utf-8 -*-

import tweepy
import configparser

CONFIG_FILE = '../twee_msg.ini'

# Reading config
config = configparser.ConfigParser()
with open(CONFIG_FILE) as configfile:
    config.read_file(configfile)

auth = tweepy.OAuthHandler(config['APP']['CONSUMER_KEY'],config['APP']['CONSUMER_SECRET'])

# Check if Auth tocken exists
if not config['APP']['AUTH_SECRET'] or not config['APP']['AUTH_TOKEN']:
    try:
        redirect_url = auth.get_authorization_url()
        print redirect_url
    except tweepy.TweepError:
        print 'Error! Failed to get request token.'

    # Example w/o callback (desktop)
    verifier = raw_input('Go to URL above, authorize and enter the code:')

    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        print 'Error! Failed to get access token.'

    config['APP']['AUTH_SECRET'] = auth.access_token_secret
    config['APP']['AUTH_TOKEN'] = auth.access_token
    with open(CONFIG_FILE,'w') as configfile:
        config.write(configfile)
else:
    auth.set_access_token(config['APP']['AUTH_TOKEN'], config['APP']['AUTH_SECRET'])

# Doing main part
api = tweepy.API(auth)

for m in api.direct_messages():
    print m.text

api.send_direct_message(screen_name='andjelx',text='This is Twitter')
