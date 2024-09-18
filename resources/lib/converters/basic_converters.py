# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import errno
import os
import shutil
import subprocess
import threading

from common import *

from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.backend_info_bridge import BackendInfoBridge
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from common import utils
from common.base_services import BaseServices
from common.logger import *
from common.setting_constants import Converters
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from common.system_queries import SystemQueries
from converters.base_converter import AudioConverter
from converters.converter_index import ConverterIndex

try:
    import xbmc
except:
    xbmc = None

module_logger: BasicLogger = BasicLogger.get_logger(__name__)
PLAYSFX_HAS_USECACHED: bool = False


class WindowsAudioConverter(AudioConverter):
    ID = Converters.WINDOWS
    service_ID = ID
    # name = 'Windows Internal'
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None
    _supported_input_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    _available = SystemQueries.is_windows
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    @classmethod
    def init_class(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def __init__(self, *args, **kwargs):
        super().__init__()
        from backends.audio import winplay
        self._player = winplay
        self.audio = None
        self.event: threading.Event = threading.Event()
        self.event.clear()

    def play(self, path):
        if not os.path.exists(path):
            type(self)._logger.info(
                    f'WindowsAudioConverter.play() - Missing sound file: {path}')
            return
        self.audio = self._player.load(path)
        self.audio.play()
        self.event.clear()
        self.event.wait(self.audio.milliseconds() / 1000.0)
        if self.event.isSet():
            self.audio.stop()
        while self.audio.isplaying():
            utils.sleep(10)
        self.audio = None

    def isPlaying(self):
        return not self.event.isSet()

    def stop(self):
        self.event.set()

    def close(self):
        self.stop()

    @staticmethod
    def available(ext=None):
        if not SystemQueries.isWindows():
            return False
        try:
            from . import winplay  # @analysis:ignore
            return True
        except:
            WindowsAudioConverter._logger.error('winplay import failed')
        return False


WindowsAudioConverter.init_class()
'''


class BaseAudioConverter(AudioConverter):
    _logger: BasicLogger = None
    _availableArgs = None
    _playArgs = None
    _speedArgs = None
    _speedMultiplier: int = 1
    _volumeArgs = None
    _volumeMultipler = 1
    _pipeArgs = None
    kill = False

    def __init__(self):
        super().__init__()
        clz = type(self)
        clz._logger = module_logger
                self.__class__.__name__)
        self._convert_process = None
        self.speed: float = 0.0
        self.volume: float | None = None
        self.active = True

    def canSetPipe(self) -> bool:
        return False

    def pipe(self, source):
        clz = type(self)
        pipe_args = self.get_pipe_args()
        clz._logger.debug_verbose('pipeArgs: {" ".join(pipe_args)}')

        with subprocess.Popen(pipe_args, stdin=subprocess.PIPE,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.STDOUT) as self._convert_process:
            try:
                shutil.copyfileobj(source, self._convert_process.stdin)
            except IOError as e:
                if e.errno != errno.EPIPE:
                    self._logger.error('Error piping audio')
            except:
                self._logger.error('Error piping audio')

            finally:
                source.close()

        self._convert_process = None

    def convert(self, convert_from: str, convert_to: str,
                input_path: str, output_path: str) -> bool:
        pass

    def stop(self):
        if not self._convert_process or self._convert_process.poll():
            return
        try:
            if self.kill:
                self._convert_process.kill()
            else:
                self._convert_process.terminate()
        except:
            pass
        finally:
            self._convert_process = None

    def close(self):
        self.active = False
        if not self._convert_process or self._convert_process.poll():
            return
        try:
            self._convert_process.kill()
        except:
            pass
        finally:
            self._convert_process = None

    @classmethod
    def available(cls, ext=None) -> bool:
        try:
            subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True)
        except:
            return False
        return True

'''


class SOXAudioConverter(AudioConverter):
    ID = Converters.SOX
    service_ID = ID
    # name = 'SOX'
    _availableArgs = ('sox', '--version')
    _playArgs = ('play', '-q', None)
    _pipeArgs = ('play', '-q', '-')
    _speedArgs = ('tempo', '-s', None)
    _speedMultiplier: Final[float] = 0.01
    _volumeArgs = ('vol', None, 'dB')
    kill = True

    _supported_input_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.CONVERTER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    def __init__(self):
        super().__init__()
        self._logger = module_logger
                self.__class__.__name__)  # type: module_logger

    def playArgs(self, path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            args[args.index(None)] = str(self.volume)
        if self.speed:
            args.extend(self._speedArgs)
            args[args.index(None)] = self.speedArg(self.speed)
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        return args

    def canSetVolume(self):
        """

        @return:
        """
        return True

    def canSetPitch(self):  # Settings implies false, but need to test
        """

        @return:
        """
        return True

    def canSetPipe(self) -> bool:
        """

        @return:
        """
        return True

    @classmethod
    def available(cls, ext=None):
        """

        @param ext:
        @return:
        """
        try:
            if ext == '.mp3':
                if '.mp3' not in subprocess.check_output(['sox', '--help'],
                                                         universal_newlines=True):
                    return False
            else:
                subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')),
                                stderr=subprocess.STDOUT, universal_newlines=True,
                                encoding='utf-8')
        except:
            return False
        return True

    @staticmethod
    def register():
        ConverterIndex.register(SOXAudioConverter.ID, SOXAudioConverter)


