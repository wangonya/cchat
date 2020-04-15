import configparser
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from halo import Halo
from prompt_toolkit import ANSI
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
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

config = configparser.ConfigParser()
config.read('.cchat.cfg')
identity = config['user']['identity']

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


def process_response(response):
    try:
        if response.get('/?EventType') and response['/?EventType'][0] in (
                'onMemberAdded', 'onMemberRemoved', ):
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
    title="messages")


def chat_handler(buffer, message):
    try:
        output = output_field.text + message
    except BaseException as e:
        output = "\n\n{}".format(e)

    # Add text to output buffer.
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
                channels_window.current_value = input_field.text.split()[1]
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
