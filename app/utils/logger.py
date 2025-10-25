import logging
import json
from typing import Optional, Dict, Any


class CustomLogger:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.FileHandler("app.log"),
                logging.StreamHandler()
            ]
        )
        self._logger = logging.getLogger(__name__)

    def _format_message(self, category: str, message: str, context: Optional[Dict[str, Any]] = None,
                        error: Optional[Exception] = None) -> str:
        """Format log message with category, message, context and error"""
        parts = [f"[{category}] {message}"]

        if context:
            parts.append(f"Context: {json.dumps(context, default=str)}")

        if error:
            parts.append(f"Error: {str(error)}")

        return " | ".join(parts)

    def info(self, category: str, message: str, context: Optional[Dict[str, Any]] = None):
        formatted = self._format_message(category, message, context)
        self._logger.info(formatted)

    def warn(self, category: str, message: str, context: Optional[Dict[str, Any]] = None):
        formatted = self._format_message(category, message, context)
        self._logger.warning(formatted)

    def error(self, category: str, message: str, error: Optional[Exception] = None,
              context: Optional[Dict[str, Any]] = None):
        formatted = self._format_message(category, message, context, error)
        self._logger.error(formatted, exc_info=error is not None)


logger = CustomLogger()