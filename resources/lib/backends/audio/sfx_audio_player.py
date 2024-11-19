from __future__ import annotations  # For union operator |

import os
import subprocess
import sys
import tempfile
import threading
import wave
from datetime import datetime, timedelta
from logging import DEBUG
from pathlib import Path

import xbmc

from backends.audio import PLAYSFX_HAS_USECACHED
from backends.audio.base_audio import AudioPlayer
from backends.audio.sound_capabilities import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services, ServiceType
from backends.transcoders.trans import TransCode
from cache.voicecache import CacheEntryInfo, VoiceCache
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import BasicLogger, DEBUG_V
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import AudioType, Players
from common.settings import Settings

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class PlaySFXAudioPlayer(AudioPlayer, BaseServices):
    """
    SFX player simply utilzies Kodi's built-in playSFX service. It is a basic
    player. You can't change speed or other parameters.
    """
    ID = Players.SFX
    service_ID = Services.SFX_ID
    service_TYPE: str = ServiceType.PLAYER
    # name = 'XBMC PlaySFX'
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _initialized: bool = False

    def __init__(self):
        clz = type(self)
        if not clz._initialized:
            clz.register(self)
            clz._initialized = True
        super().__init__()

        self._voice_cache: VoiceCache | None = None
        self._isPlaying: bool = False
        self.event: threading.Event = threading.Event()
        self.event.clear()

    @property
    def voice_cache(self) -> VoiceCache:
        clz = PlaySFXAudioPlayer
        if self._voice_cache is None:
            self._voice_cache = VoiceCache(clz.service_ID)
        return self._voice_cache

    @classmethod
    def register(cls, what):
        PlayerIndex.register(PlaySFXAudioPlayer.ID, what)
        BaseServices.register(what)

    def doPlaySFX(self, path) -> None:
        xbmc.playSFX(path, False)

    def play(self, phrase: Phrase):
        """
        Play the voice file for the given phrase
        :param phrase: Contains information about the spoken phrase, including
        path to .wav or .mp3 file
        :return:
        """
        clz = type(self)
        success: bool = False
        audio_types: List[str]
        result: CacheEntryInfo
        result = self.voice_cache.get_path_to_voice_file(phrase, use_cache=True)
        MY_LOGGER.debug(f'result: {result}')
        audio_path: Path = result.current_audio_path
        if not result.audio_exists:
            mp3_file: Path = audio_path.with_suffix(f'.{AudioType.MP3}')
            wave_file: Path = audio_path

            try:
                #  SoundCapabilities.get_capable_services(service_ID, _provides_services,
                target_audio: AudioType
                target_audio = Settings.get_current_input_format(clz.service_ID)

                tran_id = SoundCapabilities.get_transcoder(
                        target_audio=target_audio,
                        service_id=clz.service_ID)
                if tran_id is not None:
                    MY_LOGGER.debug(f'Setting converter: {tran_id} for '
                                    f'{clz.service_ID}')
                    Settings.set_converter(tran_id, clz.service_ID)
                    x = Settings.get_converter(engine_id=clz.service_ID)
                    MY_LOGGER.debug(f'Setting converter: {x}')
            except ValueError:
                # Can not find a match. Don't recover, for now
                reraise(*sys.exc_info())

            trans_id: str = Settings.get_converter(clz.service_ID)
            MY_LOGGER.debug(f'service_id: {clz.service_ID} trans_id: {trans_id}')
            success = TransCode.transcode(trans_id=trans_id,
                                          input_path=mp3_file,
                                          output_path=wave_file,
                                          remove_input=False)
            MY_LOGGER.debug(f'success: {success} wave_file: {wave_file} mp3: {mp3_file}')
            if not success:
                MY_LOGGER.debug(f'Failed to convert to WAVE file: {mp3_file}')
                return
        stop_on_play: bool = not phrase.speak_over_kodi
        if stop_on_play:
            if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                return

        clz = type(self)
        args: List[str] = []
        try:
            phrase.test_expired()  # Throws ExpiredException
            # Use previous phrase's post_play_pause
            delay_ms = max(phrase.get_pre_pause(), self._post_play_pause_ms)
            self._post_play_pause_ms = phrase.get_post_pause()
            #  pre_silence_path: Path = phrase.pre_pause_path()
            #  post_silence_path: Path = phrase.post_pause_path()
            self._isPlaying = True
            waited: timedelta = datetime.now() - self._time_of_previous_play_ended
            # TODO: Get rid of this wait loop and use phrase pauses
            waited_ms = waited / timedelta(microseconds=1000)
            delta_ms = delay_ms - waited_ms
            if delta_ms > 0.0:
                additional_wait_needed_s: float = delta_ms / 1000.0
                MY_LOGGER.debug(f'pausing {additional_wait_needed_s} ms')
                Monitor.exception_on_abort(timeout=float(additional_wait_needed_s))
            self.doPlaySFX(str(audio_path))
            f = wave.open(str(audio_path), 'rb')
            frames = f.getnframes()
            rate = f.getframerate()
            f.close()
            duration = frames / float(rate)
            self.event.clear()
            self.event.wait(duration)
            Monitor.exception_on_abort()
        except AbortException:
            self.stop(now=True)
            reraise(*sys.exc_info())
        except ExpiredException:
            MY_LOGGER.debug('EXPIRED')
            return
        except Exception as e:
            MY_LOGGER.exception(f'{phrase.get_cache_path()}')
            return
        finally:
            try:
                if stop_on_play:
                    if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                        return
                delete_after_run: Path | None = None
                if Constants.PLATFORM_WINDOWS:
                    delete_after_run = phrase.get_cache_path()
            finally:
                self._time_of_previous_play_ended = datetime.now()
                self._isPlaying = False

    def isPlaying(self) -> bool:
        return self._isPlaying

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        """
        Stop player (most likely because current text is expired)
        Players may wish to override this method, particularly when
        the player is built-in.

        :param purge: if True, then purge any queued vocings
                      if False, then only stop playing current phrase
        :param keep_silent: if True, ignore any new phrases until restarted
                            by resume_player.
                            If False, then play any new content
        :param kill: If True, kill any player processes. Implies purge and
                     keep_silent.
                     If False, then the player will remain ready to play new
                     content, depending upon keep_silent
        :return:
        """
        self.stop()

    def stop(self, now: bool = True) -> None:
        xbmc.stopSFX()

    def close(self) -> None:
        self.stop()

    @staticmethod
    def available(ext=None) -> bool:
        return xbmc and hasattr(xbmc, 'stopSFX') and PLAYSFX_HAS_USECACHED
