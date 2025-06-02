from __future__ import annotations  # For union operator |

import sys

from common import *

from common.logger import BasicLogger
from common.setting_constants import Transcoders

module_logger = BasicLogger.get_logger(__name__)


class BootstrapTranscoders:
    transcoder_ids: List[str] = [
        Transcoders.LAME
        ]
    '''
        Transcoders.NONE,
        Transcoders.WINDOWS,
        Transcoders.SOX,
        Transcoders.MPG123,
        Transcoders.MPG321_OE_PI,
        Transcoders.MPG321,
        Transcoders.LAME,
        Transcoders.MPLAYER]
    '''

    _initialized: bool = False
    _logger: BasicLogger = None

    @classmethod
    def init(cls) -> None:
        if not cls._initialized:
            cls.initialized = True
            if cls._logger is None:
                cls._logger = module_logger
            cls.load_transcoders()

    @classmethod
    def load_transcoders(cls):
        for transcoder_id in cls.transcoder_ids:
            cls.load_transcoder(transcoder_id)

    @classmethod
    def load_transcoder(cls, transcoder_id: str) -> None:
        try:
            if transcoder_id == Transcoders.MPLAYER:
                from converters.basic_converters import MPlayerAudioConverter
                MPlayerAudioConverter()
            elif transcoder_id == Transcoders.WINDOWS:
                from converters.basic_converters import WindowsAudioConverter
                WindowsAudioConverter()
            elif transcoder_id == Transcoders.SOX:
                from converters.basic_converters import AplayAudioConverter
                AplayAudioConverter()
            # elif transcoder_id == Transcoders.RECITE_ID:
            elif transcoder_id == Transcoders.MPG321:
                from converters.basic_converters import MPG321AudioConverter
                MPG321AudioConverter()
            elif transcoder_id == Transcoders.LAME:
                from converters.basic_converters import LameAudioConverter
                LameAudioConverter()
            elif transcoder_id == Transcoders.MPG123:
                from converters.basic_converters import Mpg123AudioConverter
                Mpg123AudioConverter()
            elif transcoder_id == Transcoders.MPG321_OE_PI:
                from converters.basic_converters import Mpg321OEPiAudioConverter
                Mpg321OEPiAudioConverter()
            elif transcoder_id == Transcoders.INTERNAL:
                pass
            elif transcoder_id == Transcoders.NONE:
                pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')


BootstrapTranscoders.init()
