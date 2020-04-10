import subprocess
import sys
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from prompt_toolkit.application import Application
from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next
from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import SearchToolbar, TextArea, Frame, RadioList

import commands

welcome_text = "Welcome text \n\n"
cmd_area_text = "type in command/message - ctrl-c to quit"
command_mode = False


def main():
    class ChatServer(BaseHTTPRequestHandler, ):
        def _set_headers(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

        def _html(self, message):
            """This just generates an HTML document that includes `message`
            in the body. Override, or re-write this do do more interesting stuff.
            """
            content = f"<html><body><p>{message}</p></body></html>"
            return content.encode("utf8")

        def do_GET(self):
            self._set_headers()
            self.wfile.write(self._html(f"connected"))
            buffer = Application.current_buffer
            params = parse_qs(self.path)
            chat_handler(buffer, self.process_reponse(params))

        def process_reponse(self, response):
            try:
                message_date = datetime.strptime(
                    response['DateCreated'][0], '%Y-%m-%dT%H:%M:%S.%fZ'
                )
                message_date = message_date.strftime("%m-%d-%Y, %H:%M:%S")
                message_from = response['From'][0]
                message_body = response['Body'][0]
                processed_response = f"\n[{message_date}]\n" \
                                     f"{message_from} >>> {message_body}\n "
                return f"{processed_response}"
            except KeyError:
                return "Someone messed things up.\n"

        def log_message(self, format, *args):
            """prevent log messages from showing every time a client
            connects """
            return

    def chat_server(server_class=HTTPServer,
                    handler_class=ChatServer,
                    addr="localhost",
                    port=8000):
        server_address = (addr, port)
        httpd = server_class(server_address, handler_class)
        httpd.serve_forever()

    daemon = threading.Thread(name='daemon_server',
                              target=chat_server)
    # set as a daemon so it will be killed once the main thread is dead
    daemon.setDaemon(True)
    daemon.start()

    # The layout.
    search_field = SearchToolbar()  # For reverse search.

    output_field = TextArea(focusable=False)
    output_window = Frame(output_field, title="messages")

    def chat_handler(buffer, message):
        try:
            output = message
        except BaseException as e:
            output = "\n\n{}".format(e)
        new_text = output_field.text + output

        # Add text to output buffer.
        output_field.buffer.document = Document(
            text=new_text, cursor_position=len(new_text),
        )

    channels_window = RadioList(commands.get_channels())
    channels_frame = Frame(channels_window, title="channels",
                           width=23)

    upper_container = VSplit([channels_frame, output_window])

    input_field = TextArea(
        height=1,
        prompt='> ',
        # prompt=cli,
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

    @bindings.add('escape')
    def cmd_mode(event):
        global command_mode
        command_mode = not command_mode
        if command_mode:
            command_window_frame.title = 'command mode | esc to enter insert mode'
        else:
            command_window_frame.title = 'insert mode | esc to enter command mode'

    # Style.
    style = Style(
        [
            ("line", "#004400"),
        ]
    )

    # handle commands
    def command_handler(buffer):
        global command_mode
        try:
            if command_mode:
                cmd = subprocess.run([f"{sys.executable}", commands.path(),
                                      f"{input_field.text}"], text=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,)
                if cmd.returncode != 0:
                    output = f"{cmd.stderr}\n"
                else:
                    output = f"{cmd.stdout}\n"
            else:
                output = commands.send_message(input_field.text)
        except BaseException as e:
            output = f"\n\n{e}"
        new_text = output_field.text + output

        # Add text to output buffer.
        output_field.buffer.document = Document(
            text=new_text, cursor_position=len(new_text)
        )

    input_field.accept_handler = command_handler

    # Run application.
    application = Application(
        layout=Layout(container, focused_element=input_field),
        key_bindings=bindings,
        style=style,
        mouse_support=True,
        full_screen=True,
        # editing_mode=EditingMode.VI
    )

    application.run()


if __name__ == "__main__":
    main()
