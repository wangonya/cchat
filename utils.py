"""twilio stuff, command handling and other utils"""

import os
import sys
import requests
import configparser

from halo import Halo
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from authy.api import AuthyApiClient

config = configparser.ConfigParser()
config.read('.cchat.cfg')

spinner = Halo(spinner="dots", text="checking twilio credentials ... ")

account_sid = os.getenv('ACCOUNT_SID')
chat_service_sid = os.getenv('CHAT_SERVICE_SID')
sms_service_sid = os.getenv('SMS_SERVICE_SID')
auth_token = os.getenv('AUTH_TOKEN')
authy_key = os.getenv('AUTHY_API_KEY')

ansi_red = '\033[0;31m'
ansi_bold = '\033[1m'
ansi_italics = '\033[3m'
ansi_end = '\033[0m'

if not any((account_sid, sms_service_sid, chat_service_sid, auth_token, authy_key)):
    spinner.fail("One or more Twilio credentials not set. "
                 "Please check your .env file")
    sys.exit()
else:
    spinner.succeed("twilio credentials set")

client = Client(account_sid, auth_token)
authy_api = AuthyApiClient(authy_key)

spinner.start("checking user credentials ...")
try:
    authy_id = config['user']['authy_id']
    authy_token = config['user']['authy_token']
    verification = authy_api.tokens.verify(authy_id, token=auth_token)
    if verification.ok().message == "Token is valid.":
        spinner.succeed("authy verified")
    else:
        spinner.fail("invalid authy token")
        sys.exit()
    identity = config['user']['identity']
    spinner.succeed(f"logged in as {identity}")
except (KeyError, TypeError):
    try:
        # get current users to check for duplicate username
        identities = client.chat.services(chat_service_sid).users.list()
        # create new user
        spinner.warn("new user")

        email = input("enter email: ").strip()
        while not email or not re.match("[^@]+@[^@]+\.[^@]+", email):
            if not email:
                spinner.warn("an email is required for registration")
                email = input("enter email: ").strip()
            elif not re.match("[^@]+@[^@]+\.[^@]+", email):
                spinner.warn("invali email format")
                email = input("enter email: ").strip()

        country_code = input("enter country code: ")
        while not country_code:
            spinner.warn("country code is required for registration")
            country_code = input("enter country code (without +): ")

        phone = input("enter phone number (without country code): ")
        while not phone:
            spinner.warn("phone number is required for registration")
            phone = input("enter phone number (without country code): ")

        user = authy_api.users.create(
                email=email,
                phone=phone,
                country_code=int(country_code))

        if user.ok():
            config['user'] = {}
            config['user']['authy_id'] = user.id
        else:
            spinner.fail("The email, phone or country code you provided were invalid. Please check them and try again.")
            sys.exit()

        #TODO: VERIFY

        identity = input("enter username: ").strip()
        while not identity or identity in [id_.identity for id_ in identities]:
            if not identity:
                spinner.warn("a username is required for registration")
                identity = input("enter username: ").strip()
            elif identity in [id_.identity for id_ in identities]:
                spinner.warn("that username is already taken")
                identity = input(
                    "enter a different username: ").strip()
        spinner.start("creating new user ...")
        user = client.chat.services(chat_service_sid).users.create(
            identity=identity, friendly_name=identity)
        config['user']['identity'] = identity
        config['user']['friendly_name'] = identity
        config['user']['sid'] = user.sid

        # save user details in .user.cfg
        with open('.cchat.cfg', 'w+') as configfile:
            config.write(configfile)

        spinner.succeed(f"user {ansi_bold}{identity}{ansi_end} created")
    except KeyboardInterrupt:
        spinner.fail("cancelled")
        sys.exit()

    # add user to general channel
    try:
        client.chat.services(chat_service_sid).channels(
            'general').members.create(identity=identity)
        spinner.succeed(f"user added to #general")
    except TwilioRestException as err:
        if err.status == 404:
            # if !general channel, create it and add the user
            gen_chan = client.chat.services(chat_service_sid).channels.create(
                friendly_name='General Chat Channel',
                unique_name='general',
                created_by=identity
            )
            config['channels'] = {}
            config['channels']['general'] = gen_chan.sid
            with open('.cchat.cfg', 'w+') as configfile:
                config.write(configfile)
            client.chat.services(chat_service_sid).channels(
                'general').members.create(identity=identity)
            spinner.succeed(f"user added to #general")
        else:
            spinner.fail(err.msg)
            sys.exit()


def get_channels():
    """get channels that the logged in user is a member of"""
    channels_list = []

    # fetch service channels
    channels = client.chat.services(chat_service_sid).channels.list()
    gen = None
    for channel in channels:
        channels_list.append((
            channel.sid,
            channel.unique_name,
        ))

        if not gen and channel.unique_name == 'general':
            gen = channel.sid

    # add general to config if it doesn't exist
    try:
        config['channels']['general']
    except KeyError:
        config['channels'] = {}
        config['channels']['general'] = gen
        with open('.cchat.cfg', 'w+') as configfile:
            config.write(configfile)

    # have #general always first in list
    general_ch = config['channels']['general']
    channels_list.remove((general_ch, 'general'))
    channels_list.insert(0, (general_ch, 'general'))

    return channels_list


def send_message(channel, message):
    # creating a message with the client won't trigger a webhook
    # so do a direct POST request to the api
    url = f"https://chat.twilio.com/v2/Services/{chat_service_sid}/Channels/" \
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
    elif cmd_string.startswith('/sms'):
        args = cmd_string.split(None, 2)
        if len(cmd_string.split()) < 3:
            return "Error: MOBILE_NUMBER and MESSAGE arguments are required"
        return send_sms(args[1], args[2])
    elif cmd_string.startswith('/cleanup'):
        if len(cmd_string.split()) > 1:
            return "Error: too many arguments supplied for command"
        return cleanup()
    else:
        return "Error: invalid command"


def add_channel(name):
    try:
        client.chat.services(chat_service_sid).channels.create(
            unique_name=name, created_by=identity)
        client.chat.services(chat_service_sid).channels(name).members.create(
            identity=identity)
        return f"{ansi_italics}{ansi_bold}#{name} created{ansi_end}"
    except TwilioRestException as e:
        return f"{ansi_red}{e.msg}{ansi_end}"


def delete_channel(name):
    try:
        client.chat.services(chat_service_sid).channels(name).delete()
        return f"{ansi_italics}{ansi_bold}#{name} deleted{ansi_end}"
    except TwilioRestException as e:
        return f"{ansi_red}{e.msg}{ansi_end}"


def send_sms(number, sms):
    try:
        client.messages.create(
            body=sms, messaging_service_sid=sms_service_sid, to=number)
        return f"{ansi_italics}{ansi_bold}sms sent to {number}{ansi_end}"
    except TwilioRestException as e:
        return f"{ansi_red}{e.msg}{ansi_end}"


def cleanup():
    users = client.chat.services(chat_service_sid).users.list()
    for u in users:
        if u.identity != 'admin':
            client.chat.services(chat_service_sid).users(u.sid).delete()
    channels = client.chat.services(chat_service_sid).channels.list()
    for ch in channels:
        client.chat.services(chat_service_sid).channels(ch.sid).delete()
    return "cleanup done"
