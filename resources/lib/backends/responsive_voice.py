# -*- coding: utf-8 -*-

import requests
import io
import os
from typing import Any, List, Union, Type

from backends.audio import (BuiltInAudioPlayer, MP3AudioPlayerHandler, WavAudioPlayerHandler,
                            BasePlayerHandler)
from backends import base
from common.constants import Constants
from common.logger import LazyLogger
from common.system_queries import SystemQueries
from common.messages import Messages
from common.setting_constants import Backends, Languages, Genders, Players
from common.settings import Settings

from backends.base import SimpleTTSBackendBase
from cache.voicecache import VoiceCache


module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


class ResponsiveVoiceTTSBackend(SimpleTTSBackendBase):
    # Only returns .mp3 files

    provider = Backends.RESPONSIVE_VOICE_ID
    displayName = 'ResponsiveVoice'
    player_handler_class: Type[BasePlayerHandler] = MP3AudioPlayerHandler
    pitchConstraints = (0, 50, 99, True)
    speedConstraints = (0, 50, 99, True)
    volumeConstraints = (-12, 8, 12, True)

    RESPONSIVE_VOICE_URL = "http://responsivevoice.org/responsivevoice/getvoice.php"

    settings = {
        Settings.API_KEY: None,
        Settings.GENDER: 'female',
        Settings.LANGUAGE: 'en-US',
        Settings.VOICE: 'g1',
        Settings.PIPE: False,
        Settings.PITCH: 50,
        Settings.PLAYER: Players.MPG123,
        Settings.SPEED: 50,
        Settings.VOLUME: 8,
        Settings.CACHE_SPEECH: True
    }

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

    VOICE_1 = Messages.get_msg(Messages.VOICE_1)
    VOICE_2 = Messages.get_msg(Messages.VOICE_2)
    VOICE_3 = Messages.get_msg(Messages.VOICE_3)

    voices_by_locale_map = {
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
    _logger = None

    def __init__(self):
        super().__init__()
        type(self)._logger = module_logger.getChild(
            type(self).__name__)  # type: LazyLogger
        self.process = None
        self.update()
        self.stop_processing = False

    @staticmethod
    def isSupportedOnPlatform():
        return (SystemQueries.isLinux() or SystemQueries.isWindows()
                or SystemQueries.isOSX())

    @staticmethod
    def isInstalled():
        installed = False
        if ResponsiveVoiceTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def getMode(self):
        # built-in player not supported
        # player = self.setting(Settings.PLAYER)
        if type(self).getSetting(Settings.PIPE):
            return base.SimpleTTSBackendBase.PIPE
        else:
            return base.SimpleTTSBackendBase.WAVOUT

    def runCommand(self, text_to_voice, dummy):

        # If caching disabled, then exists is always false. file_path
        # always contains path to cached file, or path where to download to

        self.stop_processing = False
        file_path, exists = self.get_path_to_voice_file(text_to_voice,
                                                        use_cache=self.is_use_cache())
        if not exists:
            file_path, mp3_voice = self.download_speech(
                text_to_voice, file_path)
            if mp3_voice is not None and not self.stop_processing:
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)

                    with open(file_path, "wb") as f:
                        f.write(mp3_voice)
                    exists = True
                except Exception as e:
                    if type(self)._logger.isEnabledFor(LazyLogger.ERROR):
                        type(self)._logger.error(
                            'Failed to download voice file: {}'.format(str(e)))
                    try:
                        os.remove(file_path)
                    except Exception as e2:
                        pass

        if self.stop_processing:
            if type(self)._logger.isEnabledFor(LazyLogger.DEBUG_EXTRA_VERBOSE):
                type(self)._logger.debug_extra_verbose('stop_processing')
            return False

        if exists:
            # the following a geared towards Mplayer. Assumption is that only adjust
            # volume in player, other settings in engine.

            volume_db = type(self).get_volume_db()  # -12 .. 12
            player_speed = 100.0  # Don't alter speed/temp (percent)
            # Changing pitch without impacting tempo (speed) is
            player_pitch = 100.0  # Percent
            # not easy. One suggestion is to use lib LADSPA
            self.setPlayer(type(self).getSetting(Settings.PLAYER))
            self.player_handler.setVolume(float(volume_db))  # In db -12 .. 12
            self.player_handler.setSpeed(player_speed)
            self.player_handler.setPitch(player_pitch)

        return exists

    def runCommandAndPipe(self, text_to_voice):

        # If caching disabled, then voice_file and mp3_voice are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. mp3_voice is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        self.stop_processing = False
        mp3_pipe = None
        voice_file, mp3_voice = self.get_voice_from_cache(text_to_voice)
        if mp3_voice is None:
            voice_file, mp3_voice = self.download_speech(
                text_to_voice, voice_file)
        if mp3_voice is not None:
            mp3_pipe = io.BytesIO(mp3_voice)

        # the following a geared towards Mplayer. Assumption is that only adjust
        # volume in player, other settings in engine.

        volume_db = type(self).get_volume_db()  # -12 .. 12
        player_speed = 1.0  # Don't alter speed/temp
        # Changing pitch without impacting tempo (speed) is
        player_pitch = 1.0
        # not easy. One suggestion is to use lib LADSPA

        self.setPlayer(type(self).getSetting(Settings.PLAYER))
        self.player_handler.setVolume(volume_db)  # In db -12 .. 12
        self.player_handler.setSpeed(player_speed)
        self.player_handler.setPitch(player_pitch)

        return mp3_pipe

    def download_speech(self, text_to_voice, voice_file):
        # If voice file is None, then don't save voiced text to it,
        # just return the voiced text as bytes

        key = type(self).getAPIKey()
        lang = type(self).getLanguage()
        gender = type(self).getGender()
        pitch = type(self).getPitch()
        speed = type(self).getSpeed()
        volume = type(self).getVolume()  # 0.1 .. 1.0
        service = type(self).getVoice()
        if type(self)._logger.isEnabledFor(LazyLogger.DEBUG_VERBOSE):
            type(self)._logger.debug_verbose(
                'text: {} lang: {} gender: {} pitch {} speed: {} volume: {} service: {}'
                .format(text_to_voice, lang, gender, pitch, speed, volume, service))
        api_volume = "1.0"  # volume
        api_speed = speed
        api_pitch = pitch
        params = {
            "key": key,
            "t": text_to_voice,
            "tl": lang,
            "pitch": api_pitch,
            "rate": api_speed,
            "vol": api_volume,
            "sv": service,
            "vn": '',
            "gender": gender
        }

        voiced_bytes = None
        if not self.stop_processing:
            try:
                r = requests.get(type(self).RESPONSIVE_VOICE_URL, params=params,
                                 timeout=10.0)
                if type(self)._logger.isEnabledFor(LazyLogger.DEBUG_VERBOSE):
                    type(self)._logger.debug_extra_verbose('Request status: {} elapsed: {}'
                                                     .format(str(r.status_code),
                                                             str(r.elapsed)))
                if r is None or r.status_code != 200:
                    if type(self)._logger.isEnabledFor(LazyLogger.ERROR):
                        type(self)._logger.error(
                            'Failed to download voice for {} status: {:d} reason {}'
                            .format(text_to_voice, r.status_code, r.reason))
                elif not self.stop_processing:
                    voiced_bytes = r.content
                    bad_file = False
                    if len(voiced_bytes) < 2048:
                        bad_file = True
                    else:
                        magic = b'<!DOCTYPE'
                        if voiced_bytes[0:len(magic)] == magic:
                            bad_file = True
                    if bad_file:
                        if type(self)._logger.isEnabledFor(LazyLogger.ERROR):
                            type(self)._logger.error('Response not valid sound file')
                        voiced_bytes = None

                    if voiced_bytes is not None and voice_file is not None:
                        try:
                            if os.path.isfile(voice_file):
                                os.unlink(voice_file)

                            with open(voice_file, "wb") as f:
                                f.write(voiced_bytes)
                            exists = True
                        except Exception as e:
                            if type(self)._logger.isEnabledFor(LazyLogger.ERROR):
                                type(self)._logger.error(
                                    'Failed to download voice file: {}'.format(str(e)))
                            try:
                                os.remove(voice_file)
                            except Exception as e2:
                                pass
            except Exception as e:
                if type(self)._logger.isEnabledFor(LazyLogger.ERROR):
                    type(self)._logger.error(
                        'Failed to download voice: {}'.format(str(e)))
                voice_file = None
                voiced_bytes = None
        return voice_file, voiced_bytes

    def update(self):
        self.process = None
        self.stop_processing = False

    def stop(self):
        if type(self)._logger.isEnabledFor(LazyLogger.DEBUG_VERBOSE):
            type(self)._logger.debug_verbose('stop')
        self.stop_processing = True
        if not self.process:
            return
        try:
            if type(self)._logger.isEnabledFor(LazyLogger.DEBUG_VERBOSE):
                type(self)._logger.debug_verbose('terminate')
            self.process.terminate()  # Could use self.process.kill()
        except:
            pass

    @classmethod
    def isSettingSupported(cls, setting):
        if setting in cls.settings.keys():
            return True
        return False

    @classmethod
    def getSettingNames(cls):
        settingNames = []
        for settingName in cls.settings.keys():
            # settingName = settingName + '.' + cls.provider
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

            players = cls.get_players(include_builtin=False)
            default_player = cls.get_setting_default(Settings.PLAYER)

            return players, default_player

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
    def get_volume_db(cls):
        # Range -12 .. +12, 0 default
        # API 0.1 .. 1.0. 1.0 default
        volume = cls.getSetting(Settings.VOLUME)
        return '{:.2f}'.format(volume)

    @classmethod
    def getVolume(cls):
        # Range -12 .. +12, 0 default
        # API 0.1 .. 1.0. 1.0 default
        volume = cls.get_volume_db()
        volume = (float(volume) + 12.0) / 24.0

        return '{:.2f}'.format(volume)

    @classmethod
    def getVoice(cls):
        voice = cls.getSetting(Settings.VOICE)
        if voice is None:
            lang = cls.voices_by_locale_map.get(cls.getLanguage())
            if lang is not None:
                voice = lang[0][1]
        voice = 'g2'
        return voice

    @classmethod
    def getLanguage(cls):
        language = cls.getSetting(Settings.LANGUAGE)
        language = 'en-US'
        return language

    @classmethod
    def getPitch(cls):
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        pitch = int(cls.getSetting(Settings.PITCH)) + 1
        pitch = float(pitch) / 100.0
        return '{:.2f}'.format(pitch)

    @classmethod
    def getSpeed(cls):
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        speed = int(cls.getSetting(Settings.SPEED)) + 1
        speed = float(speed) / 100.0
        return '{:.2f}'.format(speed)

    @classmethod
    def getGender(cls):
        gender = 'female'

    @classmethod
    def is_use_cache(cls):
        return cls.getSetting(Settings.CACHE_SPEECH)

    @classmethod
    def getAPIKey(cls):
        return cls.getSetting(Settings.API_KEY)

    # All voices are empty strings
    # def setVoice(self, voice):
    #    self.voice = voice

    @staticmethod
    def available():
        return MP3AudioPlayerHandler.canPlay()
