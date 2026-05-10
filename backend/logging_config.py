# logging_config.py - Configuración de logging estructurado
# Formato JSON para plataformas de hosting (Render, Railway, etc.)

import sys
import json
import loguru
from datetime import datetime


class JsonFormatter:
    """Formateador de logs en JSON estructurado para parsing en plataformas de hosting"""

    def __init__(self):
        self.default_fields = {
            "service": "linsolve-backend",
            "version": "1.0.0"
        }

    def __call__(self, record: loguru.Record) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "message": record["message"],
            **self.default_fields
        }

        if hasattr(record, "extra"):
            log_entry.update(record["extra"])

        if record["exception"] is not None:
            log_entry["exception"] = {
                "type": type(record["exception"]).__name__,
                "message": str(record["exception"])
            }

        return json.dumps(log_entry) + "\n"


def configure_logging(level: str = "INFO") -> None:
    """
    Configura el logging de la aplicación.

    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
    """
    logger.remove()

    logger.add(
        sys.stdout,
        format="{message}",
        level=level,
        serialize=True,
        handler=JsonFormatter()
    )

    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG" if level == "DEBUG" else "WARNING"
    )


def get_logger(name: str = "linsolve"):
    """Obtiene una instancia del logger configurado"""
    return loguru.logger.bind(logger_name=name)