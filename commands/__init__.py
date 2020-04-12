# this file not only handles commands but also various utils
# commands are handled in `main()`
# the other functions coming after `main()` are utils
# TODO: refactor to separate command handling and utils

import argparse
import configparser
import json
import pathlib
import os
import requests

from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import ChatGrant
from twilio.base.exceptions import TwilioRestException


class TwilioClient:
    def __init__(self):
        self.account_sid = os.getenv('ACCOUNT_SID')
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        self.service_sid = os.getenv('SERVICE_SID')
        self.auth_token = os.getenv('AUTH_TOKEN')
        self.client = Client(self.account_sid, self.auth_token)


twilio = TwilioClient()
client = twilio.client
config = configparser.ConfigParser()
config['user'] = {}


def main():
    global twilio
    global client

    # commands
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', dest='user', type=str,
                        help="authenticate user")
    args = parser.parse_args()

    if args.user:
        identity = args.user.strip()
        try:
            # create new user
            user = client.chat.services(twilio.service_sid).users.create(
                identity=identity)
            config['user']['identity'] = identity
            config['user']['sid'] = user.sid

            # save user details in .cchat.cfg
            with open('.cchat.cfg', 'w+') as configfile:
                config.write(configfile)
            print(f"New user created: {identity}")

            # add user to general channel
            try:
                channel = client.chat.services(twilio.service_sid).channels(
                    'general').fetch()
                client.chat.services(twilio.service_sid).channels(
                    channel.sid).members.create(identity=identity)
                print(f"{identity} added to {channel.unique_name}")
            except TwilioRestException as err:
                if err.status == 404:
                    # if !general channel, create it and add the user
                    print("Creating general channel...")
                    channel = client.chat.services(twilio.service_sid) \
                        .channels.create(
                        friendly_name='General Channel',
                        unique_name='general',
                        created_by=identity
                    )
                    print(f"Channel '{channel.unique_name}' created")
                    client.chat.services(twilio.service_sid).channels(
                        channel.sid).members.create(identity=identity)
                    print(f"{identity} added to {channel.unique_name}")
                else:
                    print(err.msg)
        except TwilioRestException as err:
            if err.status == 409:  # user exists
                print(f"Welcome back {identity}")


def get_channels():
    channels_users = []

    # fetch service channels
    channels = client.chat.services(twilio.service_sid).channels.list()
    for channel in channels:
        channels_users.append((
            channel.unique_name,
            channel.unique_name,
        ))

    return channels_users


def send_message(channel, message):
    config.read('.cchat.cfg')
    # creating a message with the client won't trigger a webhook
    # so we'll create via a direct POST request to the api
    url = f"https://chat.twilio.com/v2/Services/{twilio.service_sid}/Channels/" \
          f"{channel}/Messages"
    data = {
        "From": config['user']['identity'],
        "Body": message,
    }
    headers = {
        'X-Twilio-Webhook-Enabled': 'true',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    requests.post(url, data, headers=headers,
                  auth=(twilio.account_sid, twilio.auth_token))


def path():
    return pathlib.Path(__file__).parent.absolute()
