import logging

from app.core.request_context import current_request_id


class RequestIdFilter(logging.Filter):
    """Adds the current request id to every log record, so logs and audit records can be correlated."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id() or "-"
        return True


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] [%(request_id)s] %(message)s",
        handlers=[handler],
    )
