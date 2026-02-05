import logging
import sys

# loggers that get our handlers attached directly
_LOGGERS = ["tempo", "uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi"]


def setup_logging(config):
    """Configure logging from [logging] config section.

    Console output is always enabled.  A file handler is added only when
    config [logging] file is set to a non-empty path.

    Applies to both tempo and uvicorn loggers so that all server output goes
    through the same handlers with the same format.
    """
    level = getattr(
        logging, config.get("logging", "level", fallback="INFO").upper(), logging.INFO
    )
    fmt = config.get(
        "logging",
        "format",
        fallback="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    file = config.get("logging", "file", fallback="")

    formatter = logging.Formatter(fmt)

    # build handler list once
    handlers = []

    # console — always on
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(formatter)
    handlers.append(console)

    # file — only when configured
    if file:
        fh = logging.FileHandler(file)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        handlers.append(fh)

    # apply to every logger we care about
    for name in _LOGGERS:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers.clear()
        logger.propagate = False  # we own the handlers, stop bubbling
        for h in handlers:
            logger.addHandler(h)
