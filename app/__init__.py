import os
import click
import configparser

from click_shell import shell
from halo import Halo

from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import ChatGrant
from twilio.base.exceptions import TwilioRestException

config = configparser.ConfigParser()
spinner = Halo(text='Connecting...', spinner='dots', text_color="green")
welcome = "Welcome to the cchat app 🥳 \n" \
          "Run cchat --help for options.\n"
prompt = 'cchat > '
client = None


class Connect:
    def __init__(self):
        self.account_sid = os.getenv('ACCOUNT_SID')
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        self.service_sid = os.getenv('SERVICE_SID')
        self.auth_token = os.getenv('AUTH_TOKEN')
        self.client = Client(self.account_sid, self.auth_token)


@shell(prompt=prompt, intro=welcome)
@click.pass_context
def cli(ctx):
    spinner.start()
    ctx.obj = Connect()
    global client
    client = ctx.obj.client
    spinner.succeed("Connected")


@cli.command()
@click.argument('identity')
@click.pass_obj
def login(ctx, identity):
    """Creates a new user with the given `identity`.
    The user `identity` and `sid` are written in a `.cchat.cfg` file for
    reference.
    Each new user automatically becomes a member of the general channel."""
    try:
        # create new user
        user = client.chat.services(ctx.service_sid).users.create(
            identity=identity)
        config['user'] = {}
        config['user']['identity'] = identity
        config['user']['sid'] = user.sid

        # save user details in .cchat.cfg
        with open('.cchat.cfg', 'w+') as configfile:
            config.write(configfile)
        spinner.info(f"New user created: {identity}")

        # add user to general channel
        try:
            channel = client.chat.services(ctx.service_sid).channels(
                'general').fetch()
            client.chat.services(ctx.service_sid).channels(
                channel.sid).members.create(identity=identity)
            spinner.info(f"{identity} added to {channel.unique_name}")
        except TwilioRestException as err:
            if err.status == 404:
                # if general channel doesn't exist, create it and add the user
                spinner.info("Creating general channel...")
                channel = client.chat.services(ctx.service_sid) \
                    .channels.create(
                    friendly_name='General Channel',
                    unique_name='general',
                    created_by=identity
                )
                spinner.info(f"Channel '{channel.unique_name}' created")
                client.chat.services(ctx.service_sid).channels(
                    channel.sid).members.create(identity=identity)
                spinner.info(f"{identity} added to {channel.unique_name}")
            else:
                spinner.fail(err.msg)

    except TwilioRestException as err:
        if err.status == 409:  # user exists
            spinner.info(f"Welcome back, {identity}")
        else:
            spinner.fail(err.msg)

    # # Create access token with credentials
    # token = AccessToken(account_sid, api_key, api_secret, identity=identity)
    #
    # # Create a Chat grant and add to token
    # chat_grant = ChatGrant(service_sid=service_sid)
    # token.add_grant(chat_grant)
    #
    # # Return token info as JSON
    # print(token.to_jwt())
