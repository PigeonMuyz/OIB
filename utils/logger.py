import logging
import os
import json
from datetime import datetime
from colorlog import ColoredFormatter

# 用于跟踪是否已经初始化过日志系统
_log_initialized = False

def load_config():
    """加载配置文件"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load config: {e}")
    return {"log": {"level": "INFO"}}  # 默认配置

def get_log_level(level_str: str) -> int:
    """转换日志级别字符串为logging级别"""
    return {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'ERROR': logging.ERROR
    }.get(level_str.upper(), logging.INFO)

def rotate_log_file():
    """处理日志文件的轮转，按日期合并日志文件"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
    os.makedirs(log_dir, exist_ok=True)

    latest_log = os.path.join(log_dir, 'latest.log')
    if os.path.exists(latest_log):
        # 生成基于日期的文件名
        date_filename = datetime.now().strftime('%Y-%m-%d.log')
        target_file = os.path.join(log_dir, date_filename)

        # 如果目标文件已存在，追加内容
        if os.path.exists(target_file):
            with open(latest_log, 'r') as source, open(target_file, 'a') as target:
                target.write('\n')  # 添加一个换行作为分隔
                target.write(source.read())
            os.remove(latest_log)
        else:
            # 如果目标文件不存在，直接重命名
            os.rename(latest_log, target_file)

def setup_logger(name: str) -> logging.Logger:
    """
    设置一个带有彩色输出的logger，同时写入文件

    Args:
        name: logger的名称

    Returns:
        logging.Logger: 配置好的logger实例
    """
    global _log_initialized

    # 加载配置
    config = load_config()
    console_level = get_log_level(config['log']['level'])

    # 检查是否已经存在同名logger
    logger = logging.getLogger(name)

    # 清除所有已存在的处理器
    if logger.handlers:
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)  # 总是设置为最低级别以捕获所有日志
    logger.propagate = False

    # 第一次初始化时处理日志文件轮转
    if not _log_initialized:
        rotate_log_file()
        _log_initialized = True

    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
    latest_log = os.path.join(log_dir, 'latest.log')

    # 设置文件处理器（记录所有级别的日志）
    file_handler = logging.FileHandler(latest_log, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 设置控制台处理器（根据配置的级别）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)

    # 设置彩色日志格式
    log_colors = {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }

    console_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s%(reset)s %(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s %(white)s%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors=log_colors
    )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger
