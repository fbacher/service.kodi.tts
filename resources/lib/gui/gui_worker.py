import queue
from pathlib import Path

from common.garbage_collector import GarbageCollector
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.parse_window import ParseWindow
from gui.topic_model import TopicModel  # coding=utf-8
from gui.window_model import WindowModel
import copy

from windows.window_state_monitor import WinDialog, WinDialogState, WindowStateMonitor
import sys
import threading
from typing import Callable, Dict, Final, ForwardRef, List

import xbmc
import xbmcgui

from common import AbortException, reraise
from common.logger import *
from common.monitor import Monitor
from utils import util

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class GuiWorkerQueue:
    """
    The WindowStateMonitor checks every ~1/10th of a second for changes that
    may require voicing. Everything it detects gets placed into this queue
    for triage and processing. In particular, an older event may be superseded
    by a later one, eliminating the need to voice the older one. This can save
    a lot of processing as well as making the application more responsive.
    """

    # A monotonically increasing number that is assigned to each task dispatched
    # by the queue. Used to cancel active tasks.

    sequence_number: int = 0
    canceled_sequence_number: int = -1
    _instance: 'GuiWorkerQueue' = None
    _logger: BasicLogger = None

    class QueueItem:

        def __init__(self, changed: int, focused_id: str):
            self.changed: int = changed
            self.focused_id: str = focused_id

    def __init__(self):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(self.__class__.__name__)

        # active_queue is True as long as there is a configured active_queue engine

        self.active_queue: bool = False
        self.topics_queue = queue.Queue(50)
        self.queue_processor: threading.Thread | None = None

    @classmethod
    def init(cls):
        """

        @return:
        """
        if cls._instance is None:
            cls._instance = GuiWorkerQueue()
            cls._instance.active_queue = True
        if cls._instance.queue_processor is None:
            cls._instance.queue_processor = threading.Thread(
                    target=cls._instance._handleQueue, name=f'GuiWorkerQueue')
            cls._instance._logger.debug(f'Starting queue_processor GuiWorkerQueue')
            cls._instance.queue_processor.start()
            GarbageCollector.add_thread(cls._instance.queue_processor)

    @classmethod
    @property
    def queue(cls) -> 'GuiWorkerQueue':
        return cls._instance

    def _handleQueue(self):
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG):
            self._logger.debug(f'Threaded GuiWorkerQueue started')
        try:
            while self.active_queue and not Monitor.wait_for_abort(timeout=0.1):
                item: GuiWorkerQueue.QueueItem = None
                try:
                    item = self.topics_queue.get(timeout=0.0)
                    self.topics_queue.task_done()
                    clz.sequence_number += 1
                    GuiWorker.process_queue(item.changed, item.focused_id,
                                            clz.sequence_number)
                except queue.Empty:
                    # self._logger.debug_verbose('queue empty')
                    pass
                except AbortException:
                    return  # Let thread die
                except ValueError as e:
                    clz._logger.exception('')
                except Exception:
                    clz._logger.exception('')
        except AbortException:
            return  # Let thread die

        self.active_queue = False

    @classmethod
    def empty_queue(cls):
        #  cls._logger.debug(f'empty_queue')
        try:
            while True:
                cls.canceled_sequence_number = cls.sequence_number
                cls._instance.topics_queue.get_nowait()
                cls._instance.topics_queue.task_done()
        except queue.Empty:
            return

    @classmethod
    def add_task(cls, changed: int, focused_id: str):
        cls._logger.debug(f'Add task changed: {changed} focus_id: {focused_id}')
        current_windialog_id: int
        if WinDialogState.current_windialog == WinDialog.WINDOW:
            current_windialog_id = WinDialogState.current_window_id
            focus_id: str = f'{WinDialogState.current_window_focus_id}'
        else:
            current_windialog_id = WinDialogState.current_dialog_id
            focus_id: str = f'{WinDialogState.current_dialog_focus_id}'
        from windows import CustomTTSReader
        current_reader: CustomTTSReader
        current_reader = CustomTTSReader.get_instance(current_windialog_id)
        if current_reader is None:
            return   # Reader does not apply (xml file not ours)

        window_model: WindowModel = current_reader.window_model
        if changed & WindowStateMonitor.WINDOW_CHANGED:
            # May later change to be specific to window vs dialog
            GuiWorker.previous_topic_chain.clear()
            history_cleared = True
            cls._logger.debug('WINDOW_CHANGED')
        # if changed & WindowStateMonitor.WINDOW_FOCUS_CHANGED:
            # focused_topic = window_model.topic_by_tree_id.get(str(focus_id))
            # topic_str: str = ''
            # if focused_topic is not None:
            #     topic_str = focused_topic.name
            # clz._logger.debug(f'WINDOW_FOCUS_CHANGED focus_id: {focus_id} '
            #                  f'topic {topic_str}')
        if changed & WindowStateMonitor.DIALOG_CHANGED:
            GuiWorker.previous_topic_chain.clear()
            history_cleared = True
            cls._logger.debug('DIALOGCHANGED')

        if changed & WindowStateMonitor.DIALOG_FOCUS_CHANGED:
            focused_topic = window_model.topic_by_tree_id.get(str(focus_id))
            topic_str: str = ''
            if focused_topic is not None:
                topic_str = focused_topic.name
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose(f'DIALOG_FOCUS_CHANGED focus_id: {focus_id} '
                              f'topic {topic_str}')

        cls._logger.debug('Adding to queue')
        cls._instance.topics_queue.put_nowait(GuiWorkerQueue.QueueItem(changed,
                                                                       focus_id))


