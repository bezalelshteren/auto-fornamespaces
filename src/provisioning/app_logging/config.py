import os
from dataclasses import dataclass

@dataclass(frozen=True)
class LoggingConfig:
    level: str
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    min_connections: int
    max_connections: int

def load_logging_config() -> LoggingConfig:
    return LoggingConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "provisioning"),
        postgres_user=os.getenv("POSTGRES_USER", "provisioning"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
        min_connections=int(os.getenv("POSTGRES_LOG_MIN_CONNECTIONS", "1")),
        max_connections=int(os.getenv("POSTGRES_LOG_MAX_CONNECTIONS", "5")),
    )
