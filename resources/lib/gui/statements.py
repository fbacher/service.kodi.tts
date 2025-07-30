# coding=utf-8
from __future__ import annotations

from common.message_ids import MessageId

"""
Frequently the text that needs to be voiced for a control follows
pattern. For example, a Window topic may have:
    1) the control type (Window or Dialog, or some custom name)
    2) followed by a title and perhaps sub-titles
    3) optional help-text
    ...

While a List may have:
    1) The type of the list
    2) the title /subtitles of list
    3) optional help-text
    4) # of items in table
    5) orientation of list (vertical/horizontal)
    6) the current time, or some other changing value that is not of central
       importance to the task

The number of items in the lists don't matter.

Each 'statement' has a type field indicating its importance and broad purpose:
Normal text
hint/help which only needs to be announced once when requested and ignored
transient information that is announced, but any changed value is announced
when some other change requires announcing.
detailed information, to be announced when higher priority items have been
voiced.
"""
import copy
from enum import Enum
from logging import DEBUG
from typing import ForwardRef, List, Tuple, Union

from common.exceptions import ExpiredException
from common.globals import Globals
from common.logger import BasicLogger, DEBUG_V, DEBUG_XV, DISABLED
from common.phrases import PhraseList

module_logger = BasicLogger.get_logger(__name__)


class StatementType(Enum):
    # Same as normal. Must be compared and present. No functional difference
    # at this time.
    HIGH = 1

    # Normal text. Must be compared and must be present
    NORMAL = 2

    # The prior voicing may have included details that can be omitted from
    # this voicing

    DETAILS = 3

    # Variant text is not compared, but its presence is is_required
    VARIANT = 4

    # Hint text is only present upon request. Once voiced we don't care.
    # Ignore comparison, Okay to omit
    HINT_TEXT = 5

    # Don't voice this statement. Comparison with other statements will
    # pass. Allows text to be processed and ignored.
    SILENT = 6

    # Field contains a value. Process as NORMAL. Allows filtering
    VALUE = 7


class Statement:

    OMITTABLE: Tuple[StatementType, StatementType, StatementType]
    OMITTABLE = StatementType.HINT_TEXT, StatementType.DETAILS, StatementType.SILENT

    _logger: BasicLogger = module_logger

    def __init__(self, phrases: PhraseList,
                 stmt_type: StatementType = StatementType.NORMAL):
        clz = Statement
        self.phrases: PhraseList = phrases
        self.stmt_type: StatementType = stmt_type
        self.serial_number: int = 0

    def is_required(self, required_types) -> bool:
        """
            Determines if there is any interest in voicing a statement of this type
            (HINT_TEXT_ON_STARTUP) or if it is to be ignored.

        :param required_types: types, such as StatementType.HINT_TEXT_ON_STARTUP
        :return: True, there is a desire to voice these, compare text with previously
            voiced to be sure. Otherwise False, no interest in voicing.
        """
        clz = Statement
        if clz._logger.isEnabledFor(DEBUG_XV):
            clz._logger.debug_xv(f'stmt_type: {self.stmt_type} '
                                      f'required_types: {required_types} '
                                      f'{self.stmt_type in required_types}')
        return self.stmt_type in required_types

    @classmethod
    def create_filter(cls) -> List[StatementType]:
        stmt_filter: List[StatementType] = []
        if Globals.get_voice_hint() != MessageId.VOICE_HINT_OFF:
            stmt_filter.append(StatementType.HINT_TEXT)
        return stmt_filter

    @property
    def omittable(self) -> bool:
        clz = Statement
        if clz._logger.isEnabledFor(DEBUG_XV):
            clz._logger.debug_xv(f'omittable stmt_type: {self.stmt_type} '
                                      f'omittable: {self.stmt_type in clz.OMITTABLE}')
        return self.stmt_type in clz.OMITTABLE

    @property
    def variant(self) -> bool:
        return self.stmt_type == StatementType.VARIANT

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Statement):
            raise TypeError('Must be Statement')
        other: Statement
        return self.phrases.equal_text(other.phrases)

    def __repr__(self) -> str:
        value: str = (f' {self.stmt_type}  '
                      f'{self. phrases}')
        return value


