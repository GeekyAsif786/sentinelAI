import logging
from collections.abc import MutableMapping

import structlog


def configure_logging(log_level: str) -> None:
    log_level_number = logging.getLevelNamesMapping().get(log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level.upper(), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level_number),
    )


LogContext = MutableMapping[str, object]
