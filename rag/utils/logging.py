import logging
import sys
from typing import Optional

def setup_logging(level: str = "INFO") -> None:
    """
    简单的结构化控制台日志配置。
    """
    root = logging.getLogger()
    if root.handlers:
        # 避免重复添加 handler
        return

    handler = logging.StreamHandler(sys.stdout)
    fmt = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)
    root.setLevel(level.upper())

def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or __name__)
