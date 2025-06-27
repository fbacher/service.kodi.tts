# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.service_unavailable_exception import ServiceUnavailable
from common.base_services import BaseServices
from common.phrases import Phrase

"""
Decides whether phrases should be discarded due to:
   * expiration: Phrases become expired when, due to user input, the
     phrase is no longer relevant. Perhaps the user skipped to the next
     menu item, or movie title. They want to hear about the new item,
     not the old
   * Configuration: If a TTS engine or player is changed then all
     prior phrases are discarded.

Also responsible for shutting down players and engines that are not
currently in use.
"""
from backends.players.iplayer import IPlayer
from backends.settings.service_types import ServiceID, ServiceType
from common.logger import *
from common.setting_constants import PlayerMode
from common.settings import Settings

MY_LOGGER = BasicLogger.get_logger(__name__)


class PhraseManager:

    current_engine: ITTSBackendBase = None
    _class_name: str = None
    _prev_engine: ServiceID | None = None
    _prev_player_key: ServiceID | None = None
    _prev_player_mode: PlayerMode | None = None

    @classmethod
    def prepare_to_say(cls, engine_key: ServiceID, phrase: Phrase) -> IPlayer:
        """
        In preperation of saying something, does anything need to be done about
        the player, engine, etc.?

        The objectives here are:
          1) ensure that voicings don't step on each other.
          2) that engines, players, etc. stay in a good state
          4) that excess resets, kills and restarts are avoided

        When you have a single engine and player involved, things are fairly
        straightforward. Run all phrases through a queue to guarantee order and to
        not start playing something while something else is playing.

        Things get more complicated when the players, engines or player_modes change,
        or when a transcoder is added to the mix, or some other complication.
        Fortunately this is a rarity, but still a real problem.

        It is possible to have two players talking at the same time: 1) when the
        player changes, 2) when the player_mode changes (slave_mode has different
        latencies and uses a long-running process to play multple files; engine_speak
        mode doesn't use a player and may speak prior to a current player is done;
        3) possibly other circumstances. Safest just to expire all prior phrases and to
        kill any active player.

        Also, if an engine changes, all prior phrases must be expired. Even if
        using the same player.

        :param engine_key: key for identifying the engine Settings.get_player
                             will adjust the engine's service_key appropriately.
        :param phrase: a phrase about to be spoken.
        """
        new_player_key: ServiceID = Settings.get_player(engine_key)
        new_player_mode: PlayerMode = Settings.get_player_mode(engine_key)
        flush_player: bool = False
        stop_engine: bool = False
        stop_speech: bool = False
        stop_prev_player: bool = False
        restart_new_player: bool = False
        kill_player: bool = False

        player_changed: bool = False
        player_mode_changed: bool = False
        engine_changed: bool = False

        # First look at the player
        if cls._prev_player_key is None or cls._prev_player_key != new_player_key:
            player_changed = True
        if cls._prev_player_mode is None or cls._prev_player_mode != new_player_mode:
            player_mode_changed = True
        if cls._prev_engine is None or cls._prev_engine != engine_key:
            engine_changed = True

        if player_changed and cls._prev_player_key is not None:
            # Tell old player to stop, which generally means to kill the process,
            stop_speech = True
            stop_prev_player = True

        if player_mode_changed and cls._prev_player_mode is not None:
            stop_speech = True
            stop_prev_player = True

        if not player_changed and player_mode_changed:
            restart_new_player = True

        if engine_changed and cls._prev_engine is not None:
            # Probably should tell the engine to go to sleep or something
            stop_engine = True
            if cls._prev_player_mode != PlayerMode.ENGINE_SPEAK:
                stop_prev_player = True
            if not player_changed and new_player_mode == PlayerMode.SLAVE_FILE:
                flush_player = True

        if phrase is not None and phrase.get_interrupt():
            if not player_changed:
                if new_player_mode in (PlayerMode.SLAVE_FILE, PlayerMode.SLAVE_PIPE):
                    flush_player = True
        if stop_prev_player and cls._prev_player_mode == PlayerMode.ENGINE_SPEAK:
            stop_prev_player = False  # None to stop
            stop_engine = True        # Only way to stop current voicing

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'old player: {cls._prev_player_key} '
                            f'prev player_mode: {cls._prev_player_mode} '
                            f'prev_engine: {cls._prev_engine}')
            MY_LOGGER.debug(f'New player: {new_player_key} '
                            f'new player_mode: {new_player_mode} '
                            f'new engine: {engine_key}')
            MY_LOGGER.debug(f'engine_changed: {engine_changed} '
                            f'player_changed: {player_changed} '
                            f'player_mode_changed: {player_mode_changed}')
            MY_LOGGER.debug(f'stop_speech: {stop_speech} '
                            f'stop_prev_player: {stop_prev_player} '
                            f'stop_engine: {stop_engine} '
                            f'restart_new_player: {restart_new_player} '
                            f'flush_player: {flush_player}')

        new_player: IPlayer = BaseServices.get_service(new_player_key)
        if stop_speech:
            MY_LOGGER.debug(f'stop_speech set, but what do I do?')
            pass  # define what this means
        if stop_prev_player:
            # Stop the old player. Normally this means to kill the process
            MY_LOGGER.debug(f'stop_prev_player Killing old_player: '
                            f'{cls._prev_player_key}')
            old_player: IPlayer = BaseServices.get_service(cls._prev_player_key)
            old_player.stop_player(purge=True, keep_silent=True, kill=True)
        if flush_player:
            MY_LOGGER.debug(f'flush_player kill: {kill_player}')
            new_player.stop_player(purge=True, keep_silent=False, kill=kill_player)
        if stop_engine:
            MY_LOGGER.debug(f'stop_engine')
            engine: BaseServices = BaseServices.get_service(cls._prev_engine)
            engine.stop()

        cls._prev_player_mode = new_player_mode
        cls._prev_player_key = new_player_key
        cls._prev_engine = engine_key

        return new_player

    @classmethod
    def handle_interrupt(cls, engine_key: ServiceID, phrase: Phrase) -> IPlayer:
        """
        If this phrase has an interrupt, then purge any previous speech before
        voicing this phrase.

        :param engine_key: key for identifying the engine Settings.get_player
                             will adjust the engine's service_key appropriately.
        :param phrase: a phrase about to be spoken.
        """
        new_player_key: ServiceID = Settings.get_player(engine_key)
        new_player_mode: PlayerMode = Settings.get_player_mode(engine_key)
        flush_player: bool = False
        stop_engine: bool = False
        #  stop_speech: bool = False
        restart_new_player: bool = False
        kill_player: bool = False

        if phrase is not None and phrase.get_interrupt():
            if new_player_mode in (PlayerMode.SLAVE_FILE, PlayerMode.SLAVE_PIPE):
                flush_player = True
            elif cls._prev_player_mode == PlayerMode.ENGINE_SPEAK:
                stop_engine = True  # Only way to stop current voicing

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'kill_player: {kill_player} '
                            f'flush_player: {flush_player}')

        new_player: IPlayer = BaseServices.get_service(new_player_key)
        # if stop_speech:
        #     MY_LOGGER.debug(f'stop_speech set, but what do I do?')
        #     pass  # define what this means
        if flush_player:
            MY_LOGGER.debug(f'flush_player kill: {kill_player}')
            new_player.stop_player(purge=True, keep_silent=False, kill=kill_player)
        if stop_engine:
            MY_LOGGER.debug(f'stop_engine')
            engine: BaseServices = BaseServices.get_service(cls._prev_engine)
            engine.stop()

        # cls._prev_player_mode = new_player_mode
        # cls._prev_player_key = new_player_key
        # cls._prev_engine = engine_key

        return new_player