class MPlayerAudioConverter(AudioConverter, BaseServices):
    """
     name = 'MPlayer'
     MPlayer supports -idle and -slave which keeps player from exiting
     after files played. When in slave mode, commands are read from stdin.

     To convert from wave to mpg3:
                    if transcoder == WaveToMpg3Encoder.MPLAYER:
                        try:
                            subprocess.run(['mplayer', '-i', '/tmp/tst.wav', '-f', 'mp3',
                                            f'{voice_file_path}'], shell=False,
                                            text=True, check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'mplayer failed'
                            failed = True
    """
    ID = Converters.MPLAYER
    service_ID: str = Services.MPLAYER_ID
    service_Type: ServiceType = ServiceType.CONVERTER

    _supported_input_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.CONVERTER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _availableArgs = ('mplayer', '--help')
    _playArgs = ('mplayer', '-really-quiet', None)
    _pipeArgs = ('mplayer', '-', '-really-quiet', '-cache', '8192')
    # Mplayer supports speeds > 0:
    #  0.30 ~1/3 speed
    #  0.5 1/2 speed
    #  1   1 x speed
    #  2   2 x speed ...
    _speedArgs = 'scaletempo=scale={0}:speed=none'

    # Multiplier of 1.0 = 100% of speed (i.e. no change)
    _speedMultiplier: Final[float] = 1.0  # The base range is 3 .. 30.
    _volumeArgs = 'volume={0}'  # Volume in db -200db .. +40db Default 0
    _logger: BasicLogger = None

    def __init__(self):
        super().__init__()
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
            clz.register(self)

        self.configVolume: bool = False
        self.configSpeed: bool = False
        self.configPitch: bool = False

    def init(self):
        backend_id: str = Settings.get_engine_id()
        self.configVolume, self.configSpeed, self.configPitch = \
            BackendInfoBridge.negotiate_engine_config(
                    backend_id, self.canSetVolume(),
                    self.canSetSpeed(), self.canSetPitch())

    def playArgs(self, path: str):
        clz = type(self)
        args = self.baseArgs(path)
        #
        # None is returned if engine can not control speed, etc.
        #
        speed: float = self.getPlayerSpeed()
        volume: float = self.getVolumeDb()
        if not speed:
            self.configSpeed = False
        if not volume:
            self.configVolume = False

        if self.configSpeed or self.configVolume:
            args.append('-af')
            filters = []
            if self.configSpeed:
                filters.append(self._speedArgs.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            args.append(','.join(filters))
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        return args

    def get_pipe_args(self) -> List[str]:
        clz = type(self)
        args: List[str] = []
        args.extend(self._pipeArgs)
        speed: float = self.getPlayerSpeed()
        volume: float = self.getVolumeDb()
        if not speed:
            self.configSpeed = False
        if not volume:
            self.configVolume = False

        if self.configSpeed or self.configVolume:
            args.append('-af')
            filters = []
            if self.configSpeed:
                filters.append(self._speedArgs.format(
                        self.speedArg(speed)))
            if self.configVolume:
                filters.append(self._volumeArgs.format(volume))
            args.append(','.join(filters))
        self._logger.debug_verbose(f'args: {" ".join(args)}')
        return args

    def canSetSpeed(self) -> bool:
        return True

    def canSetVolume(self) -> bool:
        return True

    def canSetPitch(self) -> bool:
        return True

    def canSetPipe(self) -> bool:
        return True

    def getPlayerSpeed(self) -> float | None:
        backend_id: str = Settings.get_engine_id()
        engine_constraints: Constraints = BackendInfoBridge.getBackendConstraints(
                backend_id, SettingsProperties.SPEED)
        if engine_constraints is None:
            return None
        engine_speed: float = engine_constraints.currentValue(backend_id)
        # Kodi TTS speed representation is 0.25 .. 4.0
        # 0.25 = 1/4 speed, 4.0 is 4x speed
        player_speed: float = engine_speed
        return float(player_speed)

    @staticmethod
    def register():
        ConverterIndex.register(MPlayerAudioConverter.ID, MPlayerAudioConverter)


class Mpg123AudioConverter(AudioConverter, BaseServices):
    ID = Converters.MPG123
    service_ID = Services.MPG123_ID
    # name = 'mpg123'
    _availableArgs = ('mpg123', '--version')
    _playArgs = ('mpg123', '-q', None)
    _pipeArgs = ('mpg123', '-q', '-')

    _supported_input_formats: List[str] = [SoundCapabilities.MP3]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    def __init__(self) -> None:
        super().__init__()
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
            clz.register(self)

    def canSetSpeed(self) -> bool:
        return False

    def canSetVolume(self) -> bool:  # (1-100)
        return False

    def canSetPitch(self) -> bool:  # Depends upon hardware used.
        return False

    def canSetPipe(self) -> bool:  # Can read to/from pipe
        return True

    @staticmethod
    def register():
        ConverterIndex.register(Mpg123AudioConverter.ID, Mpg123AudioConverter)


class Mpg321AudioConverter(AudioConverter):
    ID = Converters.MPG321
    service_ID = ID
    # name = 'mpg321'
    _availableArgs: Tuple[str, str] = ('mpg321', '--version')
    _playArgs: Tuple[str, str, str] = ('mpg321', '-q', None)
    _pipeArgs: Tuple[str, str, str] = ('mpg321', '-q', '-')

    _supported_input_formats: List[str] = [SoundCapabilities.MP3]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    def __init__(self):
        super().__init__()
        self._logger = module_logger
                self.__class__.__name__)  # type: module_logger

    def canSetVolume(self):
        return True

    def canSetPitch(self):
        return False

    def canSetPipe(self) -> bool:  # Can read/write to pipe
        return True

    @staticmethod
    def register():
        ConverterIndex.register(Mpg321AudioConverter.ID, Mpg321AudioConverter)


