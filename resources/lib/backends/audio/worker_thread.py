import sys

from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.setting_properties import SettingsProperties
from common.base_services import BaseServices, IServices
from common.logger import BasicLogger
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.typing import *
from threading import Thread, ThreadError
from queue import Queue
from queue import Empty as EmptyQueue
from queue import Full as FullQueue


module_logger = BasicLogger.get_module_logger(module_path=__file__)


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
    _logger: BasicLogger = None

    def __init__(self, thread_name: str, task: callable, **kwargs):
        clz = type(self)
        self.queue: TTSQueue = TTSQueue()
        self.queueFullCount: int = 0
        self.queueCount: int = 0
        self.started: bool = False
        self.idle_count: int = 0
        self.task: callable = task
        self.kwargs = kwargs

        self.thread = Thread(target=self.process_queue, name=thread_name )
        self.thread_started: bool = False
        if clz._logger is None:
            clz._logger = module_logger.getChild(self.__class__.__name__)
        pass

    def interrupt(self):
        self.empty_queue()

    def add_to_queue(self, tts_data: TTSQueueData) -> None:
        clz = type(self)
        try:
            if not self.thread_started:
                self.thread.start()
                self.thread_started = True
            self.queue.put_nowait(tts_data)
            self.queueCount += 1
        except FullQueue as e:
            self.queueFullCount += 1
        except Exception as e:
            clz._logger.exception('')

    def empty_queue(self) -> None:
        clz = type(self)
        try:
            while self.queue.not_empty:
                data = self.queue.get_nowait()
                self.queue.task_done()
        except EmptyQueue as e:
            pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            clz._logger.exception('')

    def process_queue(self):
        clz = type(self)
        data: TTSQueueData = None
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
                        player_id: str = kwargs.get('player_id')
                        player: IPlayer = PlayerIndex.get_player(player_id)
                        phrase: Phrase = kwargs.get('phrase')
                        engine_id: str = kwargs.get('engine_id')
                        try:
                            player.init(engine_id)
                        except Exception as e:
                            clz._logger.exception('')
                        player.play(phrase)
                        continue
                    if kwargs['state'] == 'seed_cache':
                        engine_id: str = kwargs.get('engine_id')
                        phrases: PhraseList = kwargs.get('phrases')
                        try:
                            engine: IServices = BaseServices.getService(engine_id)
                            engine.seed_text_cache(phrases)
                        except Exception as e:
                            clz._logger.exception('')
                except AbortException as e:
                    return  #  Exit thread
                except Exception as e:
                    clz._logger.exception('')

        except AbortException as e:
            pass # Let thread exit
        except Exception as e:
            clz._logger.exception('')
        finally:
            pass
        return
