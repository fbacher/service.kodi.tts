from __future__ import annotations  # For union operator |

import os
import sys

from backends.audio import load_snd_bm2835
from backends.audio.afplay_audio_player import AfplayPlayer
from backends.audio.aplay_audio_player import AplayAudioPlayer
from backends.audio.base_audio import AudioPlayer
from backends.audio.builtin_audio_player import BuiltInAudioPlayer
from backends.audio.i_handler import PlayerHandlerType
from backends.audio.mpg123_audio_player import Mpg123AudioPlayer
from backends.audio.mpg321_audio_player import Mpg321AudioPlayer
from backends.audio.mplayer_audio_player import MPlayerAudioPlayer
from backends.audio.paplay_audio_player import PaplayAudioPlayer
from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
from backends.audio.sound_capabilities import SoundCapabilities
from backends.audio.sox_audio_player import SOXAudioPlayer
from backends.audio.windows_audio_player import WindowsAudioPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from common import *
from common import utils
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, Players
from common.settings import Settings

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class BasePlayerHandler(PlayerHandlerType):
    ID: str = 'dummy player'
    service_ID: str = 'dummy player'
    displayName = 'MP3AudioPlayerHandler'
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None

    def __init__(self):
        super().__init__()
        clz = type(self)
        clz._logger = module_logger
        self.availablePlayers: List[Type[AudioPlayer]] | None = None
        clz.set_sound_dir()
        clz.register()

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List[Type[PlayerHandlerType]]:
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
        if Settings.getSetting(SettingsProperties.USE_TEMPFS,
                               None, True) and tmpfs:
            cls._logger.debug_xv(f'Using tmpfs at: {tmpfs}')
            cls.sound_dir = os.path.join(tmpfs, 'kodi_speech')
        else:
            cls.sound_dir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.exists(cls.sound_dir):
            os.makedirs(cls.sound_dir)

    @classmethod
    def register(cls):
        PlayerIndex.register(cls.service_ID, cls)
        BaseServices.register(cls)


class WavAudioPlayerHandler(BasePlayerHandler):
    """
    Not all engines are capable of playing the sound, or may lack some
    capabilities such as volume or the ability to change the speed of playback.
    Players are used whenever capabilities are needed which are not inherit
    in the engine, or when it is more convenient to use a player.

    PlayerHandlers manage a group of players with support for a particular
    sound file type (here, wave or mp3).
    """
    ID: str = Players.WavAudioPlayerHandler
    engine_id = Players.WavAudioPlayerHandler
    service_ID: str = Services.WavAudioPlayerHandler
    displayName = 'WaveAudioPlayerHandler'
    players = (BuiltInAudioPlayer, PlaySFXAudioPlayer, WindowsAudioPlayer,
               AfplayPlayer, SOXAudioPlayer,
               PaplayAudioPlayer, AplayAudioPlayer, MPlayerAudioPlayer
               )
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
        cls.sound_file_base = os.path.join(cls.sound_dir,
                                           '{speech_file_name}{sound_file_type}')
        self._player: AudioPlayer = AudioPlayer()
        self.hasAdvancedPlayer: bool = False
        self._getAvailablePlayers(include_builtin=True)
        self.setPlayer(preferred, advanced)
        cls.register()

    def get_player(self, player_id) -> Union[Type[AudioPlayer], None]:
        for i in self.availablePlayers:
            if i.ID == player_id:
                return i
        return None

    def player(self) -> Union[Type[AudioPlayer], None]:
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
                # TODO: Delete, or move this statement (from original)
                self.hasAdvancedPlayer = True

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
            self._player: AudioPlayer = player()
            self._player.init()
        elif advanced and self.hasAdvancedPlayer:
            for p in self.availablePlayers:
                if p._advanced:
                    self._player = p()
                    break
        elif self.availablePlayers:
            self._player = self.availablePlayers[0]()
        else:
            self._player = AudioPlayer()

        if self._player and old.ID != self._player:
            type(self)._logger.info('Player: %s' % self._player.ID)
        if not self._player.ID == Players.SFX:
            load_snd_bm2835()  # For Raspberry Pi
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
                except AbortException:
                    reraise(*sys.exc_info())
                except:
                    type(self)._logger.error('Error Removing File')
        return self._player.close()

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List[Type[AudioPlayer]]:
        players: List[Type[AudioPlayer]] = []  # cast(List[Type[AudioPlayer]], [])
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


class MP3AudioPlayerHandler(WavAudioPlayerHandler):
    ID: str = Players.MP3AudioPlayerHandler
    engine_id = Players.MP3AudioPlayerHandler
    service_ID: str = Services.MP3AudioPlayerHandler
    displayName = 'MP3AudioPlayerHandler'
    players = (WindowsAudioPlayer, AfplayPlayer, SOXAudioPlayer,
               Mpg123AudioPlayer, Mpg321AudioPlayer, MPlayerAudioPlayer)
    sound_file_types: List[str] = [AudioType.WAV]
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None

    def __init__(self, preferred=None, advanced=False):
        super().__init__(preferred, advanced)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
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
        if Settings.getSetting(SettingsProperties.USE_TEMPFS, None,
                               True) and tmpfs:
            cls._logger.debug_xv(f'Using tmpfs at: {tmpfs}')
            cls.sound_dir = os.path.join(tmpfs, 'kodi_speech')
        else:
            cls.sound_dir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.exists(cls.sound_dir):
            os.makedirs(cls.sound_dir)


class BuiltInAudioPlayerHandler(BasePlayerHandler):
    ID: str = Players.BuiltInAudioPlayerHandler
    engine_id = Players.BuiltInAudioPlayerHandler
    service_ID: str = Services.BuiltInAudioPlayerHandler
    displayName = 'BuiltInAudioPlayerHandler'

    def __init__(self, base_handler: BasePlayerHandler = WavAudioPlayerHandler):
        super().__init__()
        self.base_handler = base_handler
