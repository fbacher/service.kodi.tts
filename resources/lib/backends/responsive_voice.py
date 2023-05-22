# -*- coding: utf-8 -*-
import io
import os
import re
from datetime import timedelta
from time import time

import requests
import xbmc

from backends.audio import (BasePlayerHandler, MP3AudioPlayerHandler,
                            SoundCapabilities, WavAudioPlayerHandler)
from backends.audio.sound_capabilties import ServiceType
from backends.base import Constraints, SimpleTTSBackendBase
from cache.voicecache import VoiceCache
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.setting_constants import Backends, Genders, Languages, Players
from common.settings import Settings
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)
PUNCTUATION_PATTERN = re.compile(r'([.,:])', re.DOTALL)


class ResponsiveVoiceTTSBackend(SimpleTTSBackendBase):
    """

    """
    # Only returns .mp3 files
    ID: str = Backends.RESPONSIVE_VOICE_ID
    backend_id = Backends.RESPONSIVE_VOICE_ID
    displayName = 'ResponsiveVoice'
    player_handler_class: Type[BasePlayerHandler] = WavAudioPlayerHandler
    pitchConstraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                Settings.PITCH)
    volumeConstraints: Constraints = Constraints(-12, 8, 12, True, True, 1.0,
                                                 Settings.VOLUME, midpoint=0)

    # Special Conversion constraint due to max native range is more or less
    # equivalent to 0db. See note in getEngineVolume

    volumeConversionConstraints: Constraints = Constraints(minimum=0.1, default=1.0,
                                                           maximum=2.0, integer=False,
                                                           decibels=False,
                                                           scale=1.0,
                                                           property_name=Settings.VOLUME,
                                                           midpoint=1,
                                                           increment=0.1)
    #  Note that default native volume is at max. Prefer to use external
    #  player for volume.
    volumeNativeConstraints = Constraints(1, 10, 10, False, True, scale=0.1)

    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    _sound_capabilities = SoundCapabilities(ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)

    RESPONSIVE_VOICE_URL = "http://responsivevoice.org/responsivevoice/getvoice.php"
    MAXIMUM_PHRASE_LENGTH = 200

    settings: Dict[str, str | int | bool] = {
        Settings.API_KEY: None,
        Settings.GENDER: 'female',
        Settings.LANGUAGE: 'en-US',
        Settings.VOICE: 'g1',
        Settings.PIPE: False,
        Settings.PITCH: 50,
        Settings.PLAYER: Players.MPLAYER,
        Settings.SPEED: 50,
        Settings.VOLUME: 8,
        Settings.CACHE_SPEECH: True,
        Settings.PLAYER_SPEED: 50,
        Settings.PLAYER_PITCH: 50,
        Settings.PLAYER_VOLUME: 8
    }
    supported_settings: Dict[str, str | int | bool] = settings

    # The Responsive Voice service was designed to provide text to speech in
    # a browser environment. Responsive Voice can perform the speech generation
    # directly from a remote server, or it can use an O/S supplied speech
    # engine found on Windows, MacOs, iOS, etc. In our case we only use the
    # non-natively produced speech generation.
    #
    # The open-source API that is used defines a large list of voices in
    # voice.py. It specifies parameters that don't appear to do anything,
    # at least for the free voices from Responsive Voice. Further, the
    # class names and parameters specify genders, which are largely incorrect.
    # The most important things that determine the voice are the lang (locale)
    # and the service (blank, g1, g2, g3, although others likely exist). There
    # is little pattern to the service and what it means. The parameters
    # rate, volume, speed, pitch have the expected effect, but gender appears
    # to have no effect for the calls tried. Still, instead of abandoning the
    # classes defined in voice.py and defining my own, the code continues to
    # reference them in part with the idea that they may prove more useful
    # later.
    #
    # In most cases the only difference between several voices appears to
    # be the pitch or speed.

    VOICE_1: str = Messages.get_msg(Messages.VOICE_1)
    VOICE_2: str = Messages.get_msg(Messages.VOICE_2)
    VOICE_3: str = Messages.get_msg(Messages.VOICE_3)

    voices_by_locale_map: Dict[str, Tuple[str, str, str]] = {
        Languages.LOCALE_AF: ((VOICE_1, "g1", Genders.MALE),
                              (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_AF_ZA: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_AR_SA: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_BS: ((VOICE_1, "", Genders.MALE),
                              (VOICE_2, "g1", Genders.MALE),
                              (VOICE_3, "g2", Genders.MALE)),
        Languages.LOCALE_CA: (VOICE_1, "", Genders.MALE),
        Languages.LOCALE_CA_ES: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_CS: ((VOICE_1, "", Genders.FEMALE),
                              (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_CY: ((VOICE_1, "g1", Genders.MALE),
                              (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_DA_DK: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_DE_DE: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EL_GR: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_AU: ((VOICE_1, "", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_GB: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_IE: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_IN: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2",  Genders.FEMALE)),
        Languages.LOCALE_EN_US: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_ZA: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EO: ((VOICE_1, "g1", Genders.MALE),
                              (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_ES_ES: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ES: ((VOICE_1, "", Genders.FEMALE),
                              (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ES_MX: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ES_US: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FI_FI: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FR_BE: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FR_FR: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FR_CA: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FR: ((VOICE_1, "g1", Genders.FEMALE),
                              (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_HI: ((VOICE_1, "g1", Genders.FEMALE),
                              (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_HI_IN: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_HR_HR: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_HU_HU: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_HY_AM: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_ID_ID: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_IS_IS: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_IT_IT: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_JA_JP: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_KO_KR: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_LA: ((VOICE_1, "g1", Genders.MALE),
                              (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_LV_LV: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_NB_NO: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_NL_BE: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_NL_NL: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_NO_NO: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_PL_PL: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_PT_BR: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_PT_PT: ((VOICE_1, "g1", Genders.UNKNOWN),
                                 (VOICE_2, "g2", Genders.UNKNOWN)),
        Languages.LOCALE_RO_RO: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_RU_RU: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_SK_SK: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_SQ_AL: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCAL_SR_ME: ((VOICE_1, "g1", Genders.MALE),
                                (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_SR_RS: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_SW_KE: ((VOICE_1, "g1", Genders.MALE),
                                 (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_TA: ((VOICE_1, "g1", Genders.UNKNOWN),
                              (VOICE_2, "g2", Genders.UNKNOWN)),
        Languages.LOCALE_TH_TH: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_TR_TR: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_VI_VN: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ZH_CN: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ZH_HK: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ZH_TW: ((VOICE_1, "g1", Genders.FEMALE),
                                 (VOICE_2, "g2", Genders.FEMALE))
    }
    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
        self.process = None
        self.stop_processing = False

        clz.constraints[Settings.SPEED] = clz.ttsSpeedConstraints
        clz.constraints[Settings.PITCH] = clz.pitchConstraints
        clz.constraints[Settings.VOLUME] = clz.volumeConstraints

        clz.settings[Settings.API_KEY] = None,
        clz.settings[Settings.GENDER] = 'female',
        clz.settings[Settings.LANGUAGE] = 'en-US',
        clz.settings[Settings.VOICE] = 'g1',
        clz.settings[Settings.PIPE] = False,
        clz.settings[Settings.SPEED] = clz.ttsSpeedConstraints.default
        clz.settings[Settings.PITCH] = clz.ttsPitchConstraints.default
        clz.settings[Settings.VOLUME] = clz.ttsVolumeConstraints.default

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
        if ResponsiveVoiceTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def getMode(self) -> int:
        clz = type(self)
        # built-in player not supported
        default_player: str = clz.get_setting_default(Settings.PLAYER)
        player: str = clz.get_player_setting(default_player)
        if clz.getSetting(Settings.PIPE):
            return SimpleTTSBackendBase.PIPE
        else:
            return SimpleTTSBackendBase.WAVOUT

    def runCommand(self, text_to_voice: str, dummy):
        clz = type(self)
        # If caching disabled, then exists is always false. file_path
        # always contains path to cached file, or path where to download to

        self.stop_processing = False
        file_path: Any
        exists: bool
        voiced_text: bytes
        file_path, exists, voiced_text = self.get_path_to_voice_file(text_to_voice,
                                                        use_cache=self.is_use_cache())
        self._logger.debug(f'file_path: {file_path} exists: {exists}')
        if not exists:
            # Note that when caching, some audio settings are fixed for the engine
            # and passed on to the player. See the note below "if the audio exists..."
            file_path, byte_stream = self.download_speech(
                text_to_voice, file_path)
            if byte_stream != b'' and not self.stop_processing:
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)

                    with open(file_path, "wb") as f:
                        f.write(byte_stream)
                    exists = True
                except Exception as e:
                    if clz._logger.isEnabledFor(ERROR):
                        clz._logger.error(
                            'Failed to download voice file: {}'.format(str(e)))
                    try:
                        os.remove(file_path)
                    except Exception as e2:
                        pass

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
        byte_stream: bytes
        voice_file, exists, byte_stream = self.get_path_to_voice_file(text_to_voice,
                                                                      clz.is_use_cache())
        if not voice_file or len(voice_file) == 0:
            voice_file = None
        if len(byte_stream) == 0:
            byte_stream = None

        if byte_stream is None:
            voice_file, byte_stream = self.download_speech(
                text_to_voice, voice_file)
        if byte_stream is not None:
            audio_pipe = io.BytesIO(byte_stream)

        # the following a geared towards Mplayer. Assumption is that only adjust
        # volume in player, other settings in engine.

        # volume_db: float = clz.get_volume_db()  # -12 .. 12
        self.setPlayer(clz.get_player_setting())
        return audio_pipe

    def download_speech(self, text_to_voice: str,
                        voice_file_path: str | None) -> (str | None, bytes):
        # If voice_file_path is None, then don't save voiced text to it,
        # just return the voiced text as bytes

        clz = type(self)
        # if len(text_to_voice) > 250:
        #    clz._logger.error('Text longer than 250. len:', len(text_to_voice),
        #                             text_to_voice)
        #    return None, None
        clz._logger.debug_extra_verbose(f'Text len: {len(text_to_voice)} {text_to_voice}')

        save_to_file: bool = voice_file_path is not None
        key:str  = clz.getAPIKey()
        lang: str = clz.getLanguage()
        gender: str = clz.getGender()
        pitch: str = clz.getPitch_str()    # hard coded. Let player decide
        speed: str = clz.getApiSpeed()     # Also hard coded value for 1x speed
        volume: str = clz.getEngineVolume_str()
        service: str = clz.getVoice()
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(
                'text: {} lang: {} gender: {} pitch {} speed: {} volume: {} service: {}'
                .format(text_to_voice, lang, gender, pitch, speed, volume, service))
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
                            return None, None

                # The service will not voice text which is too long.

                phrases: List[str] = self.split_into_phrases(text_to_voice)
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'phrases len: {len(phrases)}')
                voiced_bytes: [bytes] = []
                failed: bool = False
                phrase: str = ''
                r = None
                while len(phrases) > 0:
                    phrase = phrases.pop(0)
                    if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                        clz._logger.debug_verbose(f'phrase: {phrase}'
                                                  f' length: {len(phrase)} api_key: {params["key"]}')
                    params['t'] = phrase
                    r = requests.get(clz.RESPONSIVE_VOICE_URL, params=params,
                                     timeout=10.0)
                    if r is None or r.status_code != 200:
                        failed = True
                        break
                    else:
                        voiced_bytes.append(r.content)
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_extra_verbose(
                                f'Request status: {r.status_code}'
                                f' elapsed: {r.elapsed}'
                                f' content len: {len(r.content)}'
                                f' voiced_bytes len: {len(voiced_bytes)}')

                if failed and save_to_file:
                    if clz._logger.isEnabledFor(ERROR):
                        clz._logger.error(
                            'Failed to download voice for {} status: {:d} reason {}'
                            .format(phrase, r.status_code, r.reason))
                    if text_to_voice is not None and voice_file_path is not None:
                        try:
                            if os.path.isfile(failing_voice_text_file):
                                os.unlink(failing_voice_text_file)

                            with open(failing_voice_text_file, 'wt') as f:
                                f.write(text_to_voice)
                                f.write(f'\nPhrase: {phrase}')
                            exists = True
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                    f'Failed to save sample text to voice file: {str(e)}')
                            try:
                                os.remove(failing_voice_text_file)
                            except Exception as e2:
                                pass
                elif not self.stop_processing:
                    bad_file = False
                    magic = b'<!DOCTYPE'
                    if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                        clz._logger.debug_verbose(f'voiced_bytes: {len(voiced_bytes)}')

                    voiced_text: bytes
                    for voiced_text in voiced_bytes:
                        if voiced_text[0:len(magic)] == magic:
                            bad_file = True
                        if len(voiced_text) < 2048:
                            bad_file = True
                        aggregate_voiced_bytes += voiced_text
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'voiced_text: {len(voiced_text)}'
                                                      f' aggregate: {len(aggregate_voiced_bytes)}'
                                                      f' bad: {bad_file}')

                    if bad_file:
                        if clz._logger.isEnabledFor(ERROR):
                            clz._logger.error('Response not valid sound file')
                        aggregate_voiced_bytes = b''

                    if save_to_file and aggregate_voiced_bytes != b'':
                        try:
                            if os.path.isfile(voice_file_path):
                                os.unlink(voice_file_path)

                            with open(voice_file_path, "wb") as f:
                                f.write(aggregate_voiced_bytes)
                            exists = True
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                    'Failed to download voice file: {}'.format(str(e)))
                            try:
                                os.remove(voice_file_path)
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
        return voice_file_path, aggregate_voiced_bytes

    def split_into_phrases(self, text_to_voice: str) -> List[str]:
        clz = type(self)
        phrase_chunks: List[str] = []
        try:
            phrases: List[str] = re.split(PUNCTUATION_PATTERN, text_to_voice)
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'len phrases: {len(phrases)}')
            xbmc.log(f'len phrases: {len(phrases)}', xbmc.LOGDEBUG)
            while len(phrases) > 0:
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'len phrases: {len(phrases)}')
                xbmc.log(f'len phrases: {len(phrases)}', xbmc.LOGDEBUG)
                phrase_chunk = phrases.pop(0)
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'phrase: {phrase_chunk}'
                                              f' len: {len(phrase_chunk)}')
                xbmc.log(f'phrase: {phrase_chunk}'
                         f' len: {len(phrase_chunk)}', xbmc.LOGDEBUG)

                # When a phrase exceeds the maximum phrase length,
                # go ahead and return the over-length phrase.

                if (len(phrase_chunk) >=
                        ResponsiveVoiceTTSBackend.MAXIMUM_PHRASE_LENGTH):
                    if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                        clz._logger.debug_verbose(f'Long phrase: {phrase_chunk}'
                                                  f' length: {len(phrase_chunk)}')
                    xbmc.log(f'Long phrase: {phrase_chunk}'
                             f' length: {len(phrase_chunk)}', xbmc.LOGDEBUG)
                    phrase_chunks.append(phrase_chunk)
                    phrase_chunk = ''
                else:
                    # Append phrases onto phrase_chunk as long as there is room
                    while len(phrases) > 0:
                        next_phrase = phrases[0]  # Don't pop yet
                        if ((len(phrase_chunk) + len(next_phrase)) <=
                                ResponsiveVoiceTTSBackend.MAXIMUM_PHRASE_LENGTH):
                            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                                clz._logger.debug_verbose(f'Appending to phrase_chunk:'
                                                          f' {next_phrase}'
                                                          f' len: {len(next_phrase)}')
                            xbmc.log(f'Appending to phrase_chunk:'
                                     f' {next_phrase}'
                                     f' len: {len(next_phrase)}', xbmc.LOGDEBUG)
                            phrase_chunk += phrases.pop(0)
                        else:
                            phrase_chunks.append(phrase_chunk)
                            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                                clz._logger.debug_verbose(f'Normal phrase: {phrase_chunk}'
                                                          f' length: {len(phrase_chunk)}')
                            xbmc.log(f'Normal phrase: {phrase_chunk}'
                                     f' length: {len(phrase_chunk)}', xbmc.LOGDEBUG)
                            phrase_chunk = ''
                            break
                if len(phrase_chunk) > 0:
                    phrase_chunks.append(phrase_chunk)
                    if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                        clz._logger.debug_verbose(f'Last phrase: {phrase_chunk}'
                                                  f' length: {len(phrase_chunk)}')
                    xbmc.log(f'Last phrase: {phrase_chunk}'
                             f' length: {len(phrase_chunk)}', xbmc.LOGDEBUG)
        except Exception as e:
            clz._logger.exception(e)
        return phrase_chunks

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
        except:
            pass

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        if setting in cls.settings.keys():
            return True
        return False

    @classmethod
    def getSettingNames(cls) -> List[str]:
        settingNames: List[str] = []
        for settingName in cls.settings.keys():
            settingNames.append(settingName)

        return settingNames

    @classmethod
    def settingList(cls, setting, *args) -> List[str]:
        '''
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translated). Sorting/translating done
        in UI.

        :param setting:
        :param args:
        :return:
        '''
        if setting == Settings.LANGUAGE:
            # Returns list of languages and value of closest match to current
            # locale

            locales = cls.voices_by_locale_map.keys()

            # Get current process' language_code i.e. en-us
            default_locale = Constants.LOCALE.lower().replace('_', '-')

            longest_match = -1
            default_lang = default_locale[0:2]
            default_lang_country = ''
            if len(default_locale) >= 5:
                default_lang_country = default_locale[0:5]

            idx = 0
            languages = []
            # Sort by locale so that we have shortest locales listed first
            # i.e. 'en" before 'en-us'
            for locale in sorted(locales):
                lower_lang = locale.lower()
                if longest_match == -1:
                    if lower_lang.startswith(default_lang):
                        longest_match = idx
                elif lower_lang.startswith(default_lang_country):
                    longest_match = idx
                elif lower_lang.startswith(default_locale):
                    longest_match = idx

                lang = Languages.get_label(locale)
                entry = (lang, locale)  # Display value, setting_value
                languages.append(entry)
                idx += 1

            # Now, convert index to default_setting

            default_setting = ''
            if longest_match > 0:
                default_setting = languages[longest_match][1]

            return languages, default_setting

        elif setting == Settings.GENDER:
            current_locale = cls.getLanguage()
            voices = cls.voices_by_locale_map.get(current_locale)

            genders = set()
            if voices is not None:
                for voice_name, voice_id, gender_id in voices:
                    genders.add(gender_id)

            return list(genders)

        elif setting == Settings.VOICE:
            current_locale = cls.getLanguage()
            voices = cls.voices_by_locale_map.get(current_locale)

            voice_ids = list()
            if voices is not None:
                for voice_name, voice_id, gender_id in voices:

                    # TODO: translate voice_id
                    voice_ids.append((voice_name, voice_id))

            return list(voice_ids)

        elif setting == Settings.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(Settings.PLAYER)
            player_ids: List[str] = []
            for player in cls.player_handler_class().getAvailablePlayers():
                player_ids.append(player.ID)
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
    def negotiate_engine_config(cls, backend_id: str, player_volume_adjustable: bool,
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
    def getVolumeDb(cls) -> float:
        # Range -12 .. +12, 8 default
        # API 0.1 .. 1.0. 1.0 default
        volume: float
        if cls.is_use_cache():
            volume = cls.volumeConstraints.default
        else:
            volume = cls.getSetting(Settings.VOLUME)

        return volume

    @classmethod
    def getEngineVolume(cls) -> float:
        """
        Get the configured volume in our standard  -12db .. +12db scale converted
        to the native scale of the API (0.1 .. 1.0). The maximum volume is equivalent
        to 0db. Therefore, convert -12db .. 0db to scale of 0.1 to 2.0 and clip at 1.0
        """
        volumeDb: float = cls.getVolumeDb()  # -12 .. +12 db
        volume: float = cls.volumeConstraints.translate_value(cls.volumeConversionConstraints,
                                                              volumeDb)
        volume = max(1.0, volume)
        return volume

    @classmethod
    def getEngineVolume_str(cls) -> str:
        return f'{cls.getEngineVolume():.2f}'

    @classmethod
    def getVoice(cls) -> str:
        voice = cls.getSetting(Settings.VOICE)
        if voice is None:
            lang = cls.voices_by_locale_map.get(cls.getLanguage())
            if lang is not None:
                voice = lang[0][1]
        voice = 'g2'
        return voice

    @classmethod
    def getLanguage(cls) -> str:
        language = cls.getSetting(Settings.LANGUAGE)
        language = 'en-US'
        return language

    @classmethod
    def getPitch(cls) -> float:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        if cls.is_use_cache():
            pitch = float(cls.pitchConstraints.default) / 100.0
        else:
            pitch = int(cls.getSetting(Settings.PITCH)) + 1
            pitch = float(pitch) / 100.0
        return pitch

    @classmethod
    def getPitch_str(cls) -> str:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        # TODO: Solve this differently!!!!
        if cls.is_use_cache():
            pitch = float(cls.pitchConstraints.default) / 100.0
        else:
            pitch = int(cls.getSetting(Settings.PITCH)) + 1
            pitch = float(pitch) / 100.0
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
        speed_i: int = cls.getSetting(Settings.SPEED)
        speed = float(speed_i) / 100.0
        return speed

    @classmethod
    def getApiSpeed(cls) -> str:
        # Leave it to the player to adjust speed
        return "50"

    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender

    @classmethod
    def is_use_cache(cls) -> bool:
        return cls.getSetting(Settings.CACHE_SPEECH)

    @classmethod
    def getAPIKey(cls) -> str:
        return cls.getSetting(Settings.API_KEY)

    # All voices are empty strings
    # def setVoice(self, voice):
    #    self.voice = voice

    @staticmethod
    def available() -> bool:
        return MP3AudioPlayerHandler.canPlay()
