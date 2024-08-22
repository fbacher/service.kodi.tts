# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from pathlib import Path
from typing import Tuple

import xbmc
import xbmcgui

from common import *

from common.logger import *
from common.logger import BasicLogger
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.gui_globals import GuiGlobals
from gui.gui_worker import GuiWorkerQueue
from gui.parse_window import ParseWindow
from gui.statements import Statement, Statements, StatementType
from gui.topic_model import TopicModel
from gui.window_model import WindowModel
from windows import WindowReaderBase
from . import skintables
from .window_state_monitor import WinDialogState, WindowStateMonitor

CURRENT_SKIN = skintables.CURRENT_SKIN

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class CustomTTSReader(WindowReaderBase):
    ID = 'custom_tts'
    _logger: BasicLogger = None

    # window_cache: Dict[int, WindowModel] = {}
    current_reader: ForwardRef('CustomTTSReader') = None
    previous_topic_chain: List[TopicModel] = []
    _previous_stmts_chain: List[Statements] = [Statements(stmt=None, topic_id=None)]


    @classmethod
    def get_instance(cls, window_id: int) -> ForwardRef('CustomTTSReader') | None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(CustomTTSReader.__class__.__name__)

        #  cls._logger.debug(f'current_reader: {cls.current_reader} window_id: {window_id}')
        simple_path: Path = Path(xbmc.getInfoLabel('Window.Property(xmlfile)'))
        if str(simple_path.name) not in ('script-tts-settings-dialog.xml',
                                         'tts-help-dialog.xml'):
            cls._logger.debug(f'simple_path: {simple_path}')
            return None
        #  cls._logger.debug(f'window_id: {window_id}')
        if cls.current_reader is None:
            from service_worker import TTSService
            cls.current_reader = CustomTTSReader(window_id, TTSService.instance)
        if cls.current_reader is not None:
            #  cls._logger.debug(f'running: {cls.current_reader.is_running(window_id)}')
            return cls.current_reader
        return None

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None) -> None:
        super().__init__(win_id, service)
        clz = CustomTTSReader
        if clz._logger is None:
            clz._logger = module_logger.getChild(CustomTTSReader.__class__.__name__)
        # Disable old reader
        clz.current_reader = None
        simple_path: Path = Path(xbmc.getInfoLabel('Window.Property(xmlfile)'))
        # Refresh Window, Dialog, control and focus info
        changed: int
        windialog_state: WinDialogState
        changed, windialog_state = WindowStateMonitor.check_win_dialog_state()
        clz._logger.debug(f'simple_path: {simple_path}')
        #  clz._logger.debug(f'simple_path.name: {simple_path.name}')
        self.control_id = windialog_state.window_id
        clz._logger.debug(f'window_id: {self.control_id}')
        self.window_heading_ctrl: xbmcgui.ControlLabel = None
        self.heading_ctrl: int = -1
        self.window_model: WindowModel | None = None
        self.is_dialog: bool = False

        window_parser: ParseWindow | None = None
        if str(simple_path.name) in ('script-tts-settings-dialog.xml',
                                     'tts-help-dialog.xml'):
            parser: ParseWindow = ParseWindow()
            parser.parse_window(control_id=self.control_id, xml_path=simple_path,
                                is_addon=True)
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'DUMP PARSED:')
                for result in parser.dump_parsed():
                    clz._logger.debug(result)
            window_parser = parser
            #  clz._logger.debug(f'Number of parsers2: {len(parser.parsers)}')

            self.window_model: WindowModel = WindowModel(window_parser)
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'DUMP MODEL: \n{self.window_model}')

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

        clz._logger.debug(f'windialog_state focus: {windialog_state.focus_id} '
                          f'revoice: {windialog_state.revoice}')
        topic: TopicModel
        if windialog_state.window_changed:  # or windialog_state.revoice:
            clz._previous_stmts_chain = [Statements(stmt=None, topic_id=None)]

        for topic in topics_to_voice:
            if GuiWorkerQueue.canceled_sequence_number >= sequence_number:
                clz._logger.debug(f'canceled voicing: seq#: {sequence_number}'
                                  f' topic: {topic}')
                return
            stmts: Statements = Statements(stmt=None, topic_id=topic.name)
            try:
                focus_changed: bool = windialog_state.focus_changed
                if topic.is_real_topic:
                    if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                        clz._logger.debug_extra_verbose(
                            f'About to call topic {topic.name} '
                            f'control_id: {topic.control_id} '
                            f'focus_changed: {focus_changed}')
                    #  clz._logger.debug(f'Topic is real')
                    success = topic.voice_control(stmts, focus_changed,
                                                  windialog_state)
                else:
                    parent: BaseModel = topic.parent
                    if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                        clz._logger.debug_extra_verbose(
                            f'About to call {parent.__class__.__name__} '
                            f'focus_changed: {focus_changed} '
                            f'{windialog_state}')

                    success = parent.voice_control(stmts, focus_changed,
                                                   windialog_state)
            except Exception as e:
                clz._logger.exception('')
            new_stmt_chain.append(stmts)

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
        clz._logger.debug(f'Previous_chain: {clz._previous_stmts_chain}')
        clz._logger.debug(f'Current_chain: {new_stmt_chain}')
        stmts_chain_iter = iter(clz._previous_stmts_chain)
        phrases_to_voice: PhraseList = PhraseList(check_expired=False)
        stmt_filter: List[StatementType] = Statement.create_filter()
        clz._logger.debug(f'revoice: {windialog_state.revoice}')
        # Force voicing of focused item on Revoice request

        # Mark final text to be voiced with 'interrupt' if any of the
        # voiced statements request it.
        interrupt_voicing: bool = False
        for stmts in new_stmt_chain:
            stmts: Statements
            previous_stmts: Statements = None
            clz._logger.debug(f'Building what to voice stmts: {stmts}')
            try:
                # Iterate old/previous stmts in own try-catch
                previous_stmts = next(stmts_chain_iter)
            except StopIteration:
                # previous_stmt chain shorter than new chain
                # voice everything from now on.
                previous_stmts = None
                clz._logger.debug(f'No more previous_chain')
            if previous_stmts is None or stmts.requires_voicing(previous_stmts,
                                                                stmt_filter=stmt_filter):
                if previous_stmts is None:
                    clz._logger.debug(f'previous_stmts is None')
                clz._logger.debug(f'Voicing {stmts}')
                phrases: PhraseList = stmts.as_phrases(stmt_filter=stmt_filter)
                clz._logger.debug(f'expanded phrases: {phrases}')
                phrases_to_voice.extend(phrases)
                interrupt_voicing = interrupt_voicing or stmts.interrupt
                clz._logger.debug(f'Aggregate text: {phrases_to_voice}')
            else:
                clz._logger.debug(f'Not voicing {stmts}')

        clz._previous_stmts_chain = new_stmt_chain
        phrases_to_voice.set_interrupt(interrupt_voicing)
        self.service.sayText(phrases_to_voice)
