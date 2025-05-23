# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilities import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceType
from common import *
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import AudioType, Players

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class SOXAudioPlayer(SubprocessAudioPlayer):
    ID = Players.SOX
    service_id = ID
    # name = 'SOX'
    _availableArgs = ('sox', '--version')
    _playArgs = ('play', '-q', None)
    _pipeArgs = ('play', '-q', '-')
    _speedArgs = ('tempo', '-s', None)
    _speedMultiplier: Final[float] = 0.01
    _volumeArgs = ('vol', None, 'dB')
    kill = True
    _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _supported_output_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_id, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    def __init__(self):
        super().__init__()

    def playArgs(self, path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            args[args.index(None)] = str(self.volume)
        if self.speed:
            args.extend(self._speedArgs)
            args[args.index(None)] = self.speedArg(self.speed)
        self._logger.debug_v(f'args: {" ".join(args)}')
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
                                stderr=subprocess.STDOUT, universal_newlines=True,
                                encoding='utf-8')
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return False
        return True

    @classmethod
    def register(cls):
        PlayerIndex.register(SOXAudioPlayer.ID, SOXAudioPlayer)
        BaseServices.register(cls)
