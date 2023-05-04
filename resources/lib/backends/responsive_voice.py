# -*- coding: utf-8 -*-

import requests
import io
import os
import re

import xbmc

from backends.audio import (MP3AudioPlayerHandler,
                            WavAudioPlayerHandler,
                            BasePlayerHandler)
from common.constants import Constants
from common.typing import *
from common.logger import *
from common.system_queries import SystemQueries
from common.messages import Messages
from common.setting_constants import Backends, Languages, Genders, Players
from common.settings import Settings

from backends.base import SimpleTTSBackendBase, Constraints
from cache.voicecache import VoiceCache


module_logger = BasicLogger.get_module_logger(module_path=__file__)
PUNCTUATION_PATTERN = re.compile(r'([.,:])', re.DOTALL)


class ResponsiveVoiceTTSBackend(SimpleTTSBackendBase):
    # Only returns .mp3 files

    backend_id = Backends.RESPONSIVE_VOICE_ID
    displayName = 'ResponsiveVoice'
    player_handler_class: Type[BasePlayerHandler] = WavAudioPlayerHandler

    # _speedArgs = 'scaletempo=scale={0}:speed=none'
    #     _speedMultiplier = 0.01  # The base scale is 0 - 100. Mplayer is 0.0 - 1.0
    #     _volumeArgs = 'volume={0}'  # Volume in db -200db .. +40db Default 0

    playerPitchConstrants: Constraints = Constraints(0, 0, 0, True)
    playerSpeedConstraints: Constraints = Constraints(-30, 0, 30, True)
    playerVolumeConstraints: Constraints = Constraints(-12, 0, 12, True)
    pitchConstraints: Constraints = Constraints(0, 50, 99, False)
    speedConstraints: Constraints = Constraints(0, 50, 99, False)
    volumeConstraints: Constraints = Constraints(-12, 8, 12, False)

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
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)
        self.process = None
        self.stop_processing = False

    def init(self) -> None:
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
        # player = self.setting(Settings.PLAYER)
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
        file_path, exists = self.get_path_to_voice_file(text_to_voice,
                                                        use_cache=self.is_use_cache())
        self._logger.debug(f'file_path: {file_path} exists: {exists}')
        if not exists:
            # Note that when caching, some audio settings are fixed for the engine
            # and passed on to the player. See the note below "if the audio exists..."
            file_path, mp3_voice = self.download_speech(
                text_to_voice, file_path)
            if mp3_voice != b'' and not self.stop_processing:
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)

                    with open(file_path, "wb") as f:
                        f.write(mp3_voice)
                    exists = True
                except Exception as e:
                    if type(self)._logger.isEnabledFor(ERROR):
                        type(self)._logger.error(
                            'Failed to download voice file: {}'.format(str(e)))
                    try:
                        os.remove(file_path)
                    except Exception as e2:
                        pass

        if self.stop_processing:
            if type(self)._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                type(self)._logger.debug_extra_verbose('stop_processing')
            return False

        if exists:
            # If the audio exists in a file, then use a player rather
            # than the engine. When the engine is set to cache to disk,
            # the audio settings are fixed. User's audio settings (volume, pitch, speed)
            # apply to the player when caching. Otherwise, the cached file would have
            # whatever settings were at the time of the creation of the file and you
            # could have different settings per phrase from the cache.
            #
            # The following a geared towards Mplayer.
            # These will undoubtedly need a lot of tweaking before this is
            # 'good enough'

            # volume_db: float = type(self).get_volume_db()  # -12 .. 12

            # Changing pitch without impacting tempo (speed) is
            # not easy. One suggestion is to use lib LADSPA

            # player_pitch: float = 100.0  # Percent

            # Keep in mind that these settings are on top of the original settings.
            # Because of this, amplify the effect of pitch and speed because it will
            # be limited by the original recorded levels. In other words, a value of
            # 100% here will simply keep the max pitch/speed at the original engine
            # setting. We need to have ability to go beyond the original, so allow
            # 200%. Need to refine this to scale appropriately for the player and
            # engine so that the scale here + the original engine scale will give the
            # entire range of values.

            player_pitch = int(clz.getSetting(Settings.PITCH)) + 1
            # player_pitch *= 2.0

            self.setPlayer(clz.get_player_setting())
            # Convert Native Responsive Voice speed to player's
            clz.setPlayerSpeed(clz.getSpeed())
            # scale responsive voice volume to player. Both logarithmic
            # player -200 == engine -12 8 == 50 12 == 99
            # normalize by adding RV.min  &RVPlayer.min
        return exists

    def runCommandAndPipe(self, text_to_voice: str):
        clz = type(self)

        # If caching disabled, then voice_file and mp3_voice are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. mp3_voice is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        self.stop_processing = False
        mp3_pipe = None
        voice_file: str | None
        mp3_voice: bytes
        voice_file, mp3_voice = self.get_voice_from_cache(text_to_voice)
        if len(voice_file) == 0:
            voice_file = None
        if len(mp3_voice) == 0:
            mp3_voice = None

        if mp3_voice is None:
            voice_file, mp3_voice = self.download_speech(
                text_to_voice, voice_file)
        if mp3_voice is not None:
            mp3_pipe = io.BytesIO(mp3_voice)

        # the following a geared towards Mplayer. Assumption is that only adjust
        # volume in player, other settings in engine.

        # volume_db: float = clz.get_volume_db()  # -12 .. 12
        self.setPlayer(clz.get_player_setting())

        # Convert Native Responsive Voice speed to player's
        clz.setPlayerSpeed(clz.getSpeed())
        return mp3_pipe

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
        pitch: str = clz.getPitch_str()    # hard coded value when caching
        speed: str = clz.getSpeed_str()    # ""
        volume = clz.getVolume()  # ""
        service: str = clz.getVoice()
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(
                'text: {} lang: {} gender: {} pitch {} speed: {} volume: {} service: {}'
                .format(text_to_voice, lang, gender, pitch, speed, volume, service))
        api_volume: str = "1.0"  # volume
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
                # If we failed to get speech before, don't try again.

                failing_voice_file: str | None = None  # None when save_to_file False
                if save_to_file:
                    failing_voice_file = voice_file_path + '.txt'
                    if os.path.isfile(failing_voice_file):
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
                            if os.path.isfile(failing_voice_file):
                                os.unlink(failing_voice_file)

                            with open(failing_voice_file, 'wt') as f:
                                f.write(text_to_voice)
                                f.write(f'\nPhrase: {phrase}')
                            exists = True
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                    f'Failed to save sample text to voice file: {str(e)}')
                            try:
                                os.remove(failing_voice_file)
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

    def stop(self):
        if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
            type(self)._logger.debug_verbose('stop')
        self.stop_processing = True
        if not self.process:
            return
        try:
            if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
                type(self)._logger.debug_verbose('terminate')
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
    def settingList(cls, setting, *args):
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
    def getVolume(cls) -> float:
        # Range -12 .. +12, 8 default
        # API 0.1 .. 1.0. 1.0 default
        volume: float
        if cls.is_use_cache():
            volume = cls.volumeConstraints.default
        else:
            volume = cls.getSetting(Settings.VOLUME)

        return volume

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
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        #
        # Always use separate player
        #if cls.is_use_cache():
        #    speed = float(cls.speedConstraints.default) / 100.0
        #else:
        speed = int(cls.getSetting(Settings.SPEED)) + 1
        speed = float(speed) / 100.0
        return speed

    @classmethod
    def getSpeed_str(cls) -> str:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        if cls.is_use_cache():
            speed = float(cls.speedConstraints.default) / 100.0
        else:
            speed = int(cls.getSetting(Settings.SPEED)) + 1
            speed = float(speed) / 100.0
        return '{:.2f}'.format(speed)

    @classmethod
    def setPlayerSpeed(cls, speed: float) -> None:
        # Native ResponsiveVoice speed is 1 .. 100, with default of 50,
        # but this has been scaled to be a %, so we see 0.01 .. 1.00
        # Therefore 0.5 is a speed of 1x
        # Multiplying by 2 gives:
        #   speed : 0.5 => player_speed of 1x
        #   speed : 0.25 => player_speed of 1/2 x
        #   speed : 0.1 => player_speed of 1/10 x
        #   speed : .75 => player_seed of 1.5x
        #
        # Player_speed scale is 3 .. 30 where actual play speed is player_speed / 10

        player_speed: float = float(speed * 2.0)
        if player_speed < 0.30:
            player_speed = 0.30  # 1/3 x
        elif player_speed > 1.5:
            player_speed  = player_speed * 1.5 # 2 * 1.5 = 3.0

        int_player_speed: int = int(player_speed * 10)
        Settings.setSetting(Settings.PLAYER_SPEED, int_player_speed,
                            backend_id=cls.backend_id)

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