class Mpg321OEPiAudioConverter(AudioConverter):
    #
    #  Plays using ALSA
    #
    ID = Converters.MPG321_OE_PI
    service_ID = ID
    # name = 'mpg321 OE Pi'

    _supported_input_formats: List[str] = [SoundCapabilities.MP3]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    def __init__(self):
        super().__init__()
        self._logger: BasicLogger = module_logger
        self._convert_process = None
        try:
            import OEPiExtras
            OEPiExtras.init()
            self.env = OEPiExtras.getEnvironment()
            self.active = True
        except ImportError:
            self._logger.debug('Could not import OEPiExtras')

    def canSetVolume(self):
        return True

    def canSetPitch(self):  # Settings implies false, but need to test
        return False

    def canSetPipe(self) -> bool:
        return True

    def pipe(self, source):  # Plays using ALSA
        self._convert_process = subprocess.Popen('mpg321 - --wav - | aplay',
                                                 stdin=subprocess.PIPE,
                                                 stdout=(
                                                     open(os.path.devnull, 'w')),
                                                 stderr=subprocess.STDOUT,
                                                 env=self.env, shell=True,
                                                 universal_newlines=True,
                                                 encoding='utf-8')
        try:
            shutil.copyfileobj(source, self._convert_process.stdin)
        except IOError as e:
            if e.errno != errno.EPIPE:
                module_logger.error('Error piping audio')
        except:
            module_logger.error('Error piping audio')
        source.close()
        self._convert_process.stdin.close()
        while self._convert_process.poll() is None and self.active:
            utils.sleep(10)

    def play(self, path):  # Plays using ALSA
        self._convert_process = subprocess.Popen(f'mpg321 --wav - "{path}" | aplay',
                                                 stdout=(
                                                     open(os.path.devnull, 'w')),
                                                 stderr=subprocess.STDOUT, env=self.env,
                                                 shell=True, universal_newlines=True,
                                                 encoding='utf-8')

    @classmethod
    def available(cls, ext=None):
        try:
            import OEPiExtras  # analysis:ignore
        except:
            return False
        return True

    @staticmethod
    def register():
        ConverterIndex.register(Mpg321OEPiAudioConverter.ID, Mpg321OEPiAudioConverter)
