# coding=utf-8
from __future__ import annotations  # For union operator |

import json
from enum import auto

import backends.pyttsx4_run_daemon as pyttsx4_daemon
from common.logger import BasicLogger

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from typing import Any, Dict

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Cmds(StrEnum):
    CMD = auto(),
    GET_PROPERTY = auto(),
    INIT = auto(),
    SAY = auto(),
    SET_PROPERTY = auto(),
    RUN_AND_WAIT = 'runAndWait'


class CmdArgument(StrEnum):
    AGE = auto(),
    ARGS = auto(),
    DEBUG = auto(),
    DRIVER_NAME = 'driverName',
    ENGINE = auto(),
    ENGINE_ID = auto(),
    GENDER = auto(),
    LANGUAGES = auto(),
    MSG_ID = auto(),
    NAME = auto(),
    PROPERTY_NAME = auto(),
    SELF = auto(),
    TEXT = auto(),
    VOICE_ID = auto(),
    VALUE = auto(),
    VOICES = auto()


class Transport:

    msg_id: int = 0
    logger: BasicLogger = None

    @classmethod
    def __class_init__(cls):
        if cls.logger is None:
            cls.logger = module_logger.getChild(cls.__name__)

    @classmethod
    def send(cls, cmd: Dict[str, Any]) -> None:
        msg: str = json.dumps(cmd)
        Pyttsx4Proxy.daemon.send_line(msg)

    @classmethod
    def get_response(cls) -> Any:
        msg: str = Pyttsx4Proxy.daemon.get_msg()
        cls.logger.debug(f'Got response: {msg}')
        response: Dict[str, Any]
        try:
            response = json.loads(msg)
        except Exception as e:
            cls.logger.exception(f'In get_response msg: {msg}')
            response = {}
        return response

    @classmethod
    def get_msg_id(cls) -> str:
        cls.msg_id += 1
        return str(cls.msg_id)


from backends.pyttsx4_proxy.proxy_impl.engine import Engine
import weakref


class Pyttsx4Proxy:
    logger: BasicLogger = None
    _activeEngines = weakref.WeakValueDictionary()
    daemon: pyttsx4_daemon = None

    def __init__(self) -> None:
        clz = type(self)
        Transport.__class_init__()
        if clz.logger is None:
            clz._start_daemon()

    @classmethod
    def init(cls, driverName=None, debug=False):
        """
        Constructs a new TTS engine instance or reuses the existing instance for
        the driver name.

        @param driverName: Name of the platform specific driver to use. If
            None, selects the default driver for the operating system.
        @type: str
        @param debug: Debugging output enabled or not
        @type debug: bool
        @return: Engine instance
        @rtype: L{engine.Engine}
        """
        if cls.logger is None:
            cls._start_daemon()

        eng = None
        try:
            eng = cls._activeEngines.get(driverName)
            if eng is None:
                eng = Engine(driverName, debug)
                cls.logger.debug(f'Got engine: {eng} driver: {driverName}')
                cls._activeEngines[driverName] = eng
        except Exception as e:
            cls.logger.exception('')
        return eng

    @classmethod
    def speak(cls, text):
        cls.logger.debug(f'Speak text: {text}')
        eng = cls.init()
        cls.logger.debug(f'Speak engine driver: {eng._driver_name}')
        eng.say(text)
        eng.runAndWait()

    @classmethod
    def _start_daemon(cls) -> pyttsx4_daemon.Pyttsx4RunDaemon:
        if cls.daemon:
            return cls.daemon

        cls.logger = module_logger.getChild(cls.__name__)
        cls.logger.debug(f'Initializing pyttsx4_daemon')
        cls.daemon = pyttsx4_daemon.Pyttsx4RunDaemon()
        cls.logger.debug(f'Starting pyttsx4_daemon')
        cls.daemon.start_service()
        cls.logger.debug(f'started pyttsx4_daemon')
        return cls.daemon
