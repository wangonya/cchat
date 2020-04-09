import os
import sys
import subprocess
import threading
import commands
from http.server import HTTPServer, BaseHTTPRequestHandler

from subprocess import CalledProcessError
from prompt_toolkit.application import Application
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import SearchToolbar, TextArea, Frame
from twilio.rest import Client

welcome_text = "Welcome text \n\n"
cmd_area_text = "Changes dynamically"


class TwilioClient:
    def __init__(self):
        self.account_sid = os.getenv('ACCOUNT_SID')
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        self.service_sid = os.getenv('SERVICE_SID')
        self.auth_token = os.getenv('AUTH_TOKEN')
        self.client = Client(self.account_sid, self.auth_token)


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
            chat_handler(Application.current_buffer, "test")

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

    output_field = TextArea(text=welcome_text)

    def chat_handler(buffer, message=None):
        try:
            output = "yey!"
        except BaseException as e:
            output = "\n\n{}".format(e)
        new_text = output_field.text + output

        # Add text to output buffer.
        output_field.buffer.document = Document(
            text=new_text, cursor_position=len(new_text)
        )

    input_field = TextArea(
        height=1,
        prompt='> ',
        # prompt=cli,
        multiline=False,
        wrap_lines=False,
        search_field=search_field
    )

    command_window_frame = Frame(input_field, title=cmd_area_text)

    container = HSplit(
        [
            output_field,
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

    # Style.
    style = Style(
        [
            ("line", "#004400"),
        ]
    )

    # handle commands
    def command_handler(buffer):
        try:
            cmd = subprocess.run([f"{sys.executable}", commands.path(),
                                  f"{input_field.text}"], text=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,)
            if cmd.returncode != 0:
                output = f"{cmd.stderr}\n"
            else:
                output = f"{cmd.stdout}\n"
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
    )

    application.run()


if __name__ == "__main__":
    main()
