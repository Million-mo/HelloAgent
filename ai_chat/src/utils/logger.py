"""统一日志管理模块 - 提供结构化日志记录功能。

功能特性:
1. 统一的日志格式和输出
2. 不同模块使用独立的logger
3. 支持文件和控制台双重输出
4. 彩色日志输出便于查看
5. 日志轮转防止文件过大
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


# ANSI颜色代码
class LogColors:
    """日志颜色定义"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # 日志级别颜色
    DEBUG = "\033[36m"      # 青色
    INFO = "\033[32m"       # 绿色
    WARNING = "\033[33m"    # 黄色
    ERROR = "\033[31m"      # 红色
    CRITICAL = "\033[35m"   # 紫色


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    FORMATS = {
        logging.DEBUG: f"%(asctime)s | {LogColors.DEBUG}%(levelname)-8s{LogColors.RESET} | %(name)-30s | %(message)s",
        logging.INFO: f"%(asctime)s | {LogColors.INFO}%(levelname)-8s{LogColors.RESET} | %(name)-30s | %(message)s",
        logging.WARNING: f"%(asctime)s | {LogColors.WARNING}%(levelname)-8s{LogColors.RESET} | %(name)-30s | %(message)s",
        logging.ERROR: f"%(asctime)s | {LogColors.ERROR}%(levelname)-8s{LogColors.RESET} | %(name)-30s | [%(filename)s:%(lineno)d] %(message)s",
        logging.CRITICAL: f"%(asctime)s | {LogColors.CRITICAL}%(levelname)-8s{LogColors.RESET} | %(name)-30s | [%(filename)s:%(lineno)d] %(message)s",
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(
            fmt=log_fmt,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return formatter.format(record)


class FileFormatter(logging.Formatter):
    """文件日志格式化器（不包含颜色代码）"""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(
    log_dir: Optional[str] = "logs",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    初始化全局日志配置
    
    Args:
        log_dir: 日志文件目录
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件备份数量
    """
    # 创建日志目录
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
    
    # 获取根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除已有的处理器
    root_logger.handlers.clear()
    
    # 控制台处理器（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志目录）
    if log_dir:
        file_handler = RotatingFileHandler(
            filename=log_path / "app.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FileFormatter())
        root_logger.addHandler(file_handler)
        
        # 错误日志单独记录
        error_handler = RotatingFileHandler(
            filename=log_path / "error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(FileFormatter())
        root_logger.addHandler(error_handler)
    
    # 设置第三方库的日志级别，避免过多输出
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # 统一 uvicorn 日志格式
    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.error").handlers.clear()
    
    root_logger.info("日志系统初始化完成")
    root_logger.info(f"日志级别: {log_level.upper()}")
    if log_dir:
        root_logger.info(f"日志目录: {log_path.absolute()}")


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger实例
    
    Args:
        name: logger名称，通常使用 __name__
        
    Returns:
        Logger实例
    """
    return logging.getLogger(name)
