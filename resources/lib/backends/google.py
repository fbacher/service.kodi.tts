# -*- coding: utf-8 -*-
import io
import os
import pathlib

import regex
import subprocess
import sys
from email._header_value_parser import Phrase

from gtts import gTTS, gTTSError, lang

from backends import base
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.iplayer import IPlayer
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator, StringValidator
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants, ReturnCode
from common.exceptions import ExpiredException
from common.logger import *
from common.logger import BasicLogger
from common.monitor import Monitor
from common.phrases import PhraseList, Phrase, PhraseUtils
from common.setting_constants import Backends, Mode
from common.settings import Settings
from common.simple_run_command import SimpleRunCommand
from common.typing import *
from utils.util import runInThread

module_logger = BasicLogger.get_module_logger(module_path=__file__)
PUNCTUATION_PATTERN = regex.compile(r'([.,:])', regex.DOTALL)


#  gtts.lang.tts_langs()

class Results:
    """
        Contains results of background thread/process
        Provides ability for caller to get status/results
        Also allows caller to abandon results, but allow task to continue
        quietly. This is useful for downloading/generating speech which may
        get canceled before finished, but results can be cached for later use
    """

    def __init__(self):
        self.rc: ReturnCode = ReturnCode.NOT_SET
        self.download: io.BytesIO = io.BytesIO(initial_bytes=b'')
        self.finished: bool = False
        self.phrase: Phrase = None

    def get_rc(self) -> ReturnCode:
        return self.rc

    def get_download_bytes(self) -> memoryview:
        return self.download.getbuffer()

    def get_download_stream(self) -> io.BytesIO:
        return self.download

    def is_finished(self) -> bool:
        return self.finished

    def get_phrase(self) -> Phrase:
        return self.phrase

    def set_finished(self, finished: bool) -> None:
        self.finished = finished

    # def set_download(self, data: bytes | io.BytesIO | None) -> None:
    #     self.download = data

    def set_rc(self, rc: ReturnCode) -> None:
        self.rc = rc

    def set_phrase(self, phrase: Phrase) -> None:
        self.phrase = phrase


