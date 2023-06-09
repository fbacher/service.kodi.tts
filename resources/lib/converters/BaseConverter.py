# -*- coding: utf-8 -*-

import errno
import os
import shutil
import subprocess

from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.backend_info_bridge import BackendInfoBridge
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from common import utils
from common.constants import Constants
from common.logger import *
from common.base_services import BaseServices
from common.setting_constants import Converters
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from common.typing import *
from converters.converter_index import ConverterIndex
from converters.iconverter import IConverter

try:
    import xbmc
except:
    xbmc = None

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)
PLAYSFX_HAS_USECACHED: bool = False


class AudioConverter(IConverter):
    """
    An Audio Converter converts audio from one format to another. It can be needed
    to bridge between a player and engine that don't speak the same. In this
    environment, it is more likely needed to reduce the size of .wav files for
    caching. Caching is needed for high-quality, but slow engines. Almost all
    text from Kodi is often repeated, even movie descriptions, since movie
    content does not change that often.

    Currently, all converters are also players. Having separate classes for
    conversion than for playing should simplify things a bit by making it very
    clear that all settings, etc. are for acting as a converter rather than
    player.

    The objective is not to alter the audio, just the format. Ideally one could
    perform the conversion with settings that would not change to volume, etc.
    """
    ID = Converters.NONE
    # name = ''

    _advanced: bool = False
    sound_file_types: List[str] = ['.wav']
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        clz.set_sound_dir()

    @classmethod
    def set_sound_dir(cls):
        tmpfs = utils.getTmpfs()
        if Settings.getSetting(SettingsProperties.USE_TEMPFS, None, True) and tmpfs:
            cls._logger.debug_extra_verbose(f'Using tmpfs at: {tmpfs}')
            cls.sound_dir = os.path.join(tmpfs, 'kodi_speech')
        else:
            cls.sound_dir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.exists(cls.sound_dir):
            os.makedirs(cls.sound_dir)

    @classmethod
    def get_tmp_path(cls, speech_file_name: str, sound_file_type: str) -> str:
        filename: str = cls.sound_file_base.format(speech_file_name, sound_file_type)
        sound_file_path: str = os.path.join(cls.sound_dir, filename)
        return sound_file_path

    def canSetSpeed(self) -> bool:
        """

        @return:
        """
        return False

    def setSpeed(self, speed: float) -> None:
        """

        @param speed:
        """
        pass

    def canSetPitch(self) -> bool:
        """

        @return:
        """
        return False

    def setPitch(self, pitch: float) -> None:
        pass

    def canSetVolume(self) -> bool:
        return False

    def setVolume(self, volume: float) -> None:
        pass

    def canSetPipe(self) -> bool:
        return False

    def pipe(self, source) -> None:
        pass

    def play(self, path: str) -> None:
        pass

    def isPlaying(self) -> bool:
        return False

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass

    @staticmethod
    def available(ext=None) -> bool:
        return False

    @classmethod
    def is_builtin(cls) -> bool:
        #
        # Is this Audio Player built-into the voice engine (i.e. espeak).
        #
        return False

