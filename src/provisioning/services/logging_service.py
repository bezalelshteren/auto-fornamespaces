import logging
import os
from datetime import datetime, timezone

import psycopg


DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "mydb")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres123")


logger = logging.getLogger("provisioning")

logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

console_handler.setFormatter(formatter)

logger.addHandler(console_handler)


def write_log_to_db(
    level: str,
    message: str,
):
    sql = """
        INSERT INTO provisioning_logs (
            timestamp,
            level,
            logger,
            stage,
            status,
            tenant,
            team,
            application,
            lifecycle,
            cluster,
            message,
            metadata
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s::jsonb
        )
    """

    values = (
        datetime.now(timezone.utc),
        level,
        "provisioning",
        "provision",
        "success",
        "test-tenant",
        "devops",
        "test-application",
        "dev",
        "devops1",
        message,
        "{}",
    )

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    ) as connection:

        with connection.cursor() as cursor:
            cursor.execute(sql, values)

        connection.commit()