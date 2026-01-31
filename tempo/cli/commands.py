import argparse
import contextlib
import re
import sys
from inspect import cleandoc
from pathlib import Path
import tempo.cli

COMMAND_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$', re.I)
PROG_NAME = Path(sys.argv[0]).name
commands = {}
"""All loaded commands"""

class Command:
    name = None
    description = None
    epilog = None
    _parser = None

    def __init_subclass__(cls):
        cls.name = cls.name or cls.__name__.lower()
        module = cls.__module__.rpartition('.')[2]
        if not cls.is_valid_name(cls.name):
            raise ValueError(
                f"Command name {cls.name!r} "
                f"must match {COMMAND_NAME_RE.pattern!r}")
        if cls.name != module:
            raise ValueError(
                f"Command name {cls.name!r} "
                f"must match Module name {module!r}")
        commands[cls.name] = cls 

    @property
    def prog(self):
        return f"{PROG_NAME} - {self.name}"

    @property
    def parser(self):
        if not self._parser:
            self._parser = argparse.ArgumentParser(
                formatter_class=argparse.RawDescriptionHelpFormatter,
                prog=self.prog,
                description=cleandoc(self.description or self.__doc__ or ""),
                epilog=cleandoc(self.epilog or ""),
            )
        return self._parser

    @classmethod
    def is_valid_name(cls, name):
        return re.match(COMMAND_NAME_RE, name)


def load_internal_commands():
    """ Load ``commands`` from ``tempo.cli`` """
    for path in tempo.cli.__path__:
        for module in Path(path).iterdir():
            if module.suffix != '.py':
                continue
            __import__(f'tempo.cli.{module.stem}')


def find_command(name: str) -> Command | None:
    """ Get command by name. """

    # built-in commands
    if command := commands.get(name):
        return command

    # import from tempo.cli
    with contextlib.suppress(ImportError):
        __import__(f'tempo.cli.{name}')
        return commands[name]

    # import from tempo.addons.*.cli
    return commands.get(name)


def execute_command():
    args = sys.argv[1:]

    if len(args) and not args[0].startswith('-'):
        # Command specified, search for it
        command_name = args[0]
        args = args[1:]
    elif '-h' in args or '--help' in args:
        # No command specified, but help is requested
        command_name = 'help'
        args = [x for x in args if x not in ('-h', '--help')]
    else:
        # No command specified, use default
        command_name = 'help'
        args = [x for x in args if x not in ('-h', '--help')]

    if command := find_command(command_name):
        tempo.cli.COMMAND = command_name
        command().run(args)
    else:
        message = (
            f"Unknown command {command_name!r}.\n"
            f"Use '{PROG_NAME} --help' to see the list of available commands."
        )
        sys.exit(message)