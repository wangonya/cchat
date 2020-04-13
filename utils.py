"""twilio stuff, command handling and other utils"""

import os
import sys

import requests
import configparser

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

config = configparser.ConfigParser()

account_sid = os.getenv('ACCOUNT_SID')
api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET')
service_sid = os.getenv('SERVICE_SID')
auth_token = os.getenv('AUTH_TOKEN')

if not any((account_sid, api_key, api_secret, service_sid, auth_token)):
    print("Error: all required credentials not set. Please check your .env "
          "file")
    sys.exit()

client = Client(account_sid, auth_token)


def get_channels():
    channels_users = []

    # fetch service channels
    channels = client.chat.services(service_sid).channels.list()
    for channel in channels:
        channels_users.append((
            channel.unique_name,
            channel.unique_name,
        ))

    return channels_users


def send_message(channel, message):
    config.read('.cchat.cfg')
    # creating a message with the client won't trigger a webhook
    # so do a direct POST request to the api
    url = f"https://chat.twilio.com/v2/Services/{service_sid}/Channels/" \
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
                  auth=(account_sid, auth_token))


# handle commands

def command_handler(cmd_string):
    help_text = """
    cchat commands
    """
    if cmd_string.startswith('/login'):
        if len(cmd_string.split()) < 2:
            return "Error: USER  argument not provided"
        if len(cmd_string.split()) > 2:
            return "Error: too many arguments supplied for command"
        identity = cmd_string.split()[1].strip()
        return login(identity)
    elif cmd_string.startswith('/cleanup'):
        if len(cmd_string.split()) > 1:
            return "Error: too many arguments supplied for command"
        return cleanup()


def login(identity):
    try:
        # create new user
        user = client.chat.services(service_sid).users.create(
            identity=identity)
        config['user'] = {}
        config['user']['identity'] = identity
        config['user']['sid'] = user.sid

        # save user details in .cchat.cfg
        with open('.cchat.cfg', 'w+') as configfile:
            config.write(configfile)

        # add user to general channel
        try:
            channel = client.chat.services(service_sid).channels(
                'general').fetch()
            client.chat.services(service_sid).channels(
                channel.sid).members.create(identity=identity)
        except TwilioRestException as err:
            if err.status == 404:
                # if !general channel, create it and add the user
                channel = client.chat.services(service_sid).channels.create(
                    friendly_name='General Channel',
                    unique_name='general',
                    created_by=identity
                )
                client.chat.services(service_sid).channels(
                    channel.sid).members.create(identity=identity)
            else:
                return err.msg
        return f"Welcome {identity}. You've been added to #general"

    except TwilioRestException as err:
        if err.status == 409:  # user exists
            return f"Welcome back {identity}"


def cleanup():
    users = client.chat.services(service_sid).users.list()
    for user in users:
        if user.identity != 'admin':
            client.chat.services(service_sid).users(user.sid).delete()
    channel = client.chat.services(service_sid).channels(
        'general').fetch()
    messages = client.chat.services(service_sid) \
        .channels(channel.sid).messages.list()
    for message in messages:
        client.chat.services(service_sid).channels(channel.sid) \
            .messages(message.sid).delete()
    return "cleanup done"
