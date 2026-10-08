import json
import logging
import traceback
from datetime import datetime, timezone
from psycopg_pool import ConnectionPool

class PostgresLogHandler(logging.Handler):
    """Write Python LogRecords to PostgreSQL without breaking provisioning."""
    def __init__(self, *, host, port, dbname, user, password, min_size=1, max_size=5):
        super().__init__()
        self.pool = ConnectionPool(
            conninfo=(f"host={host} port={port} dbname={dbname} user={user} password={password}"),
            min_size=min_size,
            max_size=max_size,
            open=False,
        )

    def start(self):
        self.pool.open(wait=True)

    def close(self):
        try:
            self.pool.close()
        except Exception:
            pass
        super().close()

    def emit(self, record):
        try:
            error_text = None
            if record.exc_info:
                error_text = "".join(traceback.format_exception(*record.exc_info))

            reserved = {
                "request_id", "stage", "status", "tenant", "team", "application",
                "lifecycle", "cluster", "target_site", "duration_ms"
            }
            ignored = {
                "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "taskName"
            }
            metadata = {}
            for key, value in record.__dict__.items():
                if key.startswith("_") or key in reserved or key in ignored:
                    continue
                try:
                    json.dumps(value)
                    metadata[key] = value
                except TypeError:
                    metadata[key] = str(value)

            sql = """
                INSERT INTO provisioning_logs
                (timestamp, level, logger, stage, status, tenant, team, application,
                 lifecycle, cluster, target_site, request_id, message, duration_ms, error, metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            values = (
                datetime.fromtimestamp(record.created, tz=timezone.utc),
                record.levelname,
                record.name,
                getattr(record, "stage", "unknown"),
                getattr(record, "status", None),
                getattr(record, "tenant", None),
                getattr(record, "team", None),
                getattr(record, "application", None),
                getattr(record, "lifecycle", None),
                getattr(record, "cluster", None),
                getattr(record, "target_site", None),
                getattr(record, "request_id", None),
                record.getMessage(),
                getattr(record, "duration_ms", None),
                error_text,
                json.dumps(metadata, default=str),
            )
            with self.pool.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, values)
                connection.commit()
        except Exception as exc:
            # Never let a PostgreSQL logging failure stop provisioning.
            logging.getLogger("provisioning.postgres_logging").error(
                "Failed to write log to PostgreSQL: %s", exc
            )