class Statements:
    """
        Each Topic produces Statements that can be voiced.
        To avoid repetition, Statements are checked to verify that they have
        changed before revoicing.

        Each time the focus (or some other interesting event occurs) the
        text for each topic/control in the hiarchy of topics from the one with
        focus to the Window is captured. Then, the two chains are compared
        to determine what to voice.

        Some items, such as hints, or triansient, unimportant information (like
        the time) may be ignored, depending upon the context.

    """

    global_serial_number: int = 0
    _logger: BasicLogger = module_logger

    def __init__(self, stmt: Statement | None, topic_id: str | None) -> None:

        clz = Statements
        clz.global_serial_number += 1
        self.serial_number: int = clz.global_serial_number

        # Used when generating the aggregate PhraseList for voicing.
        self._interrupt: bool = True
        self.stmts: List[Statement] = []
        if stmt is None:
            stmt = Statement(PhraseList(check_expired=False),
                             stmt_type=StatementType.NORMAL)
        self.stmts.append(stmt)
        stmt.serial_number = self.serial_number
        self.topic_id: str = topic_id

    @property
    def interrupt(self) -> bool:
        """
        Indicates whether this series of Statements should interrupt any
        earlier, as yet unvoiced statement. Note that interrupts get handled
        when Statements are converted into Phrases.

        :return:
        """
        return self._interrupt

    def append(self, stmt: Statement):
        clz = Statements
        if stmt is None:
            raise ValueError('stmt is None')

        stmt.serial_number = self.serial_number
        if len(self.stmts[-1].phrases) == 0:
            self.stmts[-1] = stmt
        else:
            self.stmts.append(stmt)

    @property
    def is_empty(self) -> bool:
        return len(self.stmts) == 0

    @property
    def last(self) -> Statement:
        return self.stmts[-1]

    def mark_as_silent(self, stmt_filter: Tuple[StatementType, ...],
                       interrupt: bool = False) -> None:
        """
        Change the StatementType of all statements from NORMAL to SILENT.
        This will cause Statements to only voice items which are not SILENT.
        This allows for only a value to be voiced when it has changed without
        revoicing the whole control.

        :param stmt_filter: Limits the statements marked to ones which
             match the filter. (To mark only statements marked as NORMAL
             or HINT_TEXT_ON_STARTUP, specify stmt_filter=(NORMAL, HINT_TEXT_ON_STARTUP)).
        :param interrupt: Causes the resulting PhraseList's interrupt
            attribute to be overriden. Using interrupt=False will help
            ensure that the full-description will get voiced before a
            value update is voiced.
        :return:

        Note: Useful for voicing controls, such as slider, which allow for
        multiple value changes to occur. You don't usually want to voice the
        details each time only the value changes.
        """
        for stmt in self.stmts:
            if stmt.stmt_type in stmt_filter:
                stmt.stmt_type = StatementType.SILENT

        self._interrupt = interrupt

    def requires_voicing(self, last_voiced: Union[ForwardRef('Statements'), None],
                         stmt_filter: List[StatementType] = None) -> bool:
        """
        Determine if this Topic's (or control's) statements need to be voiced
        and if any should be omitted.

        This is accomplished by comparing with the previously voiced statements.
            If there is no previous statements, then voice all from self,
            other than ones that should be filtered out (ex: hints, when hinting
            is not enabled).

        :param stmt_filter: StatementTypes to voice, overrides
            StatementType.OMITTABLE
        :param last_voiced: The previous statements made by a Topic at the
        same 'control-level'.
        :return:
        """
        clz = Statements
        try:
            value: bool = self.requires_voicing_worker(last_voiced, stmt_filter)
        except ExpiredException:
            clz._logger.debug(f'')
            value = False
        return value

    def requires_voicing_worker(self, last_voiced: Union[ForwardRef('Statements'), None],
                                stmt_filter: List[StatementType] = None) -> bool:
        """

        :param last_voiced:
        :param stmt_filter:
        :return:
        """
        clz = Statements
        if clz._logger.isEnabledFor(DISABLED):
            clz._logger.debug_v(f'source: {self.stmts}')
            clz._logger.debug_v(f'last_voiced: {last_voiced}')
            clz._logger.debug_v(f'required_stmt_types: {stmt_filter}')

        # A few quick checks
        if (last_voiced is None
                or self.topic_id != last_voiced.topic_id
                or len(last_voiced.stmts) == 0):
            if clz._logger.isEnabledFor(DEBUG_V):
                clz._logger.debug_v('controls different. Revoice = True')
                last_none: str = ''
                topic_ids_diff: str = ''
                zero_len: str = ''
                if last_voiced is None:
                    last_none = 'last voiced was none '
                elif self.topic_id != last_voiced.topic_id:
                    last_voice: Statements
                    topic_ids_diff = (f'topic ids different {self.topic_id} vs '
                                      f'{last_voiced.topic_id} ')
                elif len(last_voiced.stmts) == 0:
                    zero_len = 'last_voiced zero len'
                if clz._logger.isEnabledFor(DEBUG_V):
                    clz._logger.debug_v(f'Reasons: {last_none}{topic_ids_diff}{zero_len}')
            return True
        else:  # Compare the statements
            new_iter: StatementIterator = StatementIterator(self, stmt_filter)
            old_iter: StatementIterator = StatementIterator(last_voiced, stmt_filter)
            finished: bool = False
            while not finished:
                try:
                    new_stmt: Statement = next(new_iter)
                    # Now see if there is an old_stmt to compare against

                    old_stmt: Statement = next(old_iter, None)
                    if old_stmt is None:
                        #  Nothing to compare against. Must voice this statement
                        return True

                    if new_stmt.stmt_type != old_stmt.stmt_type:
                        if (new_stmt.stmt_type != StatementType.SILENT
                                and old_stmt.stmt_type != StatementType.SILENT):
                            if clz._logger.isEnabledFor(DEBUG_V):
                                clz._logger.debug_v(f'Statement types different revoice:'
                                                    f' True'
                                                    f'\n  new_stmt: {new_stmt}\n  '
                                                    f'prevous_stmt: {old_stmt}')
                            return True
                    if not new_stmt.variant and new_stmt != old_stmt:
                        return True

                except StopIteration:
                    # Ran out of new statements without finding a reason
                    # to revoice.
                    return False

    def as_phrases(self,
                   stmt_filter: List[StatementType] = None)\
            -> Tuple[PhraseList, PhraseList]:
        """
        Converts the Statements to two PhraseLists: text and hint-text
        :return: If VoiceHintToggle.OFF, then hint-text will be empty
                if VoiceHintToggle.ON, then text will contain a mixture of
                text and hint-text; hint-text will be empty
                if VoiceHintToggle.PAUSE, then text will contain text and
                hint-text will contain the hint text, so that they can be voiced
                separately.
        """
        clz = Statements
        if stmt_filter is None:
            stmt_filter = []

        phrases: PhraseList = PhraseList(check_expired=False)
        hint_phrases: PhraseList = PhraseList(check_expired=False)
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'topic: {self.topic_id}')
        new_iter: StatementIterator = StatementIterator(self, stmt_filter)
        while True:
            try:
                stmt: Statement
                stmt = next(new_iter)
                if stmt.stmt_type == StatementType.HINT_TEXT:
                    hint_phrases.extend(copy.deepcopy(stmt.phrases))
                else:
                    phrases.extend(copy.deepcopy(stmt.phrases))
            except StopIteration:
                break
        return phrases, hint_phrases

    def __repr__(self) -> str:
        clz = Statements
        result: str = f'topic: {self.topic_id}'
        for stmt in self.stmts:
            result = f'{result}\n  {stmt}'
        return result


class StatementIterator:
    """
    Simple iterator for Statements which take into account filtering for
    StatementType
    """

    def __init__(self, statements: Statements,
                 stmt_filter: List[StatementType] = None) -> None:
        """
        Create an iterator for the given statement and filter
        :param statements:
        :param stmt_filter: Combined with Statement.omitABLE, determines if
                       certain StatementTypes are omitted from voicing or
                       not. (StatementType.HINT_TEXT_ON_STARTUP)
        """
        self.stmts: Statements = statements
        self.stmt_filter: List[StatementType] = stmt_filter
        self.iterator = iter(self.stmts.stmts)

    def __next__(self) -> Statement:
        while True:
            nxt_stmt = next(self.iterator)

            # Skip over statements that have been filtered out

            if (not nxt_stmt.is_required(self.stmt_filter)
                    and nxt_stmt.omittable):
                continue  # Statement will be ignored, no impact on decision
            return nxt_stmt
