"""twilio stuff, command handling and other utils"""

import os
import sys
import requests
import configparser

from halo import Halo
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

config = configparser.ConfigParser()
config.read('.user.cfg')

spinner = Halo(spinner="dots", text="checking twilio credentials ... ")

account_sid = os.getenv('ACCOUNT_SID')
api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET')
service_sid = os.getenv('SERVICE_SID')
auth_token = os.getenv('AUTH_TOKEN')

ansi_red = '\033[0;31m'
ansi_bold = '\033[1m'
ansi_italics = '\033[3m'
ansi_end = '\033[0m'

if not any((account_sid, api_key, api_secret, service_sid, auth_token)):
    spinner.fail("One or more Twilio credentials not set. "
                 "Please check your .env file")
    sys.exit()
else:
    spinner.succeed("twilio credentials set")

client = Client(account_sid, auth_token)

spinner.start("checking user credentials ...")
try:
    identity = config['user']['identity']
    spinner.succeed(f"logged in as {identity}")
except (KeyError, TypeError):
    # get current users to check for duplicate username
    identities = client.chat.services(service_sid).users.list()
    # create new user
    spinner.warn("new user")
    identity = input("enter username for registration: ").strip()
    while not identity or identity in [id_.identity for id_ in identities]:
        if not identity:
            spinner.warn("a username is required for registration")
            identity = input("enter username for registration: ").strip()
        elif identity in [id_.identity for id_ in identities]:
            spinner.warn("that username is already taken")
            identity = input(
                "enter a different username for registration: ").strip()
    spinner.start("creating new user ...")
    user = client.chat.services(service_sid).users.create(
        identity=identity, friendly_name=identity)
    config['user'] = {}
    config['user']['identity'] = identity
    config['user']['friendly_name'] = identity
    config['user']['sid'] = user.sid

    # save user details in .user.cfg
    with open('.user.cfg', 'w+') as configfile:
        config.write(configfile)

    spinner.succeed(f"user {ansi_bold}{identity}{ansi_end} created")

    # add user to general channel
    try:
        client.chat.services(service_sid).channels(
            'general').members.create(identity=identity)
        spinner.succeed(f"user added to #general")
    except TwilioRestException as err:
        if err.status == 404:
            # if !general channel, create it and add the user
            client.chat.services(service_sid).channels.create(
                friendly_name='General Chat Channel',
                unique_name='general',
                created_by=identity
            )
            client.chat.services(service_sid).channels(
                'general').members.create(identity=identity)
            spinner.succeed(f"user added to #general")
        else:
            spinner.fail(err.msg)
            sys.exit()


def get_channels():
    """get channels that the logged in user is a member of"""
    channels_list = []

    # fetch service channels
    channels = client.chat.services(service_sid).channels.list()
    for channel in channels:
        channels_list.append((
            channel.unique_name,
            channel.unique_name,
        ))

    return channels_list


def send_message(channel, message):
    # creating a message with the client won't trigger a webhook
    # so do a direct POST request to the api
    url = f"https://chat.twilio.com/v2/Services/{service_sid}/Channels/" \
          f"{channel}/Messages"
    data = {
        "From": identity,
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
    if cmd_string.startswith('/+channel'):
        args = cmd_string.split()
        if len(cmd_string.split()) < 2:
            return "Error: CHANNEL_NAME argument is required"
        elif len(cmd_string.split()) > 2:
            return "Error: too many arguments supplied for command"
        name = args[1]
        return add_channel(name)
    elif cmd_string.startswith('/-channel'):
        args = cmd_string.split()
        if len(cmd_string.split()) < 2:
            return "Error: CHANNEL_NAME argument is required"
        elif len(cmd_string.split()) > 2:
            return "Error: too many arguments supplied for command"
        name = args[1]
        return delete_channel(name)
    elif cmd_string.startswith('/cleanup'):
        if len(cmd_string.split()) > 1:
            return "Error: too many arguments supplied for command"
        return cleanup()
    else:
        return "Error: invalid command"


def add_channel(name):
    try:
        client.chat.services(service_sid).channels.create(
            unique_name=name, created_by=identity)
        client.chat.services(service_sid).channels(name).members.create(
            identity=identity)
        return f"{ansi_italics}{ansi_bold}#{name} created{ansi_end}"
    except TwilioRestException as e:
        return f"{ansi_red}{e.msg}{ansi_end}"


def delete_channel(name):
    try:
        client.chat.services(service_sid).channels(name).delete()
        return f"{ansi_italics}{ansi_bold}#{name} deleted{ansi_end}"
    except TwilioRestException as e:
        return f"{ansi_red}{e.msg}{ansi_end}"


def cleanup():
    users = client.chat.services(service_sid).users.list()
    for u in users:
        if u.identity != 'admin':
            client.chat.services(service_sid).users(u.sid).delete()
    channel = client.chat.services(service_sid).channels(
        'general').fetch()
    messages = client.chat.services(service_sid) \
        .channels(channel.sid).messages.list()
    for message in messages:
        client.chat.services(service_sid).channels(channel.sid) \
            .messages(message.sid).delete()
    return "cleanup done"