class GuiWorker:
    _logger: BasicLogger = None
    # _window_state_listener_lock: threading.RLock = None
    _window_state_lock: threading.RLock = None
    # _window_state_listeners: Dict[str, Callable[[int], bool]] = {}
    previous_topic_chain: List[TopicModel] = []

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
            WindowStateMonitor.register_window_state_listener(cls.determine_focus_change,
                                                              "special")

    def __init__(self) -> None:
        clz = type(self)
        self.service_prop: ForwardRef('TTSService') = None

    @property
    def service(self) -> ForwardRef('TTSService'):
        from service_worker import TTSService
        self.service_prop = TTSService.instance
        module_logger.debug(f'TTSService engine:'
                            f' {self.service_prop.active_backend.backend_id} '
                            f'instance: {self.service_prop} ')
        return self.service_prop

    @staticmethod
    def determine_focus_change(changed: int) -> bool:
        """
        class WinDialogState:
        current_windialog: WinDialog = WinDialog.WINDOW
        current_window_id: int = -1
        current_dialog_id: int = -1
        current_window_instance: xbmcgui.Window | None = None
        current_dialog_instance: xbmcgui.WindowDialog | None = None
        current_dialog_focus_id: int = 9999  # Windows don't have focus

        :param changed: 0 = No change in window, dialog or focus.
                            However, since not all controls have to
                            be declared, many control changes can not
                            be detected, requiring custom code to
                            query ListItems, InfoLabels, etc., which
                            is done outside of the monitor module.

        :return: True if handled and no further listeners need be called
                 False if change not handled
        """
        clz = GuiWorker
        # clz._logger.debug(f'In determine_focus_changed')
        current_windialog_id: int
        if WinDialogState.current_windialog == WinDialog.WINDOW:
            current_windialog_id = WinDialogState.current_window_id
            focus_id: str = f'{WinDialogState.current_window_focus_id}'
        else:
            current_windialog_id = WinDialogState.current_dialog_id
            focus_id: str = f'{WinDialogState.current_dialog_focus_id}'
        from windows import CustomTTSReader
        current_reader: CustomTTSReader
        current_reader = CustomTTSReader.get_instance(current_windialog_id)
        if current_reader is None:
            GuiWorkerQueue.empty_queue()
            return False  # This Reader does not apply (xml file not ours)

        # Value can change for controls even if control doesn't change. Perhaps
        # a slider where user presses left/right multiple times. Or a radio button
        # that is toggled multiple times. In these cases, just voice any value changes
        # without any other context (of course a control can choose to voice a bit more).

        # if changed == 0:
        #     return True

        if focus_id == '0':  # No control on dialog has focus (Kodi may not have focus)
            # clz._logger.debug(f'focus_id == 0, window_id: {current_windialog_id} '
            #                   f'returning True')
            GuiWorkerQueue.empty_queue()
            return True  # Don't want old code processing this

        clz._logger.debug(f'changed: {changed}')
        if changed & WindowStateMonitor.WINDOW_CHANGED:
            # May later change to be specific to window vs dialog
            GuiWorker.previous_topic_chain.clear()
            GuiWorkerQueue.empty_queue()

        if changed & WindowStateMonitor.WINDOW_FOCUS_CHANGED:
            GuiWorkerQueue.empty_queue()

        if changed & WindowStateMonitor.DIALOG_CHANGED:
            GuiWorker.previous_topic_chain.clear()
            GuiWorkerQueue.empty_queue()

        if changed & WindowStateMonitor.DIALOG_FOCUS_CHANGED:
            GuiWorkerQueue.empty_queue()

        GuiWorkerQueue.add_task(changed, focus_id)
        return True

    @staticmethod
    def process_queue(changed: int, focus_id: str, sequence_number: int) -> None:
        """
        class WinDialogState:
        current_windialog: WinDialog = WinDialog.WINDOW
        current_window_id: int = -1
        current_dialog_id: int = -1
        current_window_instance: xbmcgui.Window | None = None
        current_dialog_instance: xbmcgui.WindowDialog | None = None
        current_dialog_focus_id: int = 9999  # Windows don't have focus

        :param changed: 0 = No change in window, dialog or focus.
                            However, since not all controls have to
                            be declared, many control changes can not
                            be detected, requiring custom code to
                            query ListItems, InfoLabels, etc., which
                            is done outside of the monitor module.
        :param focus_id: id of the Topic which has/had focus
        :param sequence_number: Monotomically increasing 'transaction' number
                                used to cancel pending transactions

        :return: True if handled and no further listeners need be called
                 False if change not handled
        """
        clz = GuiWorker
        clz._logger.debug(f'changed: {changed} id: {focus_id} seq: {sequence_number}')
        current_windialog_id: int
        if WinDialogState.current_windialog == WinDialog.WINDOW:
            current_windialog_id = WinDialogState.current_window_id
        else:
            current_windialog_id = WinDialogState.current_dialog_id
        from windows import CustomTTSReader
        current_reader: CustomTTSReader
        current_reader = CustomTTSReader.get_instance(current_windialog_id)
        if current_reader is None:
            clz._logger.debug('reader is none')
            return

        window_model: WindowModel = current_reader.window_model
        focused_topic: TopicModel | None = None
        clz._logger.debug(f'changed: {changed}')
        if changed & (WindowStateMonitor.WINDOW_FOCUS_CHANGED |
                WindowStateMonitor.DIALOG_FOCUS_CHANGED):
            focused_topic = window_model.topic_by_tree_id.get(str(focus_id))

        if GuiWorkerQueue.canceled_sequence_number >= sequence_number:
            clz._logger.debug(f'Abandoning')
            return
        if changed == 0 and focus_id != 0:
            focused_topic = window_model.topic_by_tree_id.get(str(focus_id))
            topics_to_voice: List[TopicModel]
            topics_to_voice = GuiWorker.get_topics_for_voicing(window_model,
                                                               focused_topic.name,
                                                               focus_changed=False)
            current_reader.direct_voicing_topics(topics_to_voice,
                                                 sequence_number, focus_changed=False)
            return

        focused_topic_id: str = ''
        if focused_topic is not None:
            focused_topic_id = focused_topic.name
            clz._logger.debug(f'focused_topic: {focused_topic_id} ')
        else:
            pass
            clz._logger.debug(f'focused_topic is None')

        window_model.set_changed(changed, focused_topic_id, focus_id)
        topics_to_voice: List[TopicModel]
        topics_to_voice = GuiWorker.get_topics_for_voicing(window_model,
                                                           focused_topic_id)
        if GuiWorkerQueue.canceled_sequence_number >= sequence_number:
            clz._logger.debug(f'Abandoning')
            return

        # clz._logger.debug(f'About to call direct_voicing_topics')
        current_reader.direct_voicing_topics(topics_to_voice,
                                             sequence_number)
        # clz._logger.debug(f'Returned from direct_voicing_topics')
        return

    @staticmethod
    def get_topics_for_voicing(window_model: WindowModel,
                               focused_topic_id: str,
                               focus_changed: bool = True) -> List[TopicModel]:
        """
        Determine the chain of topics from the window to the topic with
        focus. Ideally, we would have enough knowledge to predict what controls
        need to be voiced, but we currently still have to discover the current
        text and then compare with what has already been voiced.

        Further, since only a tiny number of windows have had topics defined,
        another mechanism must be used.

        If focus_changed is True, then voice every change in topics from the
        window heading down to the focused object. If False, then only voice any
        change in value for the single topic sent.

        :param window_model:
        :param focused_topic_id:
        :param focus_changed: True when some change in focus occured, otherwise
                              no focus change occurred, but it is possible that
                              the value of the focused object has changed
        :return:
        """
        clz = GuiWorker
        current_focus_chain: List[TopicModel] = []

        # It is possible that UI could have been modified without us detecting it.
        # Without any hints it can be very costly to determine what has changed
        # in a window as well as deciding what changes to voice and in what order.

        if focused_topic_id == '':
            return []
        topic = window_model.topic_by_topic_name.get(focused_topic_id)
        if not focus_changed:
            current_focus_chain.append(topic)
            #  clz.previous_topic_chain = current_focus_chain.copy()
            return current_focus_chain

        clz._logger.debug(f'focused_topic_id: {focused_topic_id} topic: {topic.name}')
        clz._logger.debug(f'topic: {topic.name} outer_topic: {topic.outer_topic}')

        while topic is not None:
            current_focus_chain.append(topic)
            clz._logger.debug(f'topic: {topic.name} ctrl: {topic.parent.control_id} '
                              f'outer_topic: {topic.outer_topic}')
            topic = window_model.topic_by_topic_name.get(topic.outer_topic)

        # Reverse to make head of list the first thing to voice (window header)
        current_focus_chain = list(reversed(current_focus_chain))
        idx: int
        limit: int = min(len(current_focus_chain), len(clz.previous_topic_chain)) - 1
        if limit >= 0:
            for idx in range(0, limit):
                current_topic: TopicModel = current_focus_chain[idx]
                previous_topic: TopicModel = clz.previous_topic_chain[idx]
                if current_topic.name != previous_topic.name:
                    current_topic.clear_history()
                    previous_topic.clear_history()
        limit += 1
        if limit < len(current_focus_chain):
            for idx in limit, len(current_focus_chain) - 1:
                current_focus_chain[idx].clear_history()
        if limit < len(clz.previous_topic_chain):
            for idx in limit, len(clz.previous_topic_chain) - 1:
                clz.previous_topic_chain[idx].clear_history()

        clz.previous_topic_chain = current_focus_chain.copy()
        return current_focus_chain

    def direct_voicing_topics(self, topics_to_voice: List[TopicModel],
                              sequence_number: int) -> None:
        """
        Voice the controls/labels, etc. identified by topics_to_voice.

        :param topics_to_voice  A list of 'Topics' (labels, headings, values)
                                that need to be voiced in order (from
                                window headings down to details). Already
                                voiced items (such as window headings) have been
                                removed.
        :param sequence_number: Used to abandon any activity on now superseded
                                text to voice

        How things are voiced is determined by using information in each
        Topic as well as from the xxx_models derived from the window .xml files.

        Outside events (user input, other events) can interrupt voicing at any time
        and cause something else to be voiced instead.
        """
        clz = type(self)
        # clz._logger.debug(f'entering')
        success: bool = True
        phrases: PhraseList = PhraseList()
        for topic in topics_to_voice:
            if GuiWorkerQueue.canceled_sequence_number >= sequence_number:
                return
            topic: TopicModel
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'{topic}')
            parent: BaseModel = topic.parent
            success = parent.voice_control(phrases)

        # Rework interrupt so that window, heading, other levels can be individually
        # interrupted. In other words, if window stays the same, then you don't
        # have to interrupt voicing a window heading (just don't repeat it either).
        # Similar for other headings/groups. Requires some thought. Probably base
        # on how much 'topic chain' is altered.

        if not phrases.is_empty():
            phrases[0].set_interrupt(True)
            self.service.sayText(phrases)


GuiWorkerQueue.init()
GuiWorker.init_class()
