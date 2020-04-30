# cchat

A cli chat application made with Python &amp; Twilio's Programmable Chat REST API.

### How it works

This application provides a command line interface where registered users can chat on different channels.

## Features

- User registration with 2FA using Twilio's Authy API
- Terminal interface
- Chat using Twilio's Programmable Chat API
- Create and delete channels using the `/+channel` and `/-channel` commands
- Receive system notifications when your username is @mentioned in a channel
- Send sms to teammates right from the chat interface using the `/sms` command

## Set up

### Requirements

- Python 3
- Linux / MacOs terminal
- [ngrok](https://ngrok.com/) so we can expose our local port 8000 online for the chat webhook

### Twilio Account Settings

Before we begin, we need to collect
all the config values we need to run the application:

| Config&nbsp;Value | Description                                                                                                                                                  |
| :---------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Account&nbsp;Sid  | Your primary Twilio account identifier - find this [in the Console](https://www.twilio.com/console).                                                         |
| Auth&nbsp;Token   | Used to authenticate - [just like the above, you'll find this here](https://www.twilio.com/console).                                                         |
| Phone&nbsp;number | A Twilio phone number in [E.164 format](https://en.wikipedia.org/wiki/E.164) - you can [get one here](https://www.twilio.com/console/phone-numbers/incoming) |
| Chat service SID  | Programmable Chat service SID - - you can use SID of the default conversations service in your console or create a new chat service
| SMS service SID   | Programmable SMS service SID - you can use SID of the default conversations service in your console or create a new sms service
| Authy API Key     | Authy API key for authentication - you'll need to create an Authy app then get this from the settings

## Running The App

After the above requirements have been met:

1. Clone this repository and `cd` into it

```bash
git clone https://github.com/wangonya/cchat.git
cd cchat
```

2. Create and activate virtual environment

```bash
# I'll use virtualenv. You can use pipenv or whatever else you're comfortable with
virtualenv env
source env/bin/activate
```
3. Install dependencies

```bash
# With your virtual environment activated
pip install -r requirements.txt
```

4. Set your environment variables

I've provided a sample environment file `.sample.env`. All the values in it should be filled correctly.

```bash
cp .sample.env .env
```

In your `.env` file:

```bash
export ACCOUNT_SID=your account sid
export AUTH_TOKEN=your auth token
export CHAT_SERVICE_SID=your chat service sid
export SMS_SERVICE_SID=your sms service sid
export AUTHY_API_KEY=your authy api key
```

After you've filled everything out, run:

```bash
source .env
```

If any of these are not filled, the app will not run.

![screenshot](https://i.ibb.co/XxbcVqG/2020-04-29-06-39.png)

5. Run the application

This app has only been tested in unix terminals (linux & mac). I don't have access to a windows machine 
so I was not able to test it for windows.

```bash
python app.py
```

6. User registration

As a new user, you will have to fill in some information to be registered.

Because we are using Authy, an email, country code and phone number is required. 
An sms token will be sent to the phone number provided.

After providing the correct token, a username as a last step to identify you in the chat channels will be necessary.

![screenshot](https://i.ibb.co/vwrps0Q/cchat-auth.png)

Subsequent logins will be automatic.

![gif](https://i.ibb.co/ZLsB1Fh/valid.gif)


7. ngrok

Once the app is running, a local server is begun in the background on port 8000. We need to attach this to our 
webhook to be able to send and receive messages from others online.

In a different terminal, cd into where you have your ngrok and run:

```bash
./ngrok http 8000
```

This should give you a forwarding link, which you'll then need to copy into your webhook in the 
Programmable Chat API settings.

![screenshot ngrok](https://i.ibb.co/rtS7XL3/twilio-ngrok.png)

Also make sure you check/enable the options marked in red.


### Using the app

![app-screenshot](https://i.ibb.co/7tqTdy3/cchat-interface.png)

- Send messages by typing in the input box at the bottom and pressing enter
- Create a new channel by running `/+channel CHANNEL_NAME`
- Delete a channel by running `/-channel CHANNEL_NAME`
- Change focus from the input area to the channels window and back by pressing `TAB`
- With the channels window in focus, switch channels using the up and down keys
- Send an sms by running `/sms PHONE_NUMBER MESSAGE`

PS: Chat history is saved in an in-memory sqlite database so it gets lost once 
the app is closed.

You cannot run two sessions of this app at the same time because the port 8000 will already be in use. 
To test out chatting between different users, you can set up one of the [starter apps](https://www.twilio.com/docs/chat/javascript/quickstart#download-configure-and-run-the-starter-app) 
with the same credentials in the `.env` so that the app is connected to the same service. 

Below is an example of a chat session between two web clients and the terminal client.

![chat](https://i.ibb.co/nLNKT4t/chat.gif)

### Tests

The project does not have tests yet. TODO.                                                                |

## Resources

- [Twilio Authy](https://www.twilio.com/docs/authy)
- [Twilio Programmable Chat](https://www.twilio.com/docs/chat)
- [Twilio SMS](https://www.twilio.com/docs/sms)
- [Prompt Toolkit](https://python-prompt-toolkit.readthedocs.io/en/3.0.3/)

## Contributing

This project is open source and welcomes contributions.

## License

[MIT](http://www.opensource.org/licenses/mit-license.html)