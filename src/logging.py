import logging
import sys
from loguru import logger

LOG_LEVEL = "DEBUG"       # DEBUG in dev, INFO in prod
APP_ENV = "local"            # "local" | "production" | "staging"


class InterceptHandler(logging.Handler):
    """Redirect standard logging (uvicorn, libraries) to loguru."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Map logging level to loguru level
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find where the log message came from
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())



def setup_logging() -> None:
    """Configure loguru for local dev + ready for production."""
    # 1) Remove default loguru handler
    logger.remove()

    # 2) Local development: pretty logs
    if APP_ENV == "local":
        logger.add(
            sys.stdout,
            level=LOG_LEVEL,
            backtrace=True,
            diagnose=True,
            enqueue=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
        )
    else:
        # Production-ish: JSON logs to stdout (good for Docker / log aggregation)
        logger.add(
            sys.stdout,
            level=LOG_LEVEL,
            backtrace=False,
            diagnose=False,
            enqueue=True,
            serialize=True,  # <-- JSON
        )

    # Optional: file logs (works for both envs)
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        level=LOG_LEVEL,
        encoding="utf-8",
    )

    # 3) Redirect standard logging → loguru (uvicorn, fastapi internals, etc.)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Important loggers to intercept
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False