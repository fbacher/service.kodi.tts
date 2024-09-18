from __future__ import annotations  # For union operator |

import sys

from common import *

from common.logger import BasicLogger
from common.setting_constants import Converters

module_logger = BasicLogger.get_logger(__name__)


class BootstrapConverters:
    converter_ids: List[str] = [
        Converters.NONE,
        Converters.WINDOWS,
        Converters.SOX,
        Converters.MPLAYER,
        Converters.MPG123,
        Converters.MPG321_OE_PI,
        Converters.MPG321,
        Converters.LAME]

    _initialized: bool = False
    _logger: BasicLogger = None

    @classmethod
    def init(cls) -> None:
        if not cls._initialized:
            cls.initialized = True
            if cls._logger is None:
                cls._logger = module_logger
            cls.load_converters()

    @classmethod
    def load_converters(cls):
        for converter_id in cls.converter_ids:
            cls.load_converter(converter_id)

    @classmethod
    def load_converter(cls, converter_id: str) -> None:
        try:
            if converter_id == Converters.MPLAYER:
                from converters.basic_converters import MPlayerAudioConverter
                MPlayerAudioConverter()
            elif converter_id == Converters.WINDOWS:
                from converters.basic_converters import WindowsAudioConverter
                WindowsAudioConverter()
            elif converter_id == Converters.SOX:
                from converters.basic_converters import AplayAudioConverter
                AplayAudioConverter()
            # elif converter_id == Converters.RECITE_ID:
            elif converter_id == Converters.MPG321:
                from converters.basic_converters import MPG321AudioConverter
                MPG321AudioConverter()
            elif converter_id == Converters.LAME:
                from converters.basic_converters import LameAudioConverter
                LameAudioConverter()
            elif converter_id == Converters.MPG123:
                from converters.basic_converters import Mpg123AudioConverter
                Mpg123AudioConverter()
            elif converter_id == Converters.MPG321_OE_PI:
                from converters.basic_converters import Mpg321OEPiAudioConverter
                Mpg321OEPiAudioConverter()
            elif converter_id == Converters.INTERNAL:
                pass
            elif converter_id == Converters.NONE:
                pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')


BootstrapConverters.init()