class SpeechGenerator:
    RESPONSIVE_VOICE_URL: Final[
        str] = "http://responsivevoice.org/responsivevoice/getvoice.php"
    MAXIMUM_PHRASE_LENGTH: Final[int] = 200

    _logger: BasicLogger = None

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.download_results: Results = Results()

    def set_rc(self, rc: ReturnCode) -> None:
        self.download_results.set_rc(rc)

    def get_rc(self) -> ReturnCode:
        return self.download_results.get_rc()

    def set_phrase(self, phrase: Phrase) -> None:
        self.download_results.set_phrase(phrase)

    def get_download_bytes(self) -> bytes:
        return self.download_results.get_download_bytes()

    def set_finished(self) -> None:
        self.download_results.set_finished(True)

    def is_finished(self) -> bool:
        return self.download_results.is_finished()

    def get_results(self) -> Results:
        if self.get_rc() == ReturnCode.OK:
            phrase: Phrase = self.download_results.get_phrase()
            phrase.set_exists(True)
        return self.download_results

    def generate_speech(self, caller: 'GoogleTTSEngine', phrase: Phrase,
                        timeout: float = 720.0, download_file_only : bool = True) -> Results:
        # Disable expiration checks. We are doing this in background. Results
        # are cached for next time

        clz = type(self)
        Monitor.exception_on_abort(timeout=0.01)
        max_phrase_length: int | None
        max_phrase_length = SettingsMap.get_service_property(GoogleTTSEngine.service_ID,
                                                             Constants.MAX_PHRASE_LENGTH)
        if max_phrase_length is None:
            max_phrase_length = 10000  # Essentially no limit
        self.set_phrase(phrase)
        phrases: PhraseList = PhraseUtils.split_into_chunks(phrase, max_phrase_length)
        unchecked_phrases: PhraseList = phrases.clone(check_expired=False)
        runInThread(self._generate_speech, name='download_speech', delay=0.0,
                    phrases=unchecked_phrases, timeout=timeout, download_file_only=download_file_only)
        max_wait: int = int(timeout / 0.1)
        while max_wait > 0:
            Monitor.exception_on_abort(timeout=0.1)
            max_wait -= 1
            if self.get_rc() <= ReturnCode.MINOR_SAVE_FAIL or caller.stop_processing:
                clz._logger.debug(f'generate_speech exit rc: {self.get_rc().name}  '
                                  f'stop: {caller.stop_processing}')
                break
        return self.download_results

    def _generate_speech(self, **kwargs) -> None:
        # Break long texts into 250 char chunks so that they can be downloaded.
        # Concatenate returned binary voice files together and return
        clz = type(self)
        self.set_rc(ReturnCode.OK)
        text_file_path: pathlib.Path = None
        try:
            # The passed in phrases, are actually chunks of a phrase. Therefore
            # we concatenate the voiced text from each chunk to produce one
            # sound file. This phrase list has expiration disabled.

            phrases: PhraseList = kwargs.get('phrases')
            download_file_only: bool = kwargs.get('download_file_only', True)
            if phrases is None or len(phrases) == 0:
                self.set_rc(ReturnCode.NO_PHRASES)
                return

            phrase = phrases[0]
            Monitor.exception_on_abort()
            if phrase.exists():
                return  # Nothing to do

            rc2: int
            rc2, _ = VoiceCache.create_sound_file(phrase.get_cache_path(),
                                                  create_dir_only=True)
            if rc2 != 0:
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(f'Failed to create cache directory '
                                      f'{phrase.get_cache_path()}')
                self.set_rc(ReturnCode.CALL_FAILED)
                return

            lang: str = GoogleTTSEngine.getLanguage()
            gender: str = GoogleTTSEngine.getGender()
            pitch: str = GoogleTTSEngine.getPitch_str()  # hard coded. Let
            # player decide
            speed: str = GoogleTTSEngine.getApiSpeed()  # Also hard coded
            # value for 1x speed
            volume: str = GoogleTTSEngine.getEngineVolume_str()
            service: str = GoogleTTSEngine.getVoice()
            api_volume: str = volume  # volume
            api_speed = speed
            api_pitch: str = pitch

            with phrase.get_cache_path().open('wb') as sound_file:
                for phrase in phrases:
                    try:
                        Monitor.exception_on_abort()
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'phrase: '
                                                      f'{phrase.get_text()}')
                        gtts: MyGTTS = MyGTTS(phrase)
                        # gtts.save(phrase.get_cache_path())
                        #     gTTSError – When there’s an error with the API request.
                        # gtts.stream() # Streams bytes
                        gtts.write_to_fp(sound_file)
                        clz._logger.debug(f'Wrote cache_file fragment')
                    except AbortException:
                        self.set_rc(ReturnCode.ABORT)
                        reraise(*sys.exc_info())
                    except TypeError as e:
                        clz._logger.exception('')
                    except ExpiredException:
                        clz._logger.exception('')
                    except gTTSError as e:
                        clz._logger.exception (f'gTTSError')
                    except IOError  as e:
                        clz._logger.exception(f'Error processing phrase: '
                                          f'{phrase.get_text()}')
                        clz._logger.error(f'Error writing to cache file:'
                                          f' {str(phrase.get_cache_path())}')
                        try:
                            phrase.get_cache_path().unlink(True)
                        except Exception as e2:
                            clz._logger.exception('Can not delete '
                                                  f' {str(phrase.get_cache_path())}')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        break
                        '''
                        text_path: pathlib.Path = None
                        try:
                            text_path = phrase.get_cache_path().with_suffix(
                                    '.txt')
                            text_path.unlink(True)
                        except Exception as e:
                            clz._logger.exception(f'Unable to delete '
                                                  f'{str(text_path)}')
                        '''
            clz._logger.debug(f'Finished with loop writing cache_file: '
                              f'{phrases[0].get_cache_path()}')
            sound_file.close()
            if (self.get_rc() == ReturnCode.OK
                    and len(self.download_results.get_download_bytes()) > 0):
                self.set_finished()
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            reraise(*sys.exc_info())
        except ExpiredException:
            clz._logger.exception('')
        except Exception as e:
            if clz._logger.isEnabledFor(ERROR):
                clz._logger.error('Failed to download voice: {}'.format(str(e)))
            self.set_rc(ReturnCode.DOWNLOAD)
        finally:
            if self.get_rc() > ReturnCode.MINOR_SAVE_FAIL:
                try:
                    phrases[0].get_cache_path().unlink(True)
                except Exception:
                    clz._logger.exception('')
        clz._logger.debug(f'exit download_speech')
        return None


class MyGTTS(gTTS):

    def __init__(self, phrase: Phrase) -> None:
        """
        :param self:
        :param phrase:
        :return:

        Raises:
        AssertionError – When text is None or empty; when there’s nothing left to speak
        after pre-precessing, tokenizing and cleaning.
        ValueError – When lang_check is True and lang is not supported.
        RuntimeError – When lang_check is True but there’s an error loading the
        languages dictionary.
        """
        super().__init__(phrase.get_text(),
                         lang="en",
                         slow=False,
                         lang_check=True,
                         tld="us"
                         #  pre_processor_funcs=[
                         #     pre_processors.tone_marks,
                         #     pre_processors.end_of_line,
                         #     pre_processors.abbreviations,
                         #     pre_processors.word_sub,
                         # ],
                         # tokenizer_func=Tokenizer(
                         #         [
                         #             tokenizer_cases.tone_marks,
                         #             tokenizer_cases.period_comma,
                         #             tokenizer_cases.colon,
                         #             tokenizer_cases.other_punctuation,
                         #         ]
                         # ).run,
                         )


