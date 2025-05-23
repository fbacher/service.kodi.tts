# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |


import errno
import os
import shutil
import subprocess

from common import *
from common.constants import Constants

from common.logger import *
from common.setting_constants import Converters
from converters.iconverter import IConverter

try:
    import xbmc
except:
    xbmc = None

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)
PLAYSFX_HAS_USECACHED: bool = False


class AudioConverter(IConverter):
    """
    An Audio Converter converts audio from one format to another. It can be needed
    to bridge between a player_key and engine that don't speak the same. In this
    environment, it is more likely needed to reduce the size of .wav files for
    caching. Caching is needed for high-quality, but slow engines. Almost all
    text from Kodi is often repeated, even movie descriptions, since movie
    content does not change that often.

    Currently, all converters are also players. Having separate classes for
    conversion than for playing should simplify things a bit by making it very
    clear that all settings, etc. are for acting as a converter rather than
    player_key.

    The objective is not to alter the audio, just the format. Ideally one could
    perform the conversion with settings that would not change to volume, etc.
    """
    ID = Converters.NONE
    # name = ''

    _advanced: bool = False
    sound_file_types: List[str] = ['.wav']
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None

    def __init__(self) -> None:
        clz = type(self)

    def canSetPipe(self) -> bool:
        return False

    def pipe(self, source) -> None:
        pass

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
    sound_file_types: List[str] = [AudioType.WAV, AudioType.MP3]
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = [AudioType.WAV, AudioType.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    _available = SystemQueries.is_windows
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats,
                                            _available)

    @classmethod
    def init_class(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def __init__(self, *args, **kwargs):
        super().__init__()

        from . import winplay
        self._player = winplay
        self.audio = None
        self.event: threading.Event = threading.Event()
        self.event.clear()

    def play(self, path):
        if not os.path.text_exists(path):
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
        self._convert_process = None
        self.speed: float = 0.0
        self.volume: float | None = None
        self.active = True

    def canSetPipe(self) -> bool:
        return False

    def pipe(self, source) -> None:
        clz = type(self)
        pipe_args = self.get_pipe_args()
        MY_LOGGER.debug_v('pipeArgs: {" ".join(pipe_args)}')
        try:
            MY_LOGGER.info(f'Running command:')

            with subprocess.run(pipe_args, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.STDOUT,
                                check=True) as self._convert_process:
                try:
                    shutil.copyfileobj(source, self._convert_process.stdin)
                    # Make sure that any source process receives close from subprocess
                    source.close()
                except IOError as e:
                    if e.errno != errno.EPIPE:
                        MY_LOGGER.error('Error piping audio')
                except:
                    MY_LOGGER.error('Error piping audio')
        except subprocess.CalledProcessError:
            MY_LOGGER.error('Error piping audio')
        finally:
            # source.close()
            self._convert_process = None
        return

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
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command: Windows')
                subprocess.run(cls._availableArgs, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, text=True, shell=False,
                               encoding='utf-8', check=True, close_fds=True,
                               creationflags=subprocess.DETACHED_PROCESS)
            else:
                MY_LOGGER.info(f'Running command: Linux')
                subprocess.run(cls._availableArgs, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, text=True, shell=False,
                               encoding='utf-8', check=True, close_fds=True)
        except subprocess.CalledProcessError:
            return False
        return True


'''
class SOXAudioConverter(BaseAudioConverter):
    ID = Converters.SOX
    # name = 'SOX'
    _availableArgs = ('sox', '--version')
    _playArgs = ('play', '-q', None)
    _pipeArgs = ('play', '-q', '-')
    _speedArgs = ('tempo', '-s', None)
    _speedMultiplier: Final[float] = 0.01
    _volumeArgs = ('vol', None, 'dB')
    kill = True
    sound_file_types: List[str] = [AudioType.WAV, AudioType.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = [AudioType.WAV, AudioType.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)

    def __init__(self):
        super().__init__()
        MY_LOGGER = module_logger
                self.__class__.__name__)  # type: module_logger

    def playArgs(self, path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            args[args.index(None)] = str(self.volume)
        if self.speed:
            args.extend(self._speedArgs)
            args[args.index(None)] = self.speedArg(self.speed)
        MY_LOGGER.debug_v(f'args: {" ".join(args)}')
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


class MPlayerAudioConverter(BaseAudioConverter, BaseServices):
    """
     name = 'MPlayer'
     MPlayer supports -idle and -slave which keeps player_key from exiting
     after files played. When in slave mode, commands are read from stdin.

     To convert from wave to mpg3:
                    if transcoder == WaveToMpg3Encoder.MPLAYER:
                        try:
                            subprocess.run(['mplayer', '-i', '/tmp/tst.wav', '-f', 'mp3',
                                            f'{voice_file_path}'], shell=False, 
                                            text=True, check=True)
                        except subprocess.CalledProcessError:
                            MY_LOGGER.exception('')
                            reason = 'mplayer failed'
                            failed = True
    """
    ID = Converters.MPLAYER
    setting_id: str = Services.MPLAYER_ID
    sound_file_types: List[str] = [AudioType.WAV, AudioType.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = [AudioType.WAV, AudioType.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.TRANSCODER]
    sound_capabilities = SoundCapabilities(setting_id, _provides_services,
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
        if MY_LOGGER is None:
            MY_LOGGER = module_logger
            clz.register(self)

        self.configVolume: bool = False
        self.configSpeed: bool = False
        self.configPitch: bool = False

    def init(self):
        setting_id: str = Settings.get_service_key()
        self.configVolume, self.configSpeed, self.configPitch = \
            BackendInfoBridge.negotiate_engine_config(
                                            setting_id, self.canSetVolume(),
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
        MY_LOGGER.debug_v(f'args: {" ".join(args)}')
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
        MY_LOGGER.debug_v(f'args: {" ".join(args)}')
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
        setting_id: str = Settings.get_service_key()
        engine_constraints: Constraints = BackendInfoBridge.getBackendConstraints(
                setting_id, SettingProp.SPEED)
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


class Mpg123AudioConverter(BaseAudioConverter, BaseServices):
    ID = Converters.MPG123
    setting_id = Services.MPG123_ID
    # name = 'mpg123'
    _availableArgs = ('mpg123', '--version')
    _playArgs = ('mpg123', '-q', None)
    _pipeArgs = ('mpg123', '-q', '-')
    sound_file_types: List[str] = [AudioType.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(setting_id, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)
    _logger: BasicLogger = None

    def __init__(self) -> None:
        super().__init__()
        clz = type(self)
        if MY_LOGGER is None:
            MY_LOGGER = module_logger
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


class Mpg321AudioConverter(BaseAudioConverter):
    ID = Converters.MPG321
    # name = 'mpg321'
    _availableArgs: Tuple[str, str] = ('mpg321', '--version')
    _playArgs: Tuple[str, str, str] = ('mpg321', '-q', None)
    _pipeArgs: Tuple[str, str, str] = ('mpg321', '-q', '-')
    sound_file_types: List[str] = [AudioType.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)
    def __init__(self):
        super().__init__()
        MY_LOGGER = module_logger
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


class Mpg321OEPiAudioConverter(BaseAudioConverter):
    #
    #  Plays using ALSA
    #
    ID = Converters.MPG321_OE_PI
    # name = 'mpg321 OE Pi'

    sound_file_types: List[str] = [AudioType.MP3]
    _supported_input_formats: List[str] = sound_file_types
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)

    def __init__(self):
        super().__init__()
        MY_LOGGER = module_logger
                self.__class__.__name__)  # type: module_logger
        self._convert_process = None
        try:
            import OEPiExtras
            OEPiExtras.init()
            self.env = OEPiExtras.getEnvironment()
            self.active = True
        except ImportError:
            MY_LOGGER.debug('Could not import OEPiExtras')

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
                                            universal_newlines=True)
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
        MY_LOGGER = module_logger
        self.availablePlayers: List[Type[AudioConverter]] | None

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List['ConverterHandlerType']:
        raise Exception('Not Implemented')

    def get_player(self, player_id) -> Union[Type[AudioConverter], None]:
        raise Exception('Not Implemented')

    def setPlayer(self, preferred=None, advanced=None):
        raise Exception('Not Implemented')

    def getSpeed(self) -> float:
        speed: float = Settings.getSetting(SettingProp.SPEED, 
        Settings.get_service_key())
        return speed

    def getVolumeDb(self) -> float:
        volumeDb: float = Settings.getSetting(SettingProp.VOLUME, 
        Settings.get_service_key())
        return volumeDb

    def setSpeed(self, speed: float):
        MY_LOGGER.debug(f'setSpeed: {speed}')
        pass  # self.speed = speed

    def setVolume(self, volume: float):
        MY_LOGGER.debug(f'setVolume: {volume}')
        pass  # self.volume = volume

    def player_key(self) -> str | None:
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
        MY_LOGGER = module_logger
        self.availablePlayers: List[Type[AudioConverter]] | None = None
        clz.set_sound_dir()

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List[Type[
    ConverterHandlerType]]:
        return []

    def player_key(self) -> str | None:
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
        if Settings.getSetting(SettingProp.USE_TMPFS, None, True) and tmpfs:
            cls._logger.debug_xv(f'Using tmpfs at: {tmpfs}')
            cls.sound_dir = os.path.join(tmpfs, 'kodi_speech')
        else:
            cls.sound_dir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.text_exists(cls.sound_dir):
            os.makedirs(cls.sound_dir)


class WavAudioConverterHandler(BaseConverterHandler):
    """
    Not all engines are capable of playing the sound, or may lack some
    capabilities such as volume or the ability to change the speed of playback.
    Players are used whenever capabilities are needed which are not inherit
    in the engine, or when it is more convenient to use a player_key.

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
            cls._logger = module_logger
        self.preferred = None
        self.advanced = advanced
        self.set_sound_dir()
        cls.sound_file_base = os.path.join(cls.sound_dir, '{speech_file_name}{
        sound_file_type}')
        self._player: AudioConverter = AudioConverter()
        self.hasAdvancedPlayer: bool = False
        self._getAvailablePlayers(include_builtin=True)
        self.setPlayer(preferred, advanced)

    def get_player(self, player_id) -> Union[Type[AudioConverter], None]:
        for i in self.availablePlayers:
            if i.ID == player_id:
                return i
        return None

    def player_key(self) -> Union[Type[AudioConverter], None]:
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
        player_key = None
        if preferred:
            player_key = self.get_player(preferred)
        if player_key:
            self._player: AudioConverter = player_key()
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
        if os.path.text_exists(cls.sound_file):
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
            if os.path.text_exists(fpath):
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
    sound_file_types: List[str] = [AudioType.WAV]
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None

    def __init__(self, preferred=None, advanced=False):
        super().__init__(preferred, advanced)
        clz = type(self)
        if MY_LOGGER is None:
            MY_LOGGER = module_logger
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
        if Settings.getSetting(SettingProp.USE_TMPFS, None, True) and tmpfs:
            cls._logger.debug_xv(f'Using tmpfs at: {tmpfs}')
            cls.sound_dir = os.path.join(tmpfs, 'kodi_speech')
        else:
            cls.sound_dir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.text_exists(cls.sound_dir):
            os.makedirs(cls.sound_dir)
'''

'''

class FfmpegAudioConverter(BaseAudioConverter, BaseServices):
    """
            if transcoder == WaveToMpg3Encoder.FFMPEG:
                        try:
                            subprocess.run(['ffmpeg', '-loglevel', 'error', '-i',
                                            '/tmp/tst.wav', '-acodec', 'libmp3lame',
                                            f'{voice_file_path}'], shell=False,
                                           text=True, check=True)
                        except subprocess.CalledProcessError:
                            MY_LOGGER.exception('')
                            reason = 'ffmpeg failed'
                            failed = True
    """
    '''
