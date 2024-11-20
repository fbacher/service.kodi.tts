# coding=utf-8
"""
Defines the names of loggers for various sections/functions in TTS.
The goal is to allow you to enable only the logging that you are
interested in.
"""

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from typing import Dict, ForwardRef

from common.logger import BasicLogger


class Logger(StrEnum):

    SCRAPER = 'tts.scraper'
    NOISY_SCRAPER = 'tts.scraper.noisy'
    OLD_SCRAPER = 'tts.old_scraper'
    TTS_ENGINE = 'tts.engine'
    TTS_PLAYER = 'tts.player'
    TTS_PROCESS = 'tts.process'  # commands, daemons
    TTS_SETTINGS = 'tts.settings'
    TTS_CONFIG = 'tts.config'
    TTS_BOOTSTRAP = 'tts.bootstrap'

    _root_logger: BasicLogger = None
    _scraper_logger: BasicLogger = None

    @staticmethod
    def get_logger(logger_name: ForwardRef('Logger')) -> BasicLogger:
        if Logger._scraper_logger is None:
            Logger.init_loggers()
        logger: BasicLogger = BasicLogger.get_logger(__name__)
        return logger

    @classmethod
    def init_loggers(cls) -> None:
        cls._root_logger = BasicLogger.get_logger(__name__)
        for logger_name in Logger:
            logger: BasicLogger = cls._root_logger.getChild(logger_name)
        SCRAPER = 'tts.scraper'
        NOISY_SCRAPER = 'tts.scraper.noisy'
        OLD_SCRAPER = 'tts.old_scraper'
        TTS_ENGINE = 'tts.engine'
        TTS_PLAYER = 'tts.player'
        TTS_PROCESS = 'tts.process'  # commands, daemons
        TTS_SETTINGS = 'tts.settings'
        TTS_CONFIG = 'tts.config'
        TTS_BOOTSTRAP = 'tts.bootstrap'
