import logging


class _RedactSecrets(logging.Filter):
    """Drop the bot token from log lines (httpx logs request URLs that contain it)."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self._secrets:
            message = message.replace(secret, "***")
        record.msg, record.args = message, None
        return True


def setup_logging(secrets: list[str] | None = None, level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s", force=True
    )
    # httpx logs full request URLs, which contain the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if secrets:
        for handler in logging.getLogger().handlers:
            handler.addFilter(_RedactSecrets(secrets))
