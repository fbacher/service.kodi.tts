# -*- coding: utf-8 -*-

import time
import threading
import queue
import os
from typing import List, Type, Union

from backends import audio
from backends.audio import BuiltInAudioPlayer
from cache.voicecache import VoiceCache
from common.settings import Settings
from common.setting_constants import Genders, Misc, Languages, Players
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.monitor import my_monitor
from common import utils

import xbmc

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Constraints:
    def __init__(self, minimum=0, default=0, maximum=0, integer=True):
        super().__init__()
        self.minimum = minimum
        self.default = default
        self.integer = integer


class TTSBackendBase:
    """The base class for all speech engine backends

    Subclasses must at least implement the say() method, and can use whatever
    means are available to speak text.
    """
    provider = 'auto'
    displayName = 'Auto'
    pauseInsert = '...'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False
    # Min, Default, Max, Integer_Only (no float)
    speedConstraints = (0, 0, 0, True)
    pitchConstraints = (0, 0, 0, True)

    # Volume constraints imposed by the api being called

    volumeConstraints = (-12, 0, 12, True)

    # Volume scale as presented to the user

    volumeExternalEndpoints = (-12, 12)
    volumeStep = 1
    volumeSuffix = 'dB'
    speedInt = True
    # _loadedSettings = {}
    _logger = module_logger.getChild('TTSBackendBase')  # type: BasicLogger
    dead = False  # Backend should flag this true if it's no longer usable
    deadReason = ''  # Backend should set this reason when marking itself dead
    _closed = False
    currentBackend = None
    #  currentSettings = []
    settings = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(
                type(self).__name__)  # type: BasicLogger

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close()

    def setWavStreamMode(self, enable=True):
        self.inWavStreamMode = enable

    def scaleSpeed(self, value, limit):  # Target is between -20 and 20
        return self.scaleValue(value, self.speedConstraints, limit)

    def scalePitch(self, value, limit):  # Target is between -20 and 20
        return self.scaleValue(value, self.pitchConstraints, limit)

    def scaleVolume(self, value, limit):
        return self.scaleValue(value, self.volumeConstraints, limit)

    # speedConstraints = (80, 175, 450, True)

    def scaleValue(self, value, constraints, limit):
        if value < 0:
            adj = constraints[1] - constraints[0]
            scale = (limit + value) / float(limit)
            new = scale * adj
            new += constraints[0]
        elif value > 0:
            adj = constraints[2] - constraints[1]
            scale = value / float(limit)
            new = scale * adj
            new += constraints[1]
        else:
            new = constraints[1]

        if constraints[3]:
            return int(new)
        return new

    def scale_db_to_percent(self, value, lower_bound=0, upper_bound=100):
        scaled_value = int(round(100 * (10 ** (value / 20.0))))
        scaled_value = max(scaled_value, lower_bound)
        scaled_value = min(scaled_value, upper_bound)
        return scaled_value

    def volumeUp(self):
        clz = type(self)
        if not self.settings or not 'volume' in self.settings:
            return Messages.get_msg(Messages.CANNOT_ADJUST_VOLUME)
        vol = type(self).getSetting('volume')
        max_volume: int = self.volumeExternalEndpoints[1]
        volume_step: int = self.volumeStep
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'Volume UP: {vol} Upper Limit: {max_volume} '
                              f'step {self.volumeStep}')
        vol += volume_step
        if vol > max_volume:
            volume_step = volume_step - (vol - max_volume)
            vol = max_volume
        self.setSetting('volume', vol)
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug('Volume UP: {0}'.format(vol))
        return f'Volume Up by {volume_step} now {vol} {self.volumeSuffix}'

    def volumeDown(self):
        clz = type(self)
        if not self.settings or not Settings.VOLUME in self.settings:
            return Messages.get_msg(Messages.CANNOT_ADJUST_VOLUME)
        min_volume: int = self.volumeExternalEndpoints[0]
        volume_step: int = self.volumeStep
        vol = clz.getSetting(Settings.VOLUME)
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'Volume Down: {vol} Lower Limit: {min_volume} '
                              f'step {volume_step}')
        vol -= volume_step
        if vol < min_volume:
            volume_step = volume_step - (min_volume - vol)
            vol = min_volume
        self.setSetting(Settings.VOLUME, vol)
        if type(self)._logger.isEnabledFor(DEBUG):
            type(self)._logger.debug('Volume DOWN: {0}'.format(vol))
        return f'Volume Down by {volume_step} now {vol} {self.volumeSuffix}'

    def flagAsDead(self, reason=''):
        self.dead = True
        self.deadReason = reason or self.deadReason

    def say(self, text, interrupt=False, preload_cache=False):
        """Method accepting text to be spoken

        Must be overridden by subclasses.
        text is unicode and the text to be spoken.
        If interrupt is True, the subclass should interrupt all previous speech.

        """
        raise Exception('Not Implemented')

    def sayList(self, texts, interrupt=False):
        """Accepts a list of text strings to be spoken

        May be overriden by subclasses. The default implementation calls say()
        for each item in texts, calling insertPause() between each.
        If interrupt is True, the subclass should interrupt all previous speech.
        """
        self.say(texts.pop(0), interrupt=interrupt)
        for t in texts:
            self.insertPause()
            self.say(t)

    @classmethod
    def get_pitch_constraints(cls):
        return cls.pitchConstraints

    @classmethod
    def get_volume_constraints(cls):
        return cls.volumeConstraints

    @classmethod
    def get_speed_constraints(cls):
        return cls.speedConstraints

    @classmethod
    def isSettingSupported(cls, setting):
        if setting in cls.settings.keys():
            return True
        return False

    @classmethod
    def getSettingNames(cls):
        """
        Gets a list of all of the setting names/keys that this provider uses

        :return:
        """
        settingNames = []
        for settingName in cls.settings.keys():
            # settingName = settingName + '.' + cls.provider
            settingNames.append(settingName)

        return settingNames

    @classmethod
    def get_setting_default(cls, setting):
        default = None
        if setting in cls.settings.keys():
            default = cls.settings.get(setting, None)
        return default

    @classmethod
    def settingList(cls, setting, *args):
        """Returns a list of options for a setting

        May be overridden by subclasses. Default implementation returns None.
        """
        return None

    @classmethod
    def setting(cls, setting):

        #  TODO: Replace with getSetting
        """Returns a backend setting, or default if not set
        """
        return cls.getSetting(setting, cls.get_setting_default(setting))

        # cls._loadedSettings[setting] = cls.getSetting(
        #     setting, cls.get_setting_default(setting))
        # return cls._loadedSettings[setting]

    #  @classmethod
    #  def initSettings(cls, newSettings):
    #      if cls.currentBackend != Settings.getSetting(Settings.BACKEND):
    #          for currentSetting in TTSBackendBase.currentSettings:
    #              Settings.setSetting(currentSetting, None)
    #          TTSBackendBase.currentSettings.clear()
    #
    #          for currentSetting in newSettings:
    #              currentValue = Settings.getSetting(
    #                  currentSetting + '.' + cls.provider)
    #              Settings.setSetting(currentSetting, currentValue)
    #              TTSBackendBase.currentSettings.append(currentSetting)

    @classmethod
    def getLanguage(cls):
        default_locale = Constants.LOCALE.lower().replace('_', '-')
        return cls.getSetting(Settings.LANGUAGE, default_locale)

    @classmethod
    def getGender(cls):
        gender = cls.getSetting(Settings.GENDER, Genders.UNKNOWN)

        return gender

    @classmethod
    def getVoice(cls):
        voice = cls.getSetting(Settings.VOICE, Settings.UNKNOWN_VALUE)

        return voice

    @classmethod
    def getSpeed(cls):
        speed = cls.getSetting(Settings.SPEED, cls.speedConstraints[1])
        speed = int(speed)
        if speed not in range(cls.speedConstraints[0], cls.speedConstraints[2] + 1):
            speed = cls.speedConstraints[1]
        return speed

    @classmethod
    def getPitch(cls):
        pitch = cls.getSetting(Settings.PITCH, cls.pitchConstraints[1])
        pitch = int(pitch)
        if pitch not in range(cls.pitchConstraints[0], cls.pitchConstraints[2] + 1):
            pitch = cls.pitchConstraints[1]
        return pitch

    @classmethod
    def getVolume(cls):
        volume = cls.getSetting(Settings.VOLUME, cls.volumeConstraints[1])
        volume = int(volume)
        if volume not in range(cls.volumeConstraints[0], cls.volumeConstraints[2] + 1):
            volume = cls.volumeConstraints[1]
        return volume

    @classmethod
    def getSetting(cls, key, default=None):
        """
        Gets a setting from addon's settings.xml

        A convenience method equivalent to Settings.getSetting(key + '.'. + cls.provider,
        default, useFullSettingName).

        :param key:
        :param default:
        :param useFullSettingName:
        :return:
        """
        fully_qualified_key = key
        if key not in Settings.TOP_LEVEL_SETTINGS:
            fully_qualified_key = '{}.{}'.format(key, cls.provider)

        if default is None:
            default = cls.get_setting_default(key)

        return Settings.getSetting(fully_qualified_key, default)

        # cls._loadedSettings[fully_qualified_key] = Settings.getSetting(
        #     fully_qualified_key, default)
        # return cls._loadedSettings[fully_qualified_key]

    @classmethod
    def setSetting(cls,
                   key: str,
                   value: Union[None, str, List, bool, int, float]
                   ) -> bool:
        """
        Saves a setting to addon's settings.xml

        A convenience method for Settings.setSetting(key + '.' + cls.provider, value)

        :param key:
        :param value:
        :return:
        """
        if (not cls.isSettingSupported(key)
                and cls._logger.isEnabledFor(BasicLogger.WARNING)):
            cls._logger.warning('Setting: {}, not supported by voicing engine: {}'
                                .format(key, cls.get_provider_name()))
        fully_qualified_key = key
        if key not in Settings.TOP_LEVEL_SETTINGS:
            fully_qualified_key = '{}.{}'.format(key, cls.provider)
        previous_value = Settings.getSetting(fully_qualified_key, None,
                                             setting_type=type(value))
        changed = False
        if previous_value != value:
            changed = True
        Settings.setSetting(fully_qualified_key, value)
        return changed

    @classmethod
    def get_provider_name(cls):
        return cls.provider  # TODO: Change to backend_id

    def insertPause(self, ms=500):
        """Insert a pause of ms milliseconds

        May be overridden by sublcasses. Default implementation sleeps for ms.
        """
        xbmc.sleep(ms)

    def isSpeaking(self):
        """Returns True if speech engine is currently speaking, False if not
        and None if unknown

        Subclasses should override this respond accordingly
        """
        return None

    def getWavStream(self, text):
        """Returns an open file like object containing wav data

        Subclasses should override this to provide access to functions
        that require this functionality
        """
        return None

    def update(self):
        """Called when the user has changed a setting for this backend

        Subclasses should override this to react to user changes.
        """
        pass

    def stop(self):
        """Stop all speech, implicitly called when close() is called

        Subclasses should override this to respond to requests to stop speech.
        Default implementation does nothing.
        """
        pass

    def close(self):
        """Close the speech engine

        Subclasses should override this to clean up after themselves.
        Default implementation does nothing.
        """
        pass

    def _update(self):
        changed = self._updateSettings()
        if changed:
            return self.update()

    def _updateSettings(self):
        if not self.settings:
            return None
        # if not hasattr(self, '_loadedSettings'):
        #    self._loadedSettings = {}
        changed = False
        # for s in self.settings:
        #    old = self._loadedSettings.get(s)
        #    new = type(self).getSetting(s)
        #    if old is not None and new != old:
        #        changed = True
        return changed

    def _stop(self):
        self.stop()

    def _close(self):
        self._closed = True
        self._stop()
        self.close()

    @classmethod
    def _available(cls):
        if cls.broken and Settings.getSetting(Settings.DISABLE_BROKEN_BACKENDS,
                                              True):
            return False
        return cls.available()

    @staticmethod
    def available():
        """Static method representing the the speech engines availability

        Subclasses should override this and return True if the speech engine is
        capable of speaking text in the current environment.
        Default implementation returns False.
        """
        return False


