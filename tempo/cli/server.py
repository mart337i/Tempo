import sys
import textwrap
import signal

from .commands import Command

class Server(Command):
    """Run the Tempo server"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.epilog = textwrap.dedent("""
            Start the Tempo server with specified configuration.
            
            Examples:
              # Start with defaults
              tempo-bin server test
              
              # Start with hot reload on custom port
              tempo-bin server test --reload --port 9000
              
              # Start with config file
              tempo-bin server test --config ./my-tempo.conf
              
              # Production mode with multiple workers
              tempo-bin server production --workers 4 --host 0.0.0.0
        
        """)

    def run(
        self,
        cmdargs,
    ):
        """Start the server application."""
        parser = self.parser

        # Positional arguments
        parser.add_argument(
            "name", help="Name of the API server to run", nargs="?", default="Tempo API"
        )

        # Configuration file
        parser.add_argument(
            "--config",
            "-c",
            type=str,
            help="Path to configuration file (default: ./tempo.conf if exists)",
        )

        # Server settings
        parser.add_argument(
            "--host", type=str, help="Host to bind the server to (default: 0.0.0.0)"
        )
        parser.add_argument(
            "--port", type=int, help="Port to bind the server to (default: 8000)"
        )
        parser.add_argument(
            "--reload",
            action="store_true",
            default=None,
            help="Enable auto-reload on code changes (development mode)",
        )
        parser.add_argument(
            "--no-reload",
            action="store_false",
            dest="reload",
            help="Disable auto-reload (production mode, default)",
        )
        parser.add_argument(
            "--workers", type=int, help="Number of worker processes (default: 1)"
        )

        if not cmdargs:
            sys.exit(parser.print_help())

        args = parser.parse_args(args=cmdargs)

        from tempo.fastapi import create_api

        print("Starting server... Press Ctrl+C to stop.")
        create_api().start(**vars(args))