
import sys
import textwrap
from .commands import Command

class Server(Command):
    """ Run the Tempo server """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.epilog = """Start the Tempo server with specified configuration."""

    def run(
        self,
        cmdargs,
    ):
        """Start the server application."""
        parser = self.parser
        parser.add_argument('name', help="Name of the API server to run", nargs='?')
        parser.add_argument(
            '--host', type=str, default='0.0.0.0',
            help="Host to bind the server to (default: %(default)s)")
        parser.add_argument(
            '--port', type=int, default=8000,
            help="Port to bind the server to (default: %(default)s)")

        if not cmdargs:
            sys.exit(parser.print_help())

        args = parser.parse_args(args=cmdargs)

        from tempo.fastapi import create_api
        
        # Now configure and start the app
        create_api().start(**vars(args))