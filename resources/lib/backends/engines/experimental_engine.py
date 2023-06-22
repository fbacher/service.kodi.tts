# -*- coding: utf-8 -*-
import io
import os
import re
import sys
from datetime import timedelta
from enum import Enum
from time import time
import pathlib
import subprocess

from typing.io import IO

from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.base import SimpleTTSBackend
from backends.engines.experimental_engine_settings import ExperimentalSettings
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.setting_constants import Backends, Genders, Languages, Mode
from common.settings import Settings
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)
PUNCTUATION_PATTERN = re.compile(r'([.,:])', re.DOTALL)


class WaveToMpg3Encoder(Enum):
    FFMPEG = 0
    MPLAYER = 1
    LAME = 2


class ExperimentalTTSBackend(SimpleTTSBackend):

    ID: str = Backends.EXPERIMENTAL_ENGINE_ID
    backend_id = Backends.EXPERIMENTAL_ENGINE_ID
    engine_id = Backends.EXPERIMENTAL_ENGINE_ID
    service_ID: str = Services.EXPERIMENTAL_ENGINE_ID
    service_TYPE: str = ServiceType.ENGINE

    MAXIMUM_PHRASE_LENGTH: Final[int] = 200
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        self.process = None
        self.stop_processing = False
        BaseServices().register(self)

    def init(self) -> None:
        clz = type(self)
        if self.initialized:
            return
        super().init()
        self.update()

    @staticmethod
    def isSupportedOnPlatform() -> bool:
        return (SystemQueries.isLinux() or SystemQueries.isWindows()
                or SystemQueries.isOSX())

    @staticmethod
    def isInstalled() -> bool:
        installed: bool = False
        if ExperimentalTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def getMode(self) -> int:
        clz = type(self)
        # built-in player not supported
        default_player: str = clz.get_setting_default(SettingsProperties.PLAYER)
        player: str = clz.get_player_setting(default_player)
        if clz.getSetting(SettingsProperties.PIPE):
            return Mode.PIPE
        else:
            return Mode.FILEOUT

    def runCommand(self, text_to_voice: str, dummy) -> bool:
        clz = type(self)
        # If caching disabled, then exists is always false. file_path
        # always contains path to cached file, or path where to download to

        self.stop_processing = False
        file_path: str | None
        exists: bool
        voiced_text: bytes
        file_path, exists = self.get_path_to_voice_file(text_to_voice,
                                                        use_cache=self.is_use_cache())
        self._logger.debug(f'file_path: {file_path} exists: {exists}')
        if not file_path or len(file_path) == 0:
            file_path = None

        if not exists:
            file_path, exists = self.generate_speech(
                    text_to_voice, file_path)

        if self.stop_processing:
            if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                clz._logger.debug_extra_verbose('stop_processing')
            return False

        if exists:
            self.setPlayer(clz.get_player_setting())

        return exists

    def runCommandAndPipe(self, text_to_voice: str):
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        self.stop_processing = False
        audio_pipe = None
        voice_file: str | None
        exists: bool
        byte_stream: io.BinaryIO
        voice_file, exists = self.get_path_to_voice_file(text_to_voice,
                                                         clz.is_use_cache())
        if not voice_file or len(voice_file) == 0:
            voice_file = None

        if not exists:
            voice_file, _ = self.generate_speech(
                    text_to_voice, voice_file)
        try:
            byte_stream = io.open(voice_file, 'rb')
        except Exception:
            clz._logger.exception('')
            byte_stream = None

        # the following a geared towards Mplayer. Assumption is that only adjust
        # volume in player, other settings in engine.

        # volume_db: float = clz.get_volume_db()  # -12 .. 12
        self.setPlayer(clz.get_player_setting())
        return byte_stream

    def generate_speech(self, text_to_voice: str,
                        voice_file_path: str | None) -> (str | None, bool):
        # If voice_file_path is None, then don't save voiced text to it,
        # just return the voiced text as bytes

        clz = type(self)
        # if len(text_to_voice) > 250:
        #    clz._logger.error('Text longer than 250. len:', len(text_to_voice),
        #                             text_to_voice)
        #    return None, None
        clz._logger.debug_extra_verbose(f'Text len: {len(text_to_voice)} {text_to_voice}')

        failed: bool = False
        save_copy_of_text: bool = True
        save_to_file: bool = voice_file_path is not None
        '''
        key:str  = clz.getAPIKey()
        lang: str = clz.getLanguage()
        gender: str = clz.getGender()
        pitch: str = clz.getPitch_str()    # hard coded. Let player decide
        speed: str = clz.getApiSpeed()     # Also hard coded value for 1x speed
        volume: str = clz.getEngineVolume_str()
        service: str = clz.getVoice()
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(
                    f'text: {text_to_voice} lang: {lang} gender: {gender} pitch {pitch} '
                    f'speed: {speed} volume: {volume} service: {service}')
        api_volume: str = volume  # volume
        api_speed = speed
        api_pitch: str = pitch
        params: Dict[str, str] = {
            "key": key,
            # "t": text_to_voice,
            "tl": lang,
            "pitch": api_pitch,
            "rate": api_speed,
            "vol": api_volume,
            "sv": service,
            "vn": '',
            "gender": gender
        }
        '''
        rc: int = 0
        cache_file: IO[io.BufferedWriter] = None
        if save_to_file:
            # This engine only writes to file it creates
            rc, cache_file = VoiceCache.create_sound_file(voice_file_path,
                                                          create_dir_only=True)
            if rc != 0 or cache_file is None:
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(f'Failed to create cache file {cache_file}')
                return None, False

        aggregate_voiced_bytes: bytes = b''
        if not self.stop_processing:
            try:
                # Should only get here if voiced file (.wav, .mp3, etc.) was NOT
                # found. We might see a pre-existing .txt file which means that
                # the download failed. To prevent multiple downloads, wait a day
                # before retrying the download.

                failing_voice_text_file: str | None = None  # None when save_to_file False
                if save_to_file:
                    failing_voice_text_file = voice_file_path + '.txt'
                    if os.path.isfile(failing_voice_text_file):
                        expiration_time: float = time() - timedelta(hours=24).total_seconds()
                        if (os.stat(failing_voice_text_file).st_mtime <
                                expiration_time):
                            clz._logger.debug(f'os.remove(voice_file_path)')
                        else:
                            clz._logger.debug_extra_verbose(
                                    'Previous attempt to get speech failed. Skipping.')
                            return None, False

                    if save_copy_of_text:
                        path: str
                        file_type: str
                        copy_text_file_path, file_type = os.path.splitext(voice_file_path)
                        copy_text_file_path = f'{copy_text_file_path}.txt'
                        try:
                            if os.path.isfile(copy_text_file_path):
                                os.unlink(copy_text_file_path)

                            with open(copy_text_file_path, 'wt') as f:
                                f.write(text_to_voice)
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        f'Failed to save voiced text file: '
                                        f'{copy_text_file_path} Exception: {str(e)}')
                if Settings.get_setting_bool(SettingsProperties.DELAY_VOICING,
                                             clz.service_ID, ignore_cache=False,
                                             default_value=True):  # do conversion off line or background
                    return voice_file_path, not failed
                text_file: str
                output_dir: pathlib.Path
                output: pathlib.Path
                rc: int = 0
                reason: str = ''
                model = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
                vocoder = 'vocoder_models/en/ljspeech/univnet'
                try:
                    subprocess.run(['tts', '--text', f'{text_to_voice}', '--model_name', model, '--vocoder_name',
                                    vocoder, '--out_path', '/tmp/tst.wav'], shell=False,
                                   check=True)
                except subprocess.CalledProcessError as e:
                    clz._logger.exception('')
                    reason = 'tts failed'
                    failed = True

                transcoder: WaveToMpg3Encoder = WaveToMpg3Encoder.LAME

                if not failed:
                    if transcoder == WaveToMpg3Encoder.MPLAYER:
                        try:
                            subprocess.run(['mplayer', '-i', '/tmp/tst.wav', '-f', 'mp3',
                                            f'{voice_file_path}'], shell=False, text=True, check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'mplayer failed'
                            failed = True
                    if transcoder == WaveToMpg3Encoder.FFMPEG:
                        try:
                            subprocess.run(['ffmpeg', '-loglevel', 'error', '-i',
                                            '/tmp/tst.wav', '-acodec', 'libmp3lame',
                                            f'{voice_file_path}'], shell=False,
                                           text=True, check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'ffmpeg failed'
                            failed = True
                    if transcoder == WaveToMpg3Encoder.LAME:
                        try:
                            subprocess.run(['lame', '/tmp/tst.wav',
                                            f'{voice_file_path}'], shell=False,
                                           text=True, check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'lame failed'
                            failed = True
                if failed and save_to_file:
                    if clz._logger.isEnabledFor(ERROR):
                        clz._logger.error(
                                f'Failed to download voice for {text_to_voice} '
                                f'reason {reason}')
                    if text_to_voice is not None and voice_file_path is not None:
                        try:
                            if os.path.isfile(failing_voice_text_file):
                                os.unlink(failing_voice_text_file)

                            with open(failing_voice_text_file, 'wt') as f:
                                f.write(text_to_voice)
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        f'Failed to save sample text to voice file: '
                                        f'{str(e)}')
                            try:
                                os.remove(failing_voice_text_file)
                            except Exception as e2:
                                pass
            except Exception as e:
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(
                            'Failed to download voice: {}'.format(str(e)))
                voice_file_path = None
                aggregate_voiced_bytes = b''
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'aggregate_voiced_bytes:'
                                      f' {len(aggregate_voiced_bytes)}')
        return voice_file_path, not failed

    @classmethod
    def create_cmdline(cls, text_to_voice: str, output_path: str,
                       sound_file_name: str) -> int:
        text_file: str
        output_dir: pathlib.Path
        output: pathlib.Path
        rc: int = 0

        model = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
        vocoder = 'vocoder_models/en/ljspeech/univnet'
        output_dir = pathlib.Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        sound_file_path =  pathlib.Path(output_dir, '/', sound_file_name)
        try:
            subprocess.run(['tts', f'{text_to_voice}', '--model_name', model, '--vocoder_name',
                            vocoder, '--out_path', '/tmp/tst.wav'], shell=True, text=True,
                           check=True)
        except subprocess.CalledProcessError:
            cls._logger.exception('')
            rc = 1
        try:
            subprocess.run(['mplayer', '-benchmark', '-vo', 'null', '-vc', 'null',
                            '-ao', f'pcm:fast:file={sound_file_path}', '/tmp/tst.wav'],
                           shell=False, text=True, check=True)
        except subprocess.CalledProcessError:
            cls._logger.exception('')
            rc = 2

        return rc


    def update(self):
        self.process = None
        self.stop_processing = False

    def close(self):
        # self._close()
        pass

    def _close(self):
        # self.stop()
        # super()._close()
        pass

    def stop(self):
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose('stop')
        self.stop_processing = True
        if not self.process:
            return
        try:
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose('terminate')
            self.process.terminate()  # Could use self.process.kill()
        except AbortException:
            reraise(*sys.exc_info())
        except:
            pass

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        return SettingsMap.is_valid_property(cls.service_ID, setting)

    '''
    @classmethod
    def getSettingNames(cls) -> List[str]:
        settingNames: List[str] = []
        for settingName in cls.settings.keys():
            settingNames.append(settingName)
    
        return settingNames
    '''

    @classmethod
    def settingList(cls, setting, *args) \
            -> List[str] | List[Tuple[str, str]] | Tuple[List[str], str] | Tuple[List[Tuple[str, str]], str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translated). Sorting/translating done
        in UI.

        :param setting:
        :param args:
        :return:
        """
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and value of closest match to current
            #
            # (Display value, setting_value), default_locale-index
            return [('US-English', 'en-US')], 'en-US'

        elif setting == SettingsProperties.GENDER:
            return [Genders.FEMALE.value]

        elif setting == SettingsProperties.VOICE:
            return [('fancy', 'only')]

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[str] = []
            # for player in cls.player_handler_class().getAvailablePlayers():
            #     player_ids.append(player.ID)
            return player_ids, default_player

    # Intercept simply for testing purposes: to disable bypass
    # of voicecache during config to avoid hammering remote
    # vender service.
    #
    # TODO: Remove on ship

    @classmethod
    def setSetting(cls, key, value):
        changed = super().setSetting(key, value)
        VoiceCache.for_debug_setting_changed()
        return changed

    @classmethod
    def negotiate_engine_config(cls, engine_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing engine to control
        """
        if cls.is_use_cache():
            return True, True, True

        return False, False, False

    @classmethod
    def getVolumeDb(cls) -> float | None:
        volume_validator: ConstraintsValidator | IValidator
        volume_validator = SettingsMap.get_validator(cls.service_ID,
                                                     property_id=SettingsProperties.VOLUME)
        volume = volume_validator.getValue()

        return None  # Find out if used

    @classmethod
    def getEngineVolume(cls) -> float:
        """
        Get the configured volume in our standard  -12db .. +12db scale converted
        to the native scale of the API (0.1 .. 1.0). The maximum volume (1.0) is equivalent
        to 0db. Since we have to use a different player AND since it almost guaranteed
        that the voiced text is cached, just set volume to fixed 1.0 and let player
        handle volume).
        """
        volume_validator: ConstraintsValidator
        volume_validator = cls.get_validator(cls.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume: float = volume_validator.getValue()
        return volume

    @classmethod
    def getEngineVolume_str(cls) -> str:
        volume_validator: ConstraintsValidator
        volume_validator = cls.get_validator(cls.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume: str = volume_validator.getUIValue()
        return volume

    @classmethod
    def getVoice(cls) -> str:
        voice = cls.getSetting(SettingsProperties.VOICE)
        if voice is None:
            lang = cls.voices_by_locale_map.get(cls.getLanguage())
            if lang is not None:
                voice = lang[0][1]
        voice = 'g2'
        return voice

    @classmethod
    def getLanguage(cls) -> str:
        language_validator: ConstraintsValidator
        language_validator = cls.get_validator(cls.service_ID,
                                               property_id=SettingsProperties.LANGUAGE)
        language: str = language_validator.getValue()
        language = 'en-US'
        return language

    @classmethod
    def getPitch(cls) -> float:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        pitch_validator: ConstraintsValidator
        pitch_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.PITCH)
        if cls.is_use_cache():
            pitch = pitch_validator.default_value
        else:
            pitch: float = pitch_validator.getValue()
        return pitch

    @classmethod
    def getPitch_str(cls) -> str:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        # TODO: Solve this differently!!!!

        pitch: float = cls.getPitch()
        return '{:.2f}'.format(pitch)

    @classmethod
    def getSpeed(cls) -> float:
        # Native ResponsiveVoice speed is 1 .. 100, with default of 50,
        # Since Responsive voice always requires a player, and caching is
        # a practical necessity, a fixed setting of 50 is used with Responsive Voice
        # and leave it to the player to adjust speed.
        #
        # Kodi TTS uses a speed of +0.25 .. 1 .. +4.0
        # 0.25 is 1/4 speed and 4.0 is 4x speed
        #
        # This speed is represented as a setting as in integer by multiplying
        # by 100.
        #
        speed_validator: ConstraintsValidator
        speed_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.SPEED)
        speed: float = speed_validator.getValue()
        # speed = float(speed_i) / 100.0
        return speed

    @classmethod
    def getApiSpeed(cls) -> str:
        speed: float = cls.getSpeed()
        # Leave it to the player to adjust speed
        return "50"

    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender

    @classmethod
    def getAPIKey(cls) -> str:
        return cls.getSetting(SettingsProperties.API_KEY)

    # All voices are empty strings
    # def setVoice(self, voice):
    #    self.voice = voice

    @staticmethod
    def available() -> bool:
        engine_output_formats: List[str]
        engine_output_formats = SoundCapabilities.get_output_formats(
                ExperimentalTTSBackend.service_ID)
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[SoundCapabilities.MP3],
                producer_formats=[])
        if len(candidates) > 0:
            return True