class GoogleTTSEngine(base.SimpleTTSBackend):
    ID: str = Backends.GOOGLE_ID
    backend_id = Backends.GOOGLE_ID
    engine_id = Backends.GOOGLE_ID
    service_ID: str = Services.GOOGLE_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    displayName = 'GoogleTTS'

    _logger: BasicLogger = None
    lang_map: Dict[str, str] = None # IETF_lang_name: display_name
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        self.process = None
        self.simple_cmd: SimpleRunCommand = None
        self.stop_processing = False
        if not clz._initialized:
            BaseServices().register(self)
            clz._initialized = True

    def init(self) -> None:
        clz = type(self)
        super().init()
        self.update()

    def getMode(self) -> Mode:
        clz = type(self)
        player: IPlayer = self.get_player()
        if clz.getSetting(SettingsProperties.PIPE):
            return Mode.PIPE
        else:
            return Mode.FILEOUT

    def runCommand(self, phrase: Phrase) -> bool:
        clz = type(self)
        # Caching is ALWAYS used here, otherwise the delay would be maddening.
        # Therefore, this is only called when the voice file is NOT in the
        # cache. It is also ONLY called by the background thread in SeedCache.

        self.stop_processing = False
        try:
            if not phrase.exists():
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                espeak_engine = BaseServices.getService(SettingsProperties.ESPEAK_ID)
                espeak_engine.say_phrase(phrase)
                # generate voice in cache for the future.
                # Ignore result, don't wait
                generator: SpeechGenerator = SpeechGenerator()
                generator.generate_speech(self, tmp_phrase, timeout=0.0,
                                          download_file_only=True)
        except ExpiredException:
            return False

        return phrase.exists()

    def runCommandAndPipe(self, phrase: Phrase):
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        self.stop_processing = False
        audio_pipe = None
        byte_stream: io.BinaryIO = None
        try:
            VoiceCache.get_path_to_voice_file(phrase, use_cache=Settings.is_use_cache())
            if not phrase.exists():
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                espeak_engine = BaseServices.getService(SettingsProperties.ESPEAK_ID)
                if not espeak_engine.initialized:
                    espeak_engine.init()

                espeak_engine.say_phrase(phrase)
                # generate voice in cache for the future.
                # Ignore result, don't wait
                generator: SpeechGenerator = SpeechGenerator()
                generator.generate_speech(self, tmp_phrase, timeout=0.0,
                                          download_file_only=True)
            else:
                try:
                    byte_stream = io.open(phrase.get_cache_path(), 'br')
                except Exception:
                    clz._logger.exception('')
                    byte_stream = None

        except ExpiredException:
            pass
        # the following a geared towards Mplayer. Assumption is that only adjust
        # volume in player, other settings in engine.

        # volume_db: float = clz.get_volume_db()  # -12 .. 12
        return byte_stream

    def seed_text_cache(self, phrases: PhraseList) -> None:
        # For engines that are expensive, it can be beneficial to cache the voice
        # files. In addition, by saving text to the cache that is not yet
        # voiced, then a background process can generate speech so the cache
        # gets built more quickly

        clz = type(self)
        try:
            # We don't care whether it is too late to say this text.
            clz._logger.debug(f'Here')
            phrases = phrases.clone(check_expired=False)
            for phrase in phrases:
                if Settings.is_use_cache():
                    VoiceCache.get_path_to_voice_file(phrase, use_cache=True)
                    if not phrase.exists():
                        text_to_voice: str = phrase.get_text()
                        voice_file_path: pathlib.Path = phrase.get_cache_path()
                        clz._logger.debug_extra_verbose(f'PHRASE Text {text_to_voice}')
                        rc: int = 0
                        try:
                            # Should only get here if voiced file (.wav, .mp3, etc.) was NOT
                            # found. We might see a pre-existing .txt file which means that
                            # the download failed. To prevent multiple downloads, wait a day
                            # before retrying the download.

                            voice_text_file: pathlib.Path | None = None
                            voice_text_file = voice_file_path.with_suffix('.txt')
                            try:
                                if os.path.isfile(voice_text_file):
                                    os.unlink(voice_text_file)

                                with open(voice_text_file, 'wt') as f:
                                    f.write(text_to_voice)
                            except Exception as e:
                                if clz._logger.isEnabledFor(ERROR):
                                    clz._logger.error(
                                            f'Failed to save voiced text file: '
                                            f'{voice_text_file} Exception: {str(e)}')
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        'Failed to download voice: {}'.format(str(e)))
        except Exception as e:
            clz._logger.exception('')
        clz._logger.debug(f'Leaving')

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
    def settingList(cls, setting, *args) -> List[str] | List[Tuple[str, str]] | Tuple[
        List[str], str] | Tuple[List[Tuple[str, str]], str]:
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
            # locale

            if cls.lang_map is None:
                cls.lang_map =  lang.tts_langs()
            lang_ids = cls.lang_map.keys()

            # Get current process' language_code i.e. en-us
            default_locale = Constants.LOCALE.lower().replace('_', '-')

            longest_match = -1
            default_lang = default_locale[0:2]
            idx = 0
            languages = []
            # Sort by locale so that we have shortest locales listed first
            # i.e. 'en" before 'en-us'
            for lang_id in sorted(lang_ids):
                lower_lang = lang_id.lower()
                if longest_match == -1:
                    if lower_lang.startswith(default_lang):
                        longest_match = idx
                # elif lower_lang.startswith(default_lang_country):
                #     longest_match = idx
                if lower_lang.startswith(default_locale):
                    longest_match = idx

                lang_name: str = cls.lang_map[lang_id]
                entry = (lang_name, lang_id)  # Display value, setting_value
                languages.append(entry)
                idx += 1

            # Now, convert index to index of default_setting

            default_setting = ''
            if longest_match > 0:
                default_setting = languages[longest_match][1]

            return languages, default_setting

            '''
            elif setting == SettingsProperties.GENDER:
                current_locale = cls.getLanguage()
                voices = cls.voices_by_locale_map.get(current_locale)
    
                genders = set()
                if voices is not None:
                    for voice_name, voice_id, gender_id in voices:
                        genders.add(gender_id)
    
                return list(genders)
    
            elif setting == SettingsProperties.VOICE:
                current_locale = cls.getLanguage()
                voices = cls.voices_by_locale_map.get(current_locale)
    
                voice_ids: List[Tuple[str, str]] = list()
                if voices is not None:
                    for voice_name, voice_id, gender_id in voices:
                        voice_name: str
                        voice_id: str
    
                        # TODO: translate voice_id
                        voice_ids.append((voice_name, voice_id))
    
                return list(voice_ids)
            '''

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[str] = []
            return player_ids, default_player

    @classmethod
    def get_default_language(cls) -> str:
        languages: List[str]
        default_lang: str
        languages, default_lang = cls.settingList(SettingsProperties.LANGUAGE)
        return default_lang

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
        if Settings.is_use_cache():
            return True, True, True

        return False, False, False

    @classmethod
    def getVolumeDb(cls) -> float | None:
        volume_validator: ConstraintsValidator | IValidator
        volume_validator = SettingsMap.get_validator(cls.service_ID,
                                                     property_id=SettingsProperties.VOLUME)
        volume, _, _, _ = volume_validator.get_tts_values()

        return None  # Find out if used

    @classmethod
    def getEngineVolume(cls) -> float:
        """
        Get the configured volume in our standard  -12db .. +12db scale converted
        to the native scale of the API (0.1 .. 1.0). The maximum volume (1.0) is
        equivalent
        to 0db. Since we have to use a different player AND since it almost guaranteed
        that the voiced text is cached, just set volume to fixed 1.0 and let player
        handle volume).
        """
        return cls.getVolumeDb()

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
        return ''

        if voice is None:
            lang = cls.voices_by_locale_map.get(cls.getLanguage())
            if lang is not None:
                voice = lang[0][1]
        voice = 'g2'
        return voice

    @classmethod
    def getLanguage(cls) -> str:
        language_validator: StringValidator
        language_validator = cls.get_validator(cls.service_ID,
                                               property_id=SettingsProperties.LANGUAGE)
        language = language_validator.get_tts_value()
        return language

    @classmethod
    def getPitch(cls) -> float:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        pitch_validator: ConstraintsValidator
        pitch_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.PITCH)
        if Settings.is_use_cache():
            pitch = pitch_validator.default_value
        else:
            pitch: float = pitch_validator.get_tts_value()
        return pitch

    @classmethod
    def getPitch_str(cls) -> str:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        # TODO: Solve this differently!!!!

        # pitch: float = cls.getPitch()
        # return '{:.2f}'.format(pitch)
        return '50'

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
        speed: float
        speed, _, _, _ = speed_validator.get_tts_values()
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
                GoogleTTSEngine.service_ID)
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER, consumer_formats=[SoundCapabilities.MP3],
                producer_formats=[])
        if len(candidates) > 0:
            return True