'''
class WindowsAudioConverter(AudioConverter):
    ID = Converters.WINDOWS
    # name = 'Windows Internal'
    sound_file_types: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    _available = SystemQueries.is_windows
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats,
                                            _available)

    @classmethod
    def init_class(cls):
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)

    def __init__(self, *args, **kwargs):
        super().__init__()

        from . import winplay
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


class SubprocessAudioConverter(AudioConverter):
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
        clz._logger = module_logger.getChild(
                self.__class__.__name__)
        self._wavProcess = None
        self.speed: float = 0.0
        self.volume: float | None = None
        self.active = True

    def speedArg(self, speed: float) -> str:
        self._logger.debug(f'speedArg speed: {speed} multiplier: {self._speedMultiplier}')
        return f'{(speed * self._speedMultiplier):.2f}'

    def baseArgs(self, path: str) -> List[str]:
        args = []
        args.extend(self._playArgs)
        args[args.index(None)] = path
        return args

    def playArgs(self, path: str) -> List[str]:
        clz = type(self)
        base_args: List[str] = self.baseArgs(path)
        clz._logger.debug_verbose(f'args: {" ".join(base_args)}')
        return base_args

    def get_pipe_args(self):
        clz = type(self)
        base_args = self._pipeArgs
        clz._logger.debug(f'playArgs: {self.playArgs("xxx")} pipeArgs: {self._pipeArgs}')
        return base_args

    def canSetPipe(self) -> bool:
        return bool(self._pipeArgs)

    def pipe(self, source):
        clz = type(self)
        pipe_args = self.get_pipe_args()
        clz._logger.debug_verbose('pipeArgs: {" ".join(pipe_args)}')

        with subprocess.Popen(pipe_args, stdin=subprocess.PIPE,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.STDOUT) as self._wavProcess:
            try:
                shutil.copyfileobj(source, self._wavProcess.stdin)
            except IOError as e:
                if e.errno != errno.EPIPE:
                    self._logger.error('Error piping audio', hide_tb=True)
            except:
                self._logger.error('Error piping audio', hide_tb=True)

            finally:
                source.close()

        self._wavProcess = None

    def getSpeed(self) -> float:
        speed: float | None = \
            Settings.getSetting(SettingsProperties.SPEED, Settings.get_engine_id())
        self.setSpeed(speed)
        return speed

    def getVolumeDb(self) -> float:
        volumeDb: float | None = \
            Settings.getSetting(SettingsProperties.VOLUME, Settings.get_engine_id())
        self.setVolume(volumeDb)
        return volumeDb

    def setSpeed(self, speed: float):
        clz = type(self)
        clz._logger.debug(f'setSpeed: {speed}')
        self.speed = speed

    def setVolume(self, volume: float):
        self._logger.debug(f'setVolume: {volume}')
        self.volume = volume

    def play(self, path: str):
        clz = type(self)
        args = self.playArgs(path)
        clz._logger.debug_verbose(f'args: {" ".join(args)}')
        with subprocess.Popen(args, stdout=(open(os.path.devnull, 'w')),
                              stderr=subprocess.STDOUT) as self._wavProcess:
            pass

        self._wavProcess = None

    def isPlaying(self) -> bool:
        return self._wavProcess and self._wavProcess.poll() is None

    def stop(self):
        if not self._wavProcess or self._wavProcess.poll():
            return
        try:
            if self.kill:
                self._wavProcess.kill()
            else:
                self._wavProcess.terminate()
        except:
            pass
        finally:
            self._wavProcess = None

    def close(self):
        self.active = False
        if not self._wavProcess or self._wavProcess.poll():
            return
        try:
            self._wavProcess.kill()
        except:
            pass
        finally:
            self._wavProcess = None

    @classmethod
    def available(cls, ext=None) -> bool:
        try:
            subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True)
        except:
            return False
        return True


class SOXAudioConverter(SubprocessAudioConverter):
    ID = Converters.SOX
    # name = 'SOX'
    _availableArgs = ('sox', '--version')
    _playArgs = ('play', '-q', None)
    _pipeArgs = ('play', '-q', '-')
    _speedArgs = ('tempo', '-s', None)
    _speedMultiplier: Final[float] = 0.01
    _volumeArgs = ('vol', None, 'dB')
    kill = True
    sound_file_types: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
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
                                stderr=subprocess.STDOUT, universal_newlines=True)
        except:
            return False
        return True

    @staticmethod
    def register():
        ConverterIndex.register(SOXAudioConverter.ID, SOXAudioConverter)


class MPlayerAudioConverter(SubprocessAudioConverter, BaseServices):
    """
     name = 'MPlayer'
     MPlayer supports -idle and -slave which keeps player from exiting
     after files played. When in slave mode, commands are read from stdin.
    """
    ID = Converters.MPLAYER
    service_ID: str = Services.MPLAYER_ID
    sound_file_types: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.CONVERTER]
    sound_capabilities = SoundCapabilities(service_ID, _provides_services,
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
            clz._logger = module_logger.getChild(self.__class__.__name__)
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
        engine_speed: float = engine_constraints.currentValue()
        # Kodi TTS speed representation is 0.25 .. 4.0
        # 0.25 = 1/4 speed, 4.0 is 4x speed
        player_speed: float = engine_speed
        return float(player_speed)

    @staticmethod
    def register():
        ConverterIndex.register(MPlayerAudioConverter.ID, MPlayerAudioConverter)


class Mpg123AudioConverter(SubprocessAudioConverter, BaseServices):
    ID = Converters.MPG123
    service_ID = Services.MPG123_ID
    # name = 'mpg123'
    _availableArgs = ('mpg123', '--version')
    _playArgs = ('mpg123', '-q', None)
    _pipeArgs = ('mpg123', '-q', '-')
    sound_file_types: List[str] = [SoundCapabilities.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(service_ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)
    _logger: BasicLogger = None

    def __init__(self) -> None:
        super().__init__()
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(self.__class__.__name__)
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


class Mpg321AudioConverter(SubprocessAudioConverter):
    ID = Converters.MPG321
    # name = 'mpg321'
    _availableArgs: Tuple[str, str] = ('mpg321', '--version')
    _playArgs: Tuple[str, str, str] = ('mpg321', '-q', None)
    _pipeArgs: Tuple[str, str, str] = ('mpg321', '-q', '-')
    sound_file_types: List[str] = [SoundCapabilities.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)
    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
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


class Mpg321OEPiAudioConverter(SubprocessAudioConverter):
    #
    #  Plays using ALSA
    #
    ID = Converters.MPG321_OE_PI
    # name = 'mpg321 OE Pi'

    sound_file_types: List[str] = [SoundCapabilities.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
                self.__class__.__name__)  # type: module_logger
        self._wavProcess = None
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
        self._wavProcess = subprocess.Popen('mpg321 - --wav - | aplay',
                                            stdin=subprocess.PIPE,
                                            stdout=(
                                                open(os.path.devnull, 'w')),
                                            stderr=subprocess.STDOUT,
                                            env=self.env, shell=True,
                                            universal_newlines=True)
        try:
            shutil.copyfileobj(source, self._wavProcess.stdin)
        except IOError as e:
            if e.errno != errno.EPIPE:
                module_logger.error('Error piping audio', hide_tb=True)
        except:
            module_logger.error('Error piping audio', hide_tb=True)
        source.close()
        self._wavProcess.stdin.close()
        while self._wavProcess.poll() is None and self.active:
            utils.sleep(10)

    def play(self, path):  # Plays using ALSA
        self._wavProcess = subprocess.Popen(f'mpg321 --wav - "{path}" | aplay',
                                            stdout=(
                                                open(os.path.devnull, 'w')),
                                            stderr=subprocess.STDOUT, env=self.env,
                                            shell=True, universal_newlines=True)

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


class ConverterHandlerType:
    ID: None
    _advanced: bool = None
    sound_file_types: List[str] = ['.wav']
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger

    def __init__(self):
        clz = type(self)
        self.hasAdvancedPlayer: bool
        clz._logger = module_logger.getChild(self.__class__.__name__)
        self.availablePlayers: List[Type[AudioConverter]] | None

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List['ConverterHandlerType']:
        raise Exception('Not Implemented')

    def get_player(self, player_id) -> Union[Type[AudioConverter], None]:
        raise Exception('Not Implemented')

    def setPlayer(self, preferred=None, advanced=None):
        raise Exception('Not Implemented')

    def getSpeed(self) -> float:
        speed: float = Settings.getSetting(SettingsProperties.SPEED, Settings.get_engine_id())
        return speed

    def getVolumeDb(self) -> float:
        volumeDb: float = Settings.getSetting(SettingsProperties.VOLUME, Settings.get_engine_id())
        return volumeDb

    def setSpeed(self, speed: float):
        self._logger.debug(f'setSpeed: {speed}')
        pass  # self.speed = speed

    def setVolume(self, volume: float):
        self._logger.debug(f'setVolume: {volume}')
        pass  # self.volume = volume

    def player(self) -> str | None:
        raise Exception('Not Implemented')

    def canSetPipe(self) -> bool:
        raise Exception('Not Implemented')

    def pipeAudio(self, source):
        raise Exception('Not Implemented')

    @classmethod
    def get_sound_file(cls, text: str, sound_file_types: List[str] | None = None,
                   use_cache: bool = False) -> str:
        raise Exception('Not Implemented')

    @classmethod
    def set_sound_dir(cls):
        raise Exception('Not Implemented')

    def play(self):
        raise Exception('Not Implemented')

    def isPlaying(self):
        raise Exception('Not Implemented')

    def stop(self):
        raise Exception('Not Implemented')

    def close(self):
        raise Exception('Not Implemented')


class BaseConverterHandler(ConverterHandlerType):
    sound_file_types: List[str] = ['.wav']
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None

    def __init__(self):
        super().__init__()
        clz = type(self)
        clz._logger = module_logger.getChild(self.__class__.__name__)
        self.availablePlayers: List[Type[AudioConverter]] | None = None
        clz.set_sound_dir()

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List[Type[ConverterHandlerType]]:
        return []

    def player(self) -> str | None:
        return None

    def canSetPipe(self) -> bool:
        return False

    def pipeAudio(self, source):
        pass

    def get_sound_file(self, text: str, sound_file_types: List[str] | None = None,
                   use_cache: bool = False) -> str:
        """

        @param text:
        @param sound_file_types:
        @param use_cache:
        """
        raise Exception(
                'Not Implemented')

    def play(self):
        raise Exception('Not Implemented')

    def isPlaying(self):
        raise Exception('Not Implemented')

    def stop(self):
        raise Exception('Not Implemented')

    def close(self):
        raise Exception('Not Implemented')

    @classmethod
    def set_sound_dir(cls):
        tmpfs = utils.getTmpfs()
        if Settings.getSetting(SettingsProperties.USE_TEMPFS, None, True) and tmpfs:
            cls._logger.debug_extra_verbose(f'Using tmpfs at: {tmpfs}')
            cls.sound_dir = os.path.join(tmpfs, 'kodi_speech')
        else:
            cls.sound_dir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.exists(cls.sound_dir):
            os.makedirs(cls.sound_dir)


class WavAudioConverterHandler(BaseConverterHandler):
    """
    Not all engines are capable of playing the sound, or may lack some
    capabilities such as volume or the ability to change the speed of playback.
    Players are used whenever capabilities are needed which are not inherit
    in the engine, or when it is more convenient to use a player.

    ConverterHandlers manage a group of players with support for a particular
    sound file type (here, wave or mp3).
    """
    # players = (WindowsAudioConverter, SOXAudioConverter, MPlayerAudioConverter)
    players = (SOXAudioConverter, MPlayerAudioConverter)

    _logger: BasicLogger = None
    sound_file_types: List[str] = ['.wav']
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    sound_file: str

    def __init__(self, preferred=None, advanced=False):
        super().__init__()
        cls = type(self)
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)
        self.preferred = None
        self.advanced = advanced
        self.set_sound_dir()
        cls.sound_file_base = os.path.join(cls.sound_dir, '{speech_file_name}{sound_file_type}')
        self._player: AudioConverter = AudioConverter()
        self.hasAdvancedPlayer: bool = False
        self._getAvailablePlayers(include_builtin=True)
        self.setPlayer(preferred, advanced)

    def get_player(self, player_id) -> Union[Type[AudioConverter], None]:
        for i in self.availablePlayers:
            if i.ID == player_id:
                return i
        return None

    def player(self) -> Union[Type[AudioConverter], None]:
        return self._player and self._player.ID or None

    def canSetPipe(self) -> bool:
        return self._player.canSetPipe()

    def pipeAudio(self, source):
        return self._player.pipe(source)

    def playerAvailable(self) -> bool:
        return bool(self.availablePlayers)

    def _getAvailablePlayers(self, include_builtin=True):
        clz = type(self)
        self.availablePlayers = clz.getAvailablePlayers(
                include_builtin=include_builtin)
        for p in self.availablePlayers:
            if p._advanced:
                break

    def setPlayer(self, preferred=None, advanced=None):
        if preferred == self._player.ID or preferred == self.preferred:
            return self._player
        self.preferred = preferred
        if advanced is None:
            advanced = self.advanced
        old = self._player
        player = None
        if preferred:
            player = self.get_player(preferred)
        if player:
            self._player: AudioConverter = player()
            self._player.init()
        elif advanced and self.hasAdvancedPlayer:
            for p in self.availablePlayers:
                if p._advanced:
                    self._player = p()
                    break
        elif self.availablePlayers:
            self._player = self.availablePlayers[0]()
        else:
            self._player = AudioConverter()

        if self._player and old.ID != self._player:
            type(self)._logger.info('Player: %s' % self._player.ID)
        # if not self._player.ID == Converters.SFX:
        #     load_snd_bm2835()  # For Raspberry Pi
        return self._player

    @classmethod
    def _deleteOutFile(cls):
        if os.path.exists(cls.sound_file):
            os.remove(cls.sound_file)

    @classmethod
    def get_tmp_path(cls, speech_file_name: str, sound_file_type: str) -> str:
        filename: str = cls.sound_file_base.format(speech_file_name, sound_file_type)
        sound_file_path: str = os.path.join(cls.sound_dir, filename)
        return sound_file_path

    def canSetSpeed(self):
        return self._player.canSetSpeed()

    def setSpeed(self, speed):
        pass  # return self._player.setSpeed(speed)

    def canSetVolume(self):
        return self._player.canSetVolume()

    def setVolume(self, volume):
        pass  # return self._player.setVolume(volume)

    @classmethod
    def play(cls):
        return cls._player.play(cls.sound_file)

    def canSetPitch(self):  # Is this needed, or desired?
        return self._player.canSetPitch()

    def setPitch(self, pitch):
        pass  # return self._player.setPitch(pitch)

    def isPlaying(self):
        return self._player.isPlaying()

    def stop(self):
        return self._player.stop()

    def close(self):
        for f in os.listdir(self.sound_dir):
            if f.startswith('.'):
                continue
            fpath = os.path.join(self.sound_dir, f)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except:
                    type(self)._logger.error('Error Removing File')
        return self._player.close()

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List[Type[AudioConverter]]:
        players: List[Type[AudioConverter]] = [] # cast(List[Type[AudioConverter]], [])
        for p in cls.players:
            if p.available():
                if not p.is_builtin() or include_builtin == p.is_builtin():
                    players.append(p)
        return players

    @classmethod
    def canPlay(cls):
        for p in cls.players:
            if p.available():
                return True
        return False


class MP3AudioConverterHandler(WavAudioConverterHandler):
    # players = (WindowsAudioConverter, SOXAudioConverter,

    players = (SOXAudioConverter,
               Mpg123AudioConverter, Mpg321AudioConverter, MPlayerAudioConverter)
    sound_file_types: List[str] = [SoundCapabilities.WAVE]
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None

    def __init__(self, preferred=None, advanced=False):
        super().__init__(preferred, advanced)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        clz.set_sound_dir()

    @classmethod
    def canPlay(cls):
        for p in cls.players:
            if p.available('.mp3'):
                return True
        return False

    @classmethod
    def set_sound_dir(cls):
        tmpfs = utils.getTmpfs()
        if Settings.getSetting(SettingsProperties.USE_TEMPFS, None, True) and tmpfs:
            cls._logger.debug_extra_verbose(f'Using tmpfs at: {tmpfs}')
            cls.sound_dir = os.path.join(tmpfs, 'kodi_speech')
        else:
            cls.sound_dir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.exists(cls.sound_dir):
            os.makedirs(cls.sound_dir)