class ThreadedTTSBackend(TTSBackendBase):
    """A threaded speech engine backend

    Handles all the threading mechanics internally.
    Subclasses must at least implement the threadedSay() method, and can use
    whatever means are available to speak text.
    The say() and sayList() and insertPause() methods are not meant to be overridden.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = module_logger.getChild(type(self).__name__)  # type: BasicLogger
        self.active = True
        self._threadedIsSpeaking = False
        self.queue = queue.Queue()
        self.thread = threading.Thread(
            target=self._handleQueue, name='TTSThread: %s' % self.provider)
        self.thread.start()
        self.process = None

    def _handleQueue(self):
        if type(self)._logger.isEnabledFor(DEBUG):
            self._logger.debug('Threaded TTS Started: {0}'.format(self.provider))

        while self.active and not my_monitor.abortRequested():
            try:
                text = self.queue.get(timeout=0.5)
                self.queue.task_done()
                if isinstance(text, int):
                    time.sleep(text / 1000.0)
                else:
                    self._threadedIsSpeaking = True
                    self.threadedSay(text)
                    self._threadedIsSpeaking = False
            except queue.Empty:
                # self._logger.debug_verbose('queue empty')
                pass
        if type(self)._logger.isEnabledFor(DEBUG):
            self._logger.debug('Threaded TTS Finished: {0}'.format(self.provider))

    def _emptyQueue(self):
        try:
            if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
                self._logger.debug_verbose('_emptyQueue')
            while True:
                self.queue.get_nowait()
                self.queue.task_done()
        except queue.Empty:
            if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
                self._logger.debug_verbose('_emptyQueue is empty')
            return

    def say(self, text, interrupt=False, preload_cache=False):
        if not self.active:
            return
        if interrupt:
            self._stop()
        self.queue.put_nowait(text)

    def sayList(self, texts, interrupt=False):
        if interrupt:
            self._stop()
        self.queue.put_nowait(texts.pop(0))
        for t in texts:
            self.insertPause()
            self.queue.put_nowait(t)

    def isSpeaking(self):
        return self.active and (self._threadedIsSpeaking or not self.queue.empty())

    def _stop(self):
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception as e:
                pass
            finally:
                self.process = None

        self._emptyQueue()
        super()._stop()

    def insertPause(self, ms=500):
        self.queue.put(ms)

    def threadedSay(self, text):
        """Method accepting text to be spoken

        Subclasses must override this method and should speak the unicode text.
        Speech interruption is implemented in the stop() method.
        """
        raise Exception('Not Implemented')

    def _close(self):
        self.active = False
        super()._close()
        self._emptyQueue()


class SimpleTTSBackendBase(ThreadedTTSBackend):
    WAVOUT = 0
    ENGINESPEAK = 1
    PIPE = 2
    canStreamWav = True
    player_handler_class: Type[audio.BasePlayerHandler] = audio.WavAudioPlayerHandler
    """Handles speech engines that output wav files

    Subclasses must at least implement the runCommand() method which should
    save a wav file to outFile and/or the runCommandAndSpeak() method which
    must play the speech directly.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._logger = module_logger.getChild(type(self).__name__)  # type: BasicLogger
        self._simpleIsSpeaking = False
        self.mode = None
        player = type(self).getSetting(Settings.PLAYER)
        self.player_handler = type(self).player_handler_class(player)

    @staticmethod
    def isSupportedOnPlatform():
        """
        This O/S supports this engine/backend

        :return:
        """
        return False

    @staticmethod
    def isInstalled():
        """
        This engine/backend is installed and configured on the O/S.

        :return:
        """
        return False

    def setMode(self, mode):
        assert isinstance(mode, int), 'Bad mode'
        if mode == self.PIPE:
            if self.player_handler.canSetPipe():
                if type(self)._logger.isEnabledFor(DEBUG):
                    type(self)._logger.debug('Mode: PIPE')
            else:
                mode = self.WAVOUT
        self.mode = mode
        if mode == self.WAVOUT:
            if type(self)._logger.isEnabledFor(DEBUG):
                type(self)._logger.debug('Mode: WAVOUT')
        elif mode == self.ENGINESPEAK:
            audio.load_snd_bm2835()
            if type(self)._logger.isEnabledFor(DEBUG):
                type(self)._logger.debug('Mode: ENGINESPEAK')

    def get_player_handler(self) -> audio.AudioPlayer:
        return self.player_handler

    def setPlayer(self, preferred):
        return self.player_handler.setPlayer(preferred)

    def setSpeed(self, speed):
        self.player_handler.setSpeed(speed)

    def setVolume(self, volume):
        self.player_handler.setVolume(volume)

    def runCommand(self, text, outFile):
        """Convert text to speech and output to a .wav file

        If using WAVOUT mode, subclasses must override this method
        and output a .wav file to outFile, returning True if a file was
        successfully written and False otherwise.
        """
        raise Exception('Not Implemented')

    def runCommandAndSpeak(self, text):
        """Convert text to speech and output directly

        If using ENGINESPEAK mode, subclasses must override this method
        and speak text and should block until speech is complete.
        """
        raise Exception('Not Implemented')

    def runCommandAndPipe(self, text):
        """Convert text to speech and pipe to audio player

        If using PIPE mode, subclasses must override this method
        and return an open pipe to wav data
        """
        raise Exception('Not Implemented')

    def get_path_to_voice_file(self, text_to_voice, use_cache=False):
        exists = False
        voice_file = self.player_handler.getOutFile(
            text_to_voice, use_cache=use_cache)
        if VoiceCache.is_cache_sound_files(type(self)):

            # TODO: Remove HACK

            _, extension = os.path.splitext(voice_file)
            voice_file, exists = VoiceCache.get_sound_file_path(text_to_voice,
                                                                extension)
            self.player_handler.outFile = voice_file
        return voice_file, exists

    def get_voice_from_cache(self, text_to_voice, use_cache=False):
        voiced_text = None
        voice_file = None
        if VoiceCache.is_cache_sound_files(type(self)):
            voice_file = self.player_handler.getOutFile(text_to_voice,
                                                        use_cache=use_cache)

            # TODO: Remove HACK

            _, extension = os.path.splitext(voice_file)
            voice_file, voiced_text = VoiceCache.get_text_to_speech(text_to_voice,
                                                                    extension)
            self.player_handler.outFile = voice_file
        return voice_file, voiced_text

    def getWavStream(self, text):
        fpath = os.path.join(utils.getTmpfs(), 'speech.wav')
        if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
            type(self)._logger.debug_verbose('tmpfile: ' + fpath)

        self.runCommand(text, fpath)
        return open(fpath, 'rb')

    def config_mode(self):
        player_id = self.player_handler._player.ID
        if player_id == BuiltInAudioPlayer.ID:
            mode = self.ENGINESPEAK
        elif type(self).getSetting(Settings.PIPE):
            mode = self.PIPE
        else:
            mode = self.WAVOUT

        self.setMode(mode)

    def threadedSay(self, text):
        if not text:
            return
        try:
            self.config_mode()
            if self.mode == self.WAVOUT:
                outFile = self.player_handler.getOutFile(text)
                if not self.runCommand(text, outFile):
                    return
                self.player_handler.play()
            elif self.mode == self.PIPE:
                source = self.runCommandAndPipe(text)
                if not source:
                    return
                self.player_handler.pipeAudio(source)
            else:
                self._simpleIsSpeaking = True
                self.runCommandAndSpeak(text)
                self._simpleIsSpeaking = False
        except Exception as e:
            self._logger.exception(e)

    def isSpeaking(self):
        return (self._simpleIsSpeaking or self.player_handler.isPlaying()
                or ThreadedTTSBackend.isSpeaking(self))

    @classmethod
    def get_players(cls, include_builtin: bool = True) -> List[Players]:
        ret = []
        for p in cls.player_handler_class.getAvailablePlayers(include_builtin=include_builtin):
            ret.append(p.ID)
        return ret

    def _stop(self):
        self.player_handler.stop()
        ThreadedTTSBackend._stop(self)

    def _close(self):
        ThreadedTTSBackend._close(self)
        self.player_handler.close()


class LogOnlyTTSBackend(TTSBackendBase):
    provider = 'log'
    displayName = 'Log'
    _logger = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self).__name__)  # type: BasicLogger

    @staticmethod
    def isSupportedOnPlatform():
        return True

    @staticmethod
    def isInstalled():
        return LogOnlyTTSBackend.isSupportedOnPlatform()

    def say(self, text, interrupt=False, preload_cache=False):
        if type(self)._logger.isEnabledFor(DEBUG):
            type(self)._logger.debug(
                'say(Interrupt={1}): {0}'.format(repr(text), interrupt))

    @staticmethod
    def available():
        return True
