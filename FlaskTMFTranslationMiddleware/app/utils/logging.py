import logging
import os

def configure_logging(level: str = "INFO"):
    """
    Configure root logging level and format from environment.
    """
    lvl = getattr(logging, (level or os.getenv("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
