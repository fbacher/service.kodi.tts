# coding=utf-8
from __future__ import annotations  # For union operator |

from queue import Empty as EmptyQueue, Full as FullQueue, Queue
from threading import Thread

from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceID
from common import *
from common.base_services import BaseServices, IServices
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList

MY_LOGGER = BasicLogger.get_logger(__name__)


class TTSQueueData:
    # callable, **kwargs,
    data: Tuple[callable, Dict[str, Any]] = None

    def __init__(self, call: callable, **kwargs) -> None:
        self.data = (call, kwargs)

    def getData(self) -> Tuple[callable, Dict[str, Any]]:
        return self.data

    def get_callable(self) -> callable:
        return self.data[0]

    def get_kwargs(self) -> Dict[str, Any]:
        return self.data[1]


class TTSQueue(Queue):

    def __init__(self, maxsize: int = 50):
        super().__init__(maxsize)


class WorkerThread:

    def __init__(self, thread_name: str, task: callable, **kwargs):
        clz = type(self)
        self.queue: TTSQueue = TTSQueue()
        self.queueFullCount: int = 0
        self.queueCount: int = 0
        self.started: bool = False
        self.idle_count: int = 0
        self.task: callable = task
        self.kwargs = kwargs

        self.thread = Thread(target=self.process_queue, name=thread_name)
        self.thread_started: bool = False

    def add_to_queue(self, tts_data: TTSQueueData) -> None:
        clz = type(self)
        try:
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'tts_data: {tts_data.data}')
            if not self.thread_started:
                self.thread.start()
                self.thread_started = True
            self.queue.put_nowait(tts_data)
            self.queueCount += 1
        except FullQueue as e:
            self.queueFullCount += 1
        except Exception as e:
            MY_LOGGER.exception('')

    def process_queue(self):
        clz = type(self)
        data: TTSQueueData | None = None
        try:
            delay: float = 0.05
            while not Monitor.wait_for_abort(delay):
                try:
                    data = self.queue.get_nowait()
                    self.queue.task_done()
                    delay = 0.05
                    self.idle_count = 0
                except EmptyQueue as e:
                    self.idle_count += 1
                    if self.idle_count > (5.0 / 0.05):
                        delay = 0.10
                    continue
                try:
                    kwargs: Dict[str, Any] = data.get_kwargs()
                    if kwargs['state'] == 'play_file':
                        player_key: ServiceID = kwargs.get('player_key')
                        player: IPlayer = PlayerIndex.get_player(player_key.service_id)
                        phrase: Phrase = kwargs.get('phrase')
                        engine_key: ServiceID = kwargs.get('engine_key')
                        # MY_LOGGER.debug(f'player_key: {player_key} '
                        #                 f'engine_key: {engine_key}')
                        try:
                            engine: IServices = BaseServices.get_service(engine_key)
                            engine.say_phrase(phrase)
                        except Exception as e:
                            MY_LOGGER.exception('')
                        continue

                    if kwargs['state'] == 'seed_cache':
                        engine_key: ServiceID = kwargs.get('engine_key')
                        phrases: PhraseList = kwargs.get('phrases')
                        try:
                            engine: IServices = BaseServices.get_service(engine_key)
                            engine.seed_text_cache(phrases)
                        except Exception as e:
                            MY_LOGGER.exception('')
                except AbortException as e:
                    return  # Exit thread
                except Exception as e:
                    MY_LOGGER.exception('')

        except AbortException as e:
            pass  # Let thread exit
        except Exception as e:
            MY_LOGGER.exception('')
        finally:
            pass
        return
