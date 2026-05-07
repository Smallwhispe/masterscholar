import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class Logger:
    """统一日志管理"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        log_file: str = "logs/system.log",
        level: str = "INFO",
    ):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.logger = logging.getLogger("OPCUASystem")
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
            )
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(message)s")
        )

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger


def setup_logging(config: dict = None) -> logging.Logger:
    """初始化日志系统"""
    if config is None:
        config = {}
    logger_config = Logger(
        log_file=config.get("log_file", "logs/system.log"),
        level=config.get("level", "INFO"),
    )
    return logger_config.get_logger()
