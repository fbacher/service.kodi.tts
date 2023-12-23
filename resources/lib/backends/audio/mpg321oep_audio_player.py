import errno
import os
import shutil
import subprocess
import sys

from backends.audio.base_audio import SubprocessAudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceType
from common import utils
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import Players
from common.typing import *

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class Mpg321OEPiAudioPlayer(SubprocessAudioPlayer):
    #
    #  Plays using ALSA
    #
    ID = Players.MPG321_OE_PI
    service_ID = ID
    # name = 'mpg321 OE Pi'

    _supported_input_formats: List[str] = [SoundCapabilities.MP3]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
                self.__class__.__name__)  # type: module_logger
        self._wavProcess = None
        try:
            import OEPiExtras
            OEPiExtras.init()
            self.env = OEPiExtras.getEnvironment()
            self.active = True
        except ImportError:
            self._logger.debug('Could not import OEPiExtras')

    def canSetVolume(self):
        return True

    def canSetPitch(self):  # Settings implies false, but need to test
        return False

    def canSetPipe(self) -> bool:
        return True

    def pipe(self, source):  # Plays using ALSA
        self._wavProcess = subprocess.Popen('mpg321 - --wav - | aplay',
                                            stdin=subprocess.PIPE,
                                            stdout=(
                                                open(os.path.devnull, 'w')),
                                            stderr=subprocess.STDOUT,
                                            env=self.env, shell=True,
                                            universal_newlines=True)
        try:
            shutil.copyfileobj(source, self._wavProcess.stdin)
        except AbortException:
            reraise(*sys.exc_info())
        except IOError as e:
            if e.errno != errno.EPIPE:
                module_logger.error('Error piping audio')
        except:
            module_logger.error('Error piping audio')
        source.close()
        self._wavProcess.stdin.close()
        while self._wavProcess.poll() is None and self.active:
            utils.sleep(10)

    def play(self, path):  # Plays using ALSA
        self._wavProcess = subprocess.Popen(f'mpg321 --wav - "{path}" | aplay',
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

    @classmethod
    def register(cls):
        PlayerIndex.register(Mpg321OEPiAudioPlayer.ID, Mpg321OEPiAudioPlayer)
        BaseServices.register(cls)
