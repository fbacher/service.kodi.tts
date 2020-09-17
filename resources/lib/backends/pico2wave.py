# -*- coding: utf-8 -*-
import os, subprocess
from typing import Any, List, Union, Type

from backends.audio import BasePlayerHandler, WavAudioPlayerHandler
from backends.base import SimpleTTSBackendBase
from common.constants import Constants
from common.logger import LazyLogger
from common.system_queries import SystemQueries
from common.messages import Messages
from common.setting_constants import Backends, Languages, Genders, Players
from common.settings import Settings

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = LazyLogger.get_addon_module_logger().getChild(
        'lib.backends')
else:
    module_logger = LazyLogger.get_addon_module_logger()


class Pico2WaveTTSBackend(SimpleTTSBackendBase):
    provider = Backends.PICO_TO_WAVE_ID
    displayName = 'pico2wave'
    speedConstraints = (20,100,200,True)
    player_handler_class: Type[BasePlayerHandler] = WavAudioPlayerHandler

    settings = {Settings.LANGUAGE: '',
                Settings.PLAYER: None,
                Settings.SPEED: 0,
                Settings.VOLUME: 0
                }

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(self.__class__.__name__)  # type: LazyLogger

        self.language = None
        self.stop_processing = False
        self.update()

    @classmethod
    def isSupportedOnPlatform(cls):
        return SystemQueries.isLinux() or SystemQueries.isAndroid()

    @classmethod
    def isInstalled(cls):
        installed = False
        if cls.isSupportedOnPlatform():
            installed = cls.available()
        return installed

    def runCommand(self, text_to_voice, dummy):
        self.process = None
        self.stop_processing = False

        # If caching is enabled, voice_file will be in the cache.

        voice_file = self.player_handler.getOutFile(text_to_voice, use_cache=False)

        self._logger.debug_verbose('pico2wave.runCommand text: ' + text_to_voice +
                         ' language: ' + self.language)
        args = ['pico2wave']
        if self.language:
            args.extend(['-l', type(self).getLanguage()])
        args.extend(['-w', '{0}'.format(voice_file), '{0}'.format(text_to_voice)])
        try:
            if not self.stop_processing:
                with subprocess.call(args, universal_newlines=True) as self.process:
                    pass
                self.process = None
        except Exception as e:
            self.process = None
            self._logger.error('Failed to download voice file: {}'.format(str(e)))
            try:
                os.remove(voice_file)
            except Exception as e2:
                pass
            return False

        if self.stop_processing:
            self._logger.debug_verbose('runCommand stop_processing')
            return False

        return True

    def update(self):
        pass

    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'language':
            try:
                out = subprocess.check_output(['pico2wave','-l','NONE','-w','/dev/null','X'],
                                              stderr=subprocess.STDOUT,
                                              universal_newlines=True)
            except subprocess.CalledProcessError as e:
                out = e.output
            if 'languages:' not in out:
                return None

            languages = [(v, v) for v in
                         out.split('languages:', 1)[-1].split('\n\n')[0].strip(
                             '\n').split('\n')]

            default_locale = Constants.LOCALE.lower().replace('_', '-')
            default_language = languages[0][0]
            for language, language_id in languages:
                if default_locale == language_id:
                    default_language = default_locale

            return languages, default_language

        elif setting == Settings.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            players = cls.get_players(include_builtin=False)
            default_player = cls.get_setting_default(Settings.PLAYER)

            return players, default_player

        return None

    @classmethod
    def available(cls):
        try:
            subprocess.call(['pico2wave', '--help'],  universal_newlines=True,
                            stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return False
        return True
