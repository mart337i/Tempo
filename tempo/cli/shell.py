import textwrap

from .commands import Command


class Shell(Command):
    """Open an interactive IPython shell with Tempo preloaded"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.epilog = textwrap.dedent("""
            Pre-loaded in the shell:
              config   - TempoConfig instance (get_config())
              db       - Database instance (from tempo.db)
              Base     - SQLAlchemy declarative base

            Examples:
              # inspect config
              config.get("server", "port")

              # run a raw query
              with db.cr as conn:
                  print(conn.execute(text("SELECT 1")).fetchall())

              # ORM session
              with db.session as s:
                  users = s.query(User).all()
        """)

    def run(self, cmdargs):
        parser = self.parser
        parser.add_argument(
            "--config",
            "-c",
            type=str,
            help="Path to configuration file (default: ./tempo.conf if exists)",
        )

        args = parser.parse_args(args=cmdargs)

        from tempo.config import get_config
        from tempo.db import db, Base
        from tempo.log import setup_logging

        config = get_config(config_file=args.config)
        setup_logging(config)

        banner = textwrap.dedent(f"""
            Tempo Shell {_version()}
            ─────────────────────────
            config   → TempoConfig   (tempo.conf loaded)
            db       → Database      (configured: {db.is_configured})
            Base     → DeclarativeBase

            Type 'exit' or Ctrl-D to quit.
        """)

        namespace = {
            "config": config,
            "db": db,
            "Base": Base,
        }

        try:
            from IPython import start_ipython

            start_ipython(
                argv=[f"--InteractiveShell.banner1={banner}"],
                user_ns=namespace,
            )
        except ImportError:
            # fallback to stdlib if IPython is somehow missing
            import code

            code.interact(banner=banner, local=namespace)


def _version():
    from tempo import VERSION

    return VERSION
