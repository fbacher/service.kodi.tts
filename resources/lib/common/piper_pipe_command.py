# coding=utf-8
from __future__ import annotations  # For union operator |

import io
import os
import pathlib
import shutil
import subprocess
import sys
import threading
from enum import Enum
from subprocess import Popen

import xbmc

from common import *
from common.constants import Constants

from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList

module_logger = BasicLogger.get_logger(__name__)


class RunState(Enum):
    NOT_STARTED = 0
    RUNNING = 1
    COMPLETE = 2
    KILLED = 3
    TERMINATED = 4


class Voice:
    voices: List[Voice] = []

    """
     Index is lang or lang_country name
     ex: en_us voice1 would have two entries:
       "en" -> voice1
       "en_US" -> voice1
    """
    voices_by_lang_country: Dict[str, List[Voice]] = []

    def __init__(self, lang: str, country: str, name: str, quality: str):
        self.lang: str = lang
        self.country: str = country
        self.name: str = name
        self.quality: str = quality

    @staticmethod
    def parse(voice_spec: str) -> Voice:
        tokens: List[str] = voice_spec.split('-')
        lang: str = tokens[0]
        country: str = tokens[1]
        name: str = tokens[2]
        quality: str = tokens[3]
        voice: Voice = Voice(lang, country, name, quality)
        lang_entries = Voice.voices_by_lang_country.get(lang, [])
        lang_entries.append(voice)
        if len(country) > 0:
            lang_country_entries = Voice.voices_by_lang_country.get(f'{lang}_{country}', [])
            lang_country_entries.append(voice)
        return voice

    @classmethod
    def get_voices_by_lang_country(cls, lang: str, country: str = '') -> List[Voice] | None:
        return cls.voices_by_lang_country.get(f'{lang}_{country}', None)

    @classmethod
    def class_init(cls) -> None:
        Voice.parse('en_US-amy-medium.onnx')
        Voice.parse('en_US-kusal-medium.onnx')
        Voice.parse('en_US-ryan-high.onnx')
        Voice.parse('en_US-arctic-medium.onnx')
        Voice.parse('en_US-l2arctic-medium.onnx')
        Voice.parse('en_US-ryan-medium.onnx')
        Voice.parse('en_US-hfc_male-medium.onnx')
        Voice.parse('en_US-libritts-high.onnx')
        Voice.parse('en_US-joe-medium.onnx')
        Voice.parse('en_US-libritts_r-medium.onnx')


class PiperPipeCommand:
    """
    This implementation uses the piper binary command, which is much faster
    but perhaps less portable. There are some differences in functionality.
    The binary piper can accept json input. Unfortunately, piper doesn't process
    the json until AFTER it reaches eof, so you can't use it as a daemon very
    well. The python version process multi-line input as one voicing, no matter
    the length.

    """
    player_state: str = KodiPlayerState.VIDEO_PLAYER_IDLE
    logger: BasicLogger = None
    DEFAULT_MODEL: Final[str] = 'en_US-ryan-high.onnx'

    def __init__(self) -> None:
        """

        :param args: arguments to be passed to exec command
        """
        clz = type(self)
        PiperPipeCommand.logger = module_logger
        top: pathlib.Path = pathlib.Path('/home/fbacher/piper_env/')
        data_dir: pathlib.Path = top
        python_path: pathlib.Path = top.joinpath('bin/python3.11')
        self.model: str = PiperPipeCommand.DEFAULT_MODEL
        self.process: subprocess.Popen | None = None
        output_dir: pathlib.Path = pathlib.Path('/tmp')
        return

    def say(self, phrase: Phrase, model: str = DEFAULT_MODEL) -> bool:
        self.model = model
        clz = type(self)
        text: str = f'{phrase.get_text()}.'
        text_file: str
        voice_file_path: pathlib.Path = phrase.get_cache_path()
        output_dir: pathlib.Path
        output: pathlib.Path
        wave_path: pathlib.Path = voice_file_path.with_suffix('.wav')

        # Can send .wav to stdout via args "-f -" (not via json)
        args_cpp: List[str] = ['/home/fbacher/piper/piper',
                               '--model',
                               f'/home/fbacher/piper_cache/{self.model}',
                               '--output-file',
                               f'{wave_path}'
                               ]
        env = os.environ.copy()

        failed = False
        stdout: str = ''
        try:
            #  clz.get.debug(f'args: {args_cpp}')
            if Constants.PLATFORM_WINDOWS:
                # Prevent console for ffmpeg from opening
                #
                # Here, we keep stdout & stderr separate and combine the output in the
                # log. Need to change to be configurable: separate, combined at
                # process level (stderr = subprocess.STDOUT), devnull or pass through
                # via pipe and don't log
                self.process = subprocess.Popen(args_cpp, stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, shell=False,
                                                env=env,
                                                text=True,
                                                close_fds=True,
                                                creationflags=subprocess.DETACHED_PROCESS)
            else:
                self.process = subprocess.Popen(args_cpp, stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT,
                                                shell=False,
                                                env=env,
                                                text=True,
                                                close_fds=True)
            stdout, _ = self.process.communicate(input=text, timeout=5.0)
        except subprocess.TimeoutExpired:
            failed = True
            clz.logger.debug(f'piper command timed out')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz.logger.exception('')
            failed = True

        if failed:
            clz.logger.debug(f'failed: {failed} stdout: {stdout}')
        if failed:
            if self.process.poll() is None:
                self.process.kill()
        if self.process.poll() != 0:
            failed = True

        if failed:
            wave_path.unlink(missing_ok=True)
        return failed
