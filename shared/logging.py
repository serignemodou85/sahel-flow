import json
import logging
from datetime import datetime, timezone

# Attributs standard d'un LogRecord Python.
# Tout ce qui est dans record.__dict__ ET absent de cet ensemble
# est un champ contextuel ajouté via extra={} → inclus dans le JSON.
_STDLIB_RECORD_ATTRS: frozenset[str] = frozenset({
    "args", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs",
    "msg", "name", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "thread", "threadName", "taskName",
})


class _JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        # Résout les arguments de formatage du message ("Hello %s" % "world")
        record.message = record.getMessage()

        entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.message,
        }

        # Champs contextuels : logger.info("msg", extra={"country": "SEN", "rows": 24})
        for key, value in record.__dict__.items():
            if key not in _STDLIB_RECORD_ATTRS:
                entry[key] = value

        # Exception traceback si présente
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        # default=str : sérialise les types non-JSON (datetime, Decimal…) proprement
        return json.dumps(entry, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    # Import différé : évite l'import circulaire si config.py venait à importer logging.py
    from shared.config import get_settings

    logger = logging.getLogger(name)
    logger.propagate = False   # évite la duplication vers le root logger d'Airflow

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)

    level_name = get_settings().log_level.upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    return logger
