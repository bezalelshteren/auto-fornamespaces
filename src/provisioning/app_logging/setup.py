import logging
import sys
from .config import load_logging_config
from .postgres_handler import PostgresLogHandler

_CONFIGURED = False

def setup_logging():
    global _CONFIGURED
    logger = logging.getLogger("provisioning")
    if _CONFIGURED:
        return logger

    config = load_logging_config()
    level = getattr(logging, config.level, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    try:
        postgres = PostgresLogHandler(
            host=config.postgres_host,
            port=config.postgres_port,
            dbname=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password,
            min_size=config.min_connections,
            max_size=config.max_connections,
        )
        postgres.start()
        postgres.setLevel(logging.DEBUG)
        logger.addHandler(postgres)
        logger.info("PostgreSQL logging initialized")
    except Exception as exc:
        logger.error("PostgreSQL logging is unavailable: %s", exc)

    _CONFIGURED = True
    return logger
