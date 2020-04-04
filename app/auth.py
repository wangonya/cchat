import os
import click

from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import ChatGrant
from twilio.rest import Client

from . import cli


@cli.command()
@click.argument('identity')
def auth(identity):
    # Credentials
    account_sid = os.getenv('ACCOUNT_SID')
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    service_sid = os.getenv('SERVICE_SID')
    # identity = 'user@example.com'

    # Create access token with credentials
    token = AccessToken(account_sid, api_key, api_secret, identity=identity)

    # Create a Chat grant and add to token
    chat_grant = ChatGrant(service_sid=service_sid)
    token.add_grant(chat_grant)

    # Return token info as JSON
    print(token.to_jwt())