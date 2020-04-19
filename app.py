import sqlite3
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from halo import Halo
from prompt_toolkit import ANSI
from prompt_toolkit.application import Application, get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import to_formatted_text, \
    fragment_list_to_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next
from prompt_toolkit.layout import BufferControl
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import SearchToolbar, TextArea, Frame, RadioList

import utils
from utils import ansi_bold, ansi_italics, ansi_end

conn = sqlite3.connect('.chat.db', check_same_thread=False)
c = conn.cursor()
conn.execute('''CREATE TABLE IF NOT EXISTS history
                    (id integer primary key, 
                    msg_time time, sender text, msg text, channel text)''')

identity = utils.config['user']['identity']

spinner = Halo(spinner="dots", text="starting app ...")
spinner.start()

cmd_area_text = "type in command/message - ctrl-c to quit"


class ChatServer(BaseHTTPRequestHandler, ):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, params):
        """Shows the url params on the browser in html.
            Nothing useful. Just for debugging
            """
        content = f"<html><body><p>{params}</p></body></html>"
        return content.encode("utf8")

    def do_GET(self):
        self._set_headers()
        buffer = Application.current_buffer
        params = parse_qs(self.path)
        self.wfile.write(self._html(params))
        chat_handler(buffer, process_response(params))

    def log_message(self, format, *args):
        """suppress logs"""
        return


def chat_server(server_class=HTTPServer,
                handler_class=ChatServer,
                addr="localhost",
                port=8000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


def process_response(response, from_db=False):
    """receives response from webhook when actions happen on the chat client
    processes response and returns a formatted message to show on the client
    response might also be from db in the case of fetching chat history"""
    try:
        if from_db:
            processed_response = ''
            for line in response:
                message_time = line[1]
                message_from = line[2]
                message_body = line[3]
                processed_response += f"{message_time} " \
                                      f"{message_from}  " \
                                      f"{message_body}\n"
        else:
            if response.get('/?EventType') and response['/?EventType'][0] in (
                    'onMemberAdded', 'onMemberRemoved',):
                processed_response = f"{ansi_italics}{response['Identity'][0]} " \
                                     f"{response['Reason'][0].lower()}{ansi_end}\n"
            else:
                message_date = datetime.strptime(
                    response['DateCreated'][0], '%Y-%m-%dT%H:%M:%S.%fZ'
                )
                message_time = message_date.strftime("%H:%M")
                message_from = response['From'][0]
                message_body = response['Body'][0]
                processed_response = f"{message_time} " \
                                     f"{ansi_bold}{message_from}{ansi_end}  " \
                                     f"{message_body}\n"
        return f"{processed_response}"
    except KeyError as e:
        return f"Failed to parse response: {e}\n"
    except Exception as e:
        return f"An error occurred: {e}"


spinner.start("rendering interface ...")

# layout.
search_field = SearchToolbar()  # For reverse search.
output_field = Buffer()
output_field.text = f"logged in as {ansi_bold}{identity}{ansi_end}\n\n"


class FormatText(Processor):
    def apply_transformation(self, input_):
        fragments = to_formatted_text(
            ANSI(fragment_list_to_text(input_.fragments)))
        return Transformation(fragments)


output_window = Frame(Window(BufferControl(
    buffer=output_field,
    focusable=False,
    input_processors=[FormatText()]),
    wrap_lines=True),
    title="#general")


def chat_handler(buffer, message, from_db=False):
    """from_db=True if showing chat history"""
    try:
        output = output_field.text + message
        output_field.document = Document(
            text=output, cursor_position=len(output),
        )
    except BaseException as e:
        output = output_field.text + "{}\n".format(e)
        output_field.document = Document(
            text=output, cursor_position=len(output),
        )
    else:
        """When a user switches channels, we want to clear the messages 
        in the current channel and show the messages from the new channel.
        When they come back to a previous channel, they expect to see the 
        messages they left there (+new unread ones if any). Fetching all 
        channel messages from the server each time would be expensive, 
        so save chat in sqlite db and fetch from there."""
        if not from_db:
            try:
                msg_data = message.split()
                c.execute('INSERT INTO history VALUES (NULL,?,?,?,?)',
                          (msg_data[0], msg_data[1], msg_data[2],
                           channels_window.current_value))
                conn.commit()
            except Exception as e:
                conn.rollback()
                output = output_field.text + "{}\n".format(e)
                output_field.document = Document(
                    text=output, cursor_position=len(output),
                )


channels_window = RadioList(utils.get_channels())
channels_window.current_value = 'general'
channels_frame = Frame(channels_window, title="channels",
                       width=23)

upper_container = VSplit([channels_frame, output_window])

input_field = TextArea(
    height=1,
    prompt='> ',
    multiline=False,
    wrap_lines=False,
    search_field=search_field,
)

command_window_frame = Frame(input_field, title=cmd_area_text)

container = HSplit(
    [
        upper_container,
        command_window_frame,
        search_field,
    ]
)

# The key bindings.
bindings = KeyBindings()


@bindings.add("c-c")
@bindings.add("c-q")
def _(event):
    """ Pressing Ctrl-Q or Ctrl-C will exit the user interface. """
    event.app.exit()


@bindings.add('tab')
def tab_(event):
    focus_next(event)


@Condition
def input_buffer_active():
    """Only activate 'enter' key binding if input buffer is not active"""
    if not get_app().layout.buffer_has_focus:
        active_channel = channels_window.values[channels_window._selected_index][0]
        output_window.title = f"#{active_channel}"
        c.execute('SELECT * FROM history WHERE channel=?', (active_channel,))
        chat_history = c.fetchall()
        output_field.document = Document(
            text='', cursor_position=0,
        )
        buffer = Application.current_buffer
        chat_handler(buffer, process_response(chat_history, True), True)


@bindings.add('enter', filter=input_buffer_active)
def enter_(event):
    pass


# Style.
style = Style(
    [
        ("line", "#004400"),
    ]
)


# handle commands
def command_handler(buffer):
    # input starting with '/' is treated as a command
    try:
        if input_field.text.startswith('/'):  # command
            cmd_response = utils.command_handler(input_field.text)
            output = f"{cmd_response}\n"
            new_text = output_field.text + output
            output_field.document = Document(
                text=new_text, cursor_position=len(new_text),
            )
            if cmd_response.find('Error') == -1 and \
                    input_field.text.find('channel') != -1:
                # channel command - refresh channel list
                channels_window.values = utils.get_channels()
                if input_field.text.find('+') != -1:
                    channels_window.current_value = input_field.text.split()[1]
                elif input_field.text.find('-') != -1:
                    if channels_window.current_value == \
                            input_field.text.split()[1]:
                        channels_window.current_value = 'general'
        else:  # message
            utils.send_message(channels_window.current_value,
                               input_field.text)
    except BaseException as e:
        output = f"\n\n{e}"
        new_text = output_field.text + output
        output_field.document = Document(
            text=new_text, cursor_position=len(new_text),
        )


input_field.accept_handler = command_handler
spinner.succeed("interface rendered")

spinner.start("starting app ...")
# Run application.
application = Application(
    layout=Layout(container, focused_element=input_field),
    key_bindings=bindings,
    style=style,
    mouse_support=True,
    full_screen=True,
    erase_when_done=True,
)
spinner.succeed("all good")


def main():
    # start server
    daemon = threading.Thread(name='daemon_server',
                              target=chat_server)
    daemon.setDaemon(True)  # killed once the main thread is dead
    daemon.start()
    # start app
    application.run()


if __name__ == "__main__":
    main()
