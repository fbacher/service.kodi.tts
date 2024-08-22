import queue
import threading
from typing import ForwardRef, List

from common import AbortException
from common.garbage_collector import GarbageCollector
from common.logger import *
from common.monitor import Monitor
from common.phrases import PhraseList
from gui.base_model import BaseModel
from gui.gui_globals import GuiGlobals
from gui.statements import Statements
from gui.topic_model import TopicModel
from gui.window_model import WindowModel
from windows.window_state_monitor import WinDialogState, WindowStateMonitor

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

        def __init__(self, changed: int, windialog_state: WinDialogState):
            self.changed: int = changed
            self.windialog_state: WinDialogState = windialog_state

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
            cls._instance._logger.debug_verbose(f'Starting queue_processor GuiWorkerQueue')
            cls._instance.queue_processor.start()
            GarbageCollector.add_thread(cls._instance.queue_processor)

    @classmethod
    @property
    def queue(cls) -> 'GuiWorkerQueue':
        return cls._instance

    def get_window_model(self, window_id: int) -> WindowModel:
        from windows import CustomTTSReader
        current_reader: CustomTTSReader
        current_reader = CustomTTSReader.get_instance(window_id)
        return current_reader.window_model

    def _handleQueue(self):
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG):
            self._logger.debug_verbose(f'Threaded GuiWorkerQueue started')
        try:
            while self.active_queue and not Monitor.wait_for_abort(timeout=0.1):
                item: GuiWorkerQueue.QueueItem = None
                try:
                    item = self.topics_queue.get(timeout=0.0)
                    self.topics_queue.task_done()
                    clz.sequence_number += 1
                    GuiWorker.process_queue(item.changed, item.windialog_state,
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
    def add_task(cls, changed: int, windialog_state: WinDialogState):
        focus_id: str = str(windialog_state.focus_id)
        visible: bool = windialog_state.is_control_visible

        cls._logger.debug(f'Add task changed: {changed} '
                          f'focus_id: {focus_id} visible {visible}')

        current_windialog_id: int = windialog_state.window_id
        from windows import CustomTTSReader
        current_reader: CustomTTSReader
        current_reader = CustomTTSReader.get_instance(current_windialog_id)
        if current_reader is None:
            return  # Reader does not apply (xml file not ours)
        window_model: WindowModel = current_reader.window_model
        if windialog_state.window_changed:  #  | windialog_state.revoice:
            # May later change to be specific to window vs dialog
            GuiWorker.previous_topic_chain.clear()
            history_cleared = True
            cls._logger.debug('WinDialog changed')
        """
            What to do when the control is not visible?
            Perhaps there is no control with focus (focus_id == 0). This can
            occur when this is a window (or dialog) with focusable controls,
            or with no focusable controls visible. What can we read when we
            don't have something to 'focus on'?
            
            With Topics we can at least read the header and whatever else they
            lead. Without Topics we can walk the tree of controls with ids.
            Ugly.
        """
        if True:  # windialog_state.is_control_visible:
            if changed & WindowStateMonitor.WINDOW_FOCUS_CHANGED:
                focused_topic = window_model.topic_by_tree_id.get(str(focus_id))
                topic_str: str = ''
                if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                    cls._logger.debug_verbose(f'WINDOW_FOCUS_CHANGED '
                                              f'focus_id: {focus_id} '
                                              f'topic {topic_str}')
        cls._logger.debug('Adding to queue')
        cls._instance.topics_queue.put_nowait(
                GuiWorkerQueue.QueueItem(changed, windialog_state))


class GuiWorker:
    _logger: BasicLogger = None
    # _window_state_listener_lock: threading.RLock = None
    _window_state_lock: threading.RLock = None
    # _window_state_listeners: Dict[str, Callable[[int], bool]] = {}
    previous_topic_chain: List[TopicModel] = []
    _previous_stmts_chain: List[Statements] = [Statements(stmt=None, topic_id=None)]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
            WindowStateMonitor.register_window_state_listener(cls.determine_focus_change,
                                                              "special",
                                                              require_focus_change=False)

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
    def determine_focus_change(changed: int, window_state: WinDialogState) -> bool:
        """
        class WinDialogState:
        current_windialog: WinDialog = WinDialog.WINDOW
        current_window_id: int = -1
        current_dialog_id: int = -1
        current_window_instance: xbmcgui.Window | None = None
        current_dialog_instance: xbmcgui.WindowDialog | None = None
        current_dialog_focus_id: int = 9999  # Windows don't have focus

        :param changed:  0 = No change in window, dialog or focus.
                            However, since not all controls have to
                            be declared, many control changes can not
                            be detected, requiring custom code to
                            query ListItems, InfoLabels, etc., which
                            is done outside of the monitor module.

        :param window_state: is the WinDialogStatus for the current window/dialog

        :return: True if handled and no further listeners need be called
                 False if change not handled
        """
        clz = GuiWorker
        # Value can change for controls even if control doesn't change. Perhaps
        # a slider where user presses left/right multiple times. Or a radio button
        # that is toggled multiple times. In these cases, just voice any value changes
        # without any other context (of course a control can choose to voice a bit more).

        #  TODO: process some which are changed = 0 and focus = 0. Needs to be done
        #  occasionally to catch windows that don't need input (all labels).
        #  But very expensive to do all of the time when changed = 0 is probably right.

        if GuiGlobals.require_focus_change and not window_state.focus_changed:
            return True
        if not GuiGlobals.require_focus_change and window_state.focus_changed:
            GuiGlobals.require_focus_change = True

        if window_state.changed == 0 and window_state.focus_id == 0:
            return True

        clz._logger.debug(f'In determine_focus_changed window_state: {window_state}')

        current_windialog_id: int = window_state.window_id

        from windows import CustomTTSReader
        current_reader: CustomTTSReader
        current_reader = CustomTTSReader.get_instance(current_windialog_id)
        if current_reader is None:
            GuiWorkerQueue.empty_queue()
            return False  # This Reader does not apply (xml file not ours)
        """
        if focus_id == '0':  # No control on dialog has focus (Kodi may not have focus)
            # clz._logger.debug(f'focus_id == 0, window_id: {current_windialog_id} '
            #                   f'returning True')
            GuiWorkerQueue.empty_queue()
            return True  # Don't want old code processing this
        """

        clz._logger.debug(f'changed: {changed} 0x{changed:02x} new window '
                          f'{window_state.window_changed} '
                          f'focus change: {window_state.focus_changed}'
                          f' revoice: {window_state.revoice}')
        try:
            if window_state.window_changed or window_state.revoice:
                # May later change to be specific to window vs dialog
                GuiWorker.previous_topic_chain.clear()
                GuiWorkerQueue.empty_queue()
            elif window_state.focus_changed:
                GuiWorkerQueue.empty_queue()
            elif window_state.visibility_changed:
                GuiWorkerQueue.empty_queue()
            elif window_state.focus_changed:
                GuiWorkerQueue.empty_queue()

            clz._logger.debug(f'Calling add_task')
            GuiWorkerQueue.add_task(changed, window_state)
        except Exception:
            clz._logger.exception('')
        return True

    @staticmethod
    def process_queue(changed: int, windialog_state: WinDialogState,
                      sequence_number: int) -> None:
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
        :param windialog_state: WinDialogState information on the focused window
        :param sequence_number: Monotomically increasing 'transaction' number
                                used to cancel pending transactions

        :return: True if handled and no further listeners need be called
                 False if change not handled
        """
        clz = GuiWorker
        changed: int = windialog_state.changed
        focus_id: int = windialog_state.focus_id
        clz._logger.debug(
                f'changed: {changed} focus_id: {focus_id} seq: {sequence_number}')
        window_id: int = windialog_state.window_id
        from windows import CustomTTSReader
        current_reader: CustomTTSReader
        current_reader = CustomTTSReader.get_instance(window_id)
        if current_reader is None:
            clz._logger.debug('reader is None')
            return

        window_model: WindowModel = current_reader.window_model
        focused_topic: TopicModel | None = None
        clz._logger.debug(f'changed: {changed} revoice: {windialog_state.revoice}')
        if windialog_state.focus_changed or not GuiGlobals.require_focus_change:
            clz._logger.debug(f'focus_id: {focus_id}')
            focused_topic = window_model.topic_by_tree_id.get(str(focus_id))
            clz._logger.debug(f'focused_topic: {focused_topic}')

        if GuiWorkerQueue.canceled_sequence_number >= sequence_number:
            clz._logger.debug(f'Abandoning')
            return
        # Is it worth to scrape to find out if something has changed (label, etc.)
        # that otherwise does not show up because no api directly detects it?

        if focused_topic is None and windialog_state.potential_change:
            try:
                focused_topic = window_model.topic_by_tree_id.get(str(focus_id))
                topics_to_voice: List[TopicModel]
                focused_topic_id: str = ''
                if focused_topic is not None:
                    focused_topic_id = focused_topic.name
                topics_to_voice = GuiWorker.get_topics_for_voicing(window_model,
                                                                   focused_topic_id,
                                                                   focus_changed=False)
                clz._logger.debug(f'windialog_state focus: {windialog_state.focus_id} '
                                  f'revoice: {windialog_state.revoice}')
                current_reader.direct_voicing_topics(topics_to_voice,
                                                     windialog_state=windialog_state,
                                                     sequence_number=sequence_number)
            except Exception as e:
                clz._logger.exception(f'focus_id: {focus_id} window_id: {window_id} '
                                      f'\n {focused_topic}')
            return

        focused_topic_id: str = ''
        if focused_topic is not None:
            focused_topic_id = focused_topic.name
            clz._logger.debug(f'focused_topic: {focused_topic_id} ')
        else:
            pass
            clz._logger.debug(f'focused_topic is None or not real:'
                              f' focus_id: {focus_id} '
                              f' topic_id: {focused_topic_id} {focused_topic}')
            #  Must look for window header and see where that takes us

        window_model.set_changed(changed, windialog_state)
        topics_to_voice: List[TopicModel]
        topics_to_voice = GuiWorker.get_topics_for_voicing(window_model,
                                                           focused_topic_id)
        if GuiWorkerQueue.canceled_sequence_number >= sequence_number:
            clz._logger.debug(f'Abandoning')
            return

        # clz._logger.debug(f'About to call direct_voicing_topics')
        current_reader.direct_voicing_topics(topics_to_voice,
                                             windialog_state=windialog_state,
                                             sequence_number=sequence_number)
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
        :param focused_topic_id: Can be 0 when window only has dialogs, or no
                                 focusable controls are visible
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
        #
        # For now, read any window header and wherever the heading topic leads.
        # Without topics we can discover any controls WITH IDs that are 'top-level'
        # TODO: tackle later

        # if focused_topic_id == '':
        #    # Is there a heading topic?
        #     return []

        # The plan is to start with the Topic with focus and then create chain
        # of topics/controls from the focused control to the window by following
        # the 'Outer Topic" chain.

        topic: TopicModel | None = None
        if focused_topic_id == '':
            topic = window_model.root_topic
            clz._logger.debug(f'Getting root topic: {topic.name}')
        else:  # There is no topic that has focus
            # TODO: next check for a control (without topic) having focus
            # From there see if there is a topic with a neighboring controlId
            topic = window_model.get_topic_for_id(focused_topic_id)
            # Fake topics are created for controls which have no <topic> in the
            # xml. Can't use them for this purpose.
            if topic is None or not topic.is_real_topic:
                clz._logger.debug(f'Can not find topic for focus control: '
                                  f'{focused_topic_id}')
                topic = None
                clz._logger.debug(f'No topics found for root')
                return []
            clz._logger.debug(f'focused topic: {topic.name}')

        if not focus_changed:
            current_focus_chain.append(topic)
            return current_focus_chain

        while topic is not None:
            if not topic.is_real_topic:
                clz._logger.debug(f'Skipping over fake topic: {topic}')
                continue
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
        limit += 1

        clz.previous_topic_chain = current_focus_chain.copy()
        return current_focus_chain


GuiWorkerQueue.init()
GuiWorker.init_class()
