# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import pathlib
import subprocess

import xbmc

from backends.audio.sound_capabilities import SoundCapabilities
from common import *

from backends.settings.service_types import (ServiceType, TranscoderType,
                                             WaveToMpg3Transcoder)
from common.logger import *
from common.monitor import Monitor
from common.setting_constants import AudioType
from common.simple_run_command import SimpleRunCommand

MY_LOGGER = BasicLogger.get_logger(__name__)


class TransCode:

    _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _supported_output_formats: List[AudioType] = [AudioType.MP3, AudioType.WAV]
    _provides_services: List[ServiceType] = [ServiceType.TRANSCODER]
    SoundCapabilities.add_service(TranscoderType.LAME,
                                  _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    @staticmethod
    def transcode(trans_id: str,
                  input_path: pathlib.Path,
                  output_path: pathlib.Path,
                  remove_input: bool = False) -> bool:
        """
        Transcodes a .wav file to an .mpg3 file

        :param trans_id: The Transcoder to use. See WaveToMpg3Transcoder
        :param input_path: File to transcode
        :param output_path: File to produce
        :param remove_input: If True, then remove input_path IF transcode
                             is successful
        :return: True if transcode was successful, otherwise False
        """
        success: bool = True
        args: List[str] = []
        # transcoder: TranscoderType = TranscoderType[trans_id]
        MY_LOGGER.debug(f'trans_id: {trans_id} LAME: {TranscoderType.LAME.value} '
                        f'== {trans_id == TranscoderType.LAME.value} '
                        f'input_path: {input_path} '
                        f'output_path: {output_path}')
        if trans_id == TranscoderType.MPLAYER.value:
            args = ['mencoder', '-really_quiet',
                    '-af', 'volume=-10', '-i', input_path,
                    '-o', output_path]
        elif trans_id == TranscoderType.FFMPEG.value:
            args = ['ffmpeg', '-loglevel', 'error', '-i',
                    input_path, '-filter:a', 'speechnorm',
                    '-acodec', 'libmp3lame',
                    output_path]

        elif trans_id == TranscoderType.LAME.value:
            MY_LOGGER.debug(f'I\'m LAME')
            # --scale 1.00 amplifies by 1
            args: List[str] = []
            if output_path.suffix == '.mp3':
                args = ['lame', '--scale', '1.00',
                        '--replaygain-accurate', input_path,
                        output_path]
            elif output_path.suffix == '.wav':
                args = ['lame', '--scale', '1.00',
                        '--replaygain-accurate', '--decode', input_path,
                        output_path]
            else:
                MY_LOGGER.debug(f'Unknown conversion: {input_path} to {output_path}')
                return False
            MY_LOGGER.debug(f'args: {args}')

        MY_LOGGER.debug(f'args: {args}')
        rc: int = TransCode.run_trivial_command(args, time_limit=0.5)
        if rc == 0 and remove_input:
            # input_path.unlink(missing_ok=True)
            pass
        return rc == 0

    @staticmethod
    def run_trivial_command(args: List[str], time_limit: float) -> int:
        rc: int = 0
        env = os.environ.copy()
        try:
            if xbmc.getCondVisibility('System.Platform.Windows'):
                # Prevent console for command from opening
                #
                # Here, we keep stdout & stderr separate and combine the output in the
                # log. Need to change to be configureable: separate, combined at
                # process level (stderr = subprocess.STDOUT), devnull or pass through
                # via pipe and don't log

                MY_LOGGER.debug(f'Starting cmd args: {args}')
                completed_proc: subprocess.CompletedProcess
                completed_proc = subprocess.run(args, stdin=subprocess.DEVNULL,
                                                capture_output=False,
                                                timeout=time_limit,
                                                shell=False,
                                                env=env,
                                                #  encoding='cp1252',  # 'utf-8',
                                                close_fds=True,
                                                creationflags=subprocess.DETACHED_PROCESS)
            else:
                completed_proc = subprocess.run(args, stdin=subprocess.DEVNULL,
                                                capture_output=False,
                                                shell=False,
                                                env=env,
                                                close_fds=True)
            rc = completed_proc.returncode
            Monitor.exception_on_abort()
        except AbortException as e:
            rc = 99
        except Exception as e:
            MY_LOGGER.exception('')
            rc = 10
        return rc
