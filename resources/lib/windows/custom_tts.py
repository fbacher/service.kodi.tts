# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from pathlib import Path

import xbmc
import xbmcgui

from common import *

from common.logger import *
from common.logger import BasicLogger
from common.phrases import PhraseList
from gui.base_model import BaseModel
from gui.gui_globals import GuiGlobals
from gui.gui_worker import GuiWorkerQueue
from gui.parser.parse_window import ParseWindow
from gui.statements import Statement, Statements, StatementType
from gui.topic_model import TopicModel
from gui.window_model import WindowModel
from gui.window_structure import WindowStructure
from windows import WindowReaderBase
from . import skintables
from .window_state_monitor import WinDialogState, WindowStateMonitor

CURRENT_SKIN = skintables.CURRENT_SKIN

module_logger = BasicLogger.get_logger(__name__)


class CustomTTSReader(WindowReaderBase):
    ID = 'custom_tts'
    _logger: BasicLogger = module_logger  # None

    # window_cache: Dict[int, WindowModel] = {}
    current_reader: ForwardRef('CustomTTSReader') = None
    previous_topic_chain: List[TopicModel] = []
    _previous_stmts_chain: List[Statements] = [Statements(stmt=None, topic_id=None)]


    @classmethod
    def get_instance(cls, window_id: int,
                     windialog_state: WinDialogState)\
            -> Union[ForwardRef('CustomTTSReader'),  None]:
        if cls._logger is None:
            cls._logger = module_logger

        cls._logger.debug(f'current_reader: {cls.current_reader.__class__.__name__}'
                          f' window_id: {window_id}')
        simple_path: Path = Path(xbmc.getInfoLabel('Window.Property(xmlfile)'))
        if str(simple_path.name) not in ('script-tts-settings-dialog.xml',
                                         'selection-dialog.xml',
                                         'tts-help-dialog.xml'):
            cls._logger.debug(f'simple_path: {simple_path}')
            return None
        #  cls._logger.debug(f'window_id: {window_id}')
        if cls.current_reader is None:
            from service_worker import TTSService
            cls.current_reader = CustomTTSReader(window_id, TTSService.instance,
                                                 windialog_state)
        if cls.current_reader is not None:
            #  cls._logger.debug(f'running: {cls.current_reader.is_running(window_id)}')
            return cls.current_reader
        return None

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None,
                 windialog_state: WinDialogState = None) -> None:
        super().__init__(win_id, service)
        clz = CustomTTSReader
        if clz._logger is None:
            clz._logger = module_logger
        # Disable old reader
        clz.current_reader = None
        simple_path: Path = Path(xbmc.getInfoLabel('Window.Property(xmlfile)'))
        # Refresh Window, Dialog, control and focus info
        changed: int
        clz._logger.debug(f'simple_path: {simple_path}')
        clz._logger.debug(f'simple_path.name: {simple_path.name}')
        self.control_id = win_id
        clz._logger.debug(f'window_id: {win_id}')
        self.window_heading_ctrl: xbmcgui.ControlLabel = None
        self.heading_ctrl: int = -1
        self.window_model: WindowModel | None = None
        self.window_struct: WindowStructure | None = None
        self.is_dialog: bool = False

        window_parser: ParseWindow | None = None
        if str(simple_path.name) in ('script-tts-settings-dialog.xml',
                                     'selection-dialog.xml',
                                     'tts-help-dialog.xml'):
            parser: ParseWindow = ParseWindow()
            parser.parse_window(control_id=self.control_id, xml_path=simple_path,
                                is_addon=True)
            if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                clz._logger.debug_extra_verbose(f'DUMP PARSED:')
                for result in parser.dump_parsed():
                    clz._logger.debug_extra_verbose(result)
                clz._logger.debug_extra_verbose('finished DUMP PARSED')
            window_parser = parser
            #  clz._logger.debug(f'Number of parsers2: {len(parser.parsers)}')
            # Builds entire window model and topic models
            self.window_model: WindowModel = WindowModel(window_parser)
            self.window_model.window_struct = self.window_struct
            self.window_model.windialog_state = windialog_state
            # Need window id in order to build WindowStructure
            self.window_struct = WindowStructure(self.window_model)

            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'DUMP MODEL:'
                              f' \n{self.window_model.to_string(include_children=True)}')
            # clz._logger.debug(f'DUMP MODEL:'
            #                   f' \n{self.window_model.to_string(include_children=True)}')
        clz.current_reader = self
        return

    def is_running(self, control_id: int) -> bool:
        clz = CustomTTSReader
        return clz.current_reader == self

    def direct_voicing_topics(self, topics_to_voice: List[TopicModel],
                              windialog_state: WinDialogState,
                              sequence_number: int) -> None:
        """
        Voice the controls/labels, etc. identified by topics_to_voice.

        :param topics_to_voice  A list of 'Topics' (labels, headings, values)
                                that need to be voiced in order (from
                                window headings down to details). Already
                                voiced items (such as window headings) have been
                                removed.
        :param windialog_state: contains some useful state information
        :param sequence_number: Used to abandon any activity on now superseded
                                text to voice

        How things are voiced is determined by using information in each
        Topic as well as from the xxx_models derived from the window .xml files.

        Outside events (user input, other events) can interrupt voicing at any time
        and cause something else to be voiced instead.
        """
        clz = CustomTTSReader
        new_stmt_chain: List[Statements] = []
        # clz._logger.debug(f'entering')
        success: bool = True
        revoice_topic_id: str = ''

        focus_changed: bool = windialog_state.focus_changed
        debug_high_verbosity: int = DEBUG_VERBOSE
        debug_normal_verbosity: int = DEBUG
        if focus_changed and not GuiGlobals.require_focus_change:
            GuiGlobals.clear()
            GuiGlobals.require_focus_change = True
            GuiGlobals.saved_states['TRACE'] = 'abc'
            clz._logger.debug(f'FOCUS CHANGED: {windialog_state.focus_id} '
                              f'{windialog_state.window_id}')
        else:
            debug_high_verbosity = DEBUG_EXTRA_VERBOSE
            debug_normal_verbosity = DEBUG_VERBOSE
        if clz._logger.isEnabledFor(debug_high_verbosity):
            clz._logger.debug(f'windialog_state {windialog_state}')

        topic: TopicModel = topics_to_voice[0]
        # Update the window state before evaluation
        topic.parent.windialog_state = windialog_state

        if windialog_state.window_changed:  # or windialog_state.revoice:
            clz._previous_stmts_chain = [Statements(stmt=None, topic_id=None)]
        debug_msg_not_voiced: List[str] = []
        debug_msg_voiced: List[str] = []

        for topic in topics_to_voice:
            if clz._logger.isEnabledFor(debug_high_verbosity) and focus_changed:
                clz._logger.debug_verbose(f'topic: {topic}')
            if GuiWorkerQueue.canceled_sequence_number >= sequence_number:
                clz._logger.debug(f'canceled voicing: seq#: {sequence_number}'
                                  f' topic: {topic.name}')
                return
            stmts: Statements = Statements(stmt=None, topic_id=topic.name)
            try:
                focus_changed: bool = windialog_state.focus_changed
                #
                #  V O I C E   C O N T R O L
                #
                if not focus_changed:
                    debug_msg_not_voiced.append(topic.name)
                if topic.is_real_topic:
                    if clz._logger.isEnabledFor(debug_high_verbosity) and focus_changed:
                        clz._logger.debug_verbose(
                            f'\n topic {topic.name} '
                            f'\ncontrol_id: {topic.control_id} '
                            f'\nfocus: {windialog_state.focus_id} '
                            f'\nfocus_changed: {focus_changed}')
                    #  clz._logger.debug(f'Topic is real')
                    success = topic.voice_control(stmts)
                    debug_msg_voiced.append(topic.name)
                else:
                    if clz._logger.isEnabledFor(debug_high_verbosity) and focus_changed:
                        parent: BaseModel = topic.parent
                        if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                            clz._logger.debug_extra_verbose(
                                f'About to call {parent.__class__.__name__} '
                                f'\nfocus_changed: {focus_changed} '
                                f'\n{windialog_state}')
                        success = parent.voice_control(stmts)
            except Exception as e:
                clz._logger.exception('')
            new_stmt_chain.append(stmts)
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'topics voiced: {", ".join(debug_msg_voiced)}'
                                      f' not voiced: {", ".join(debug_msg_not_voiced)}')

        #
        #    D E C I D E   W H A T   T O   V O I C E
        #
        # Finished processing topic chain and getting new_stmt_chain

        # Rework interrupt so that window, heading, other levels can be individually
        # interrupted. In other words, if window stays the same, then you don't
        # have to interrupt voicing a window heading (just don't repeat it either).
        # Similar for other headings/groups. Requires some thought. Probably base
        # on how much 'topic chain' is altered.

        # Generate phrases to voice

        # Force revoice
        if windialog_state.revoice:
            clz._previous_stmts_chain = []
        if clz._logger.isEnabledFor(debug_high_verbosity) and focus_changed:
            clz._logger.debug(f'Previous_chain: {clz._previous_stmts_chain}')
            clz._logger.debug(f'Current_chain: {new_stmt_chain}')
        stmts_chain_iter = iter(clz._previous_stmts_chain)
        phrases_to_voice: PhraseList = PhraseList(check_expired=False)
        stmt_filter: List[StatementType] = Statement.create_filter()
        #  clz._logger.debug(f'revoice: {windialog_state.revoice}')
        # Force voicing of focused item on Revoice request

        # Mark final text to be voiced with 'interrupt' if any of the
        # voiced statements request it.
        previous_chain_empty: bool = False
        interrupt_voicing: bool = False
        for stmts in new_stmt_chain:
            stmts: Statements
            previous_stmts: Statements | None = None
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'Building what to voice stmts: {stmts}')
            try:
                # Iterate old/previous stmts in own try-catch
                previous_stmts = next(stmts_chain_iter)
            except StopIteration:
                # previous_stmt chain shorter than new chain
                # voice everything from now on.
                previous_stmts = None
                if not previous_chain_empty:
                    if clz._logger.isEnabledFor(debug_normal_verbosity):
                        clz._logger.debug(f'No more previous_chain')
                    previous_chain_empty = True
            if previous_stmts is None or stmts.requires_voicing(previous_stmts,
                                                                stmt_filter=stmt_filter):
                # if previous_stmts is None:
                #     clz._logger.debug(f'previous_stmts is None')
                clz._logger.debug(f'Voicing {stmts}')
                phrases: PhraseList = stmts.as_phrases(stmt_filter=stmt_filter)
                #  clz._logger.debug(f'expanded phrases: {phrases}')
                phrases_to_voice.extend(phrases)
                interrupt_voicing = interrupt_voicing or stmts.interrupt
                if (clz._logger.isEnabledFor(DEBUG_VERBOSE)
                        and not phrases_to_voice.is_empty()):
                    clz._logger.debug(f'Aggregate text: {phrases_to_voice}')
            else:
                if clz._logger.isEnabledFor(DEBUG_VERBOSE) and focus_changed:
                    clz._logger.debug(f'Not voicing {stmts}')

        clz._previous_stmts_chain = new_stmt_chain
        if clz._logger.isEnabledFor(DEBUG) and not phrases_to_voice.is_empty():
            clz._logger.debug(f'Final Aggregate text: {phrases_to_voice}')
        if not phrases_to_voice.is_empty():
            interrupt_voicing = True
            phrases_to_voice.set_interrupt(interrupt_voicing)
            self.service.sayText(phrases_to_voice)
