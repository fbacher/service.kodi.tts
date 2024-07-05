# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from pathlib import Path
from typing import Tuple

import xbmc
import xbmcgui

from common import *

from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.logger import *
from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui import button_model, ControlType, radio_button_model
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.group_list_model import GroupListModel
from gui.gui_worker import GuiWorkerQueue
from gui.label_model import LabelModel
from gui.parse_window import ParseWindow
from gui.topic_model import TopicModel
from gui.window_model import WindowModel
from windowNavigation.custom_settings_ui import SettingsGUI
from windows import WindowReaderBase
# from gui.window import Window
from . import guitables, skintables, windowparser
from .guitables import getWindowAddonID, WINDOW_HOME
from .window_state_monitor import WinDialog, WinDialogState, WindowStateMonitor
from .windowparser import WindowParser
from windows.ui_constants import AltCtrlType

CURRENT_SKIN = skintables.CURRENT_SKIN

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class CustomTTSReader(WindowReaderBase):
    ID = 'custom_tts'
    _logger: BasicLogger = None

    # window_cache: Dict[int, WindowModel] = {}
    current_reader: ForwardRef('CustomTTSReader') = None
    previous_topic_chain: List[TopicModel] = []

    @classmethod
    def get_instance(cls, window_id: int) -> ForwardRef('CustomTTSReader') | None:
        #  cls._logger.debug(f'current_reader: {cls.current_reader} window_id: {window_id}')
        simple_path: Path = Path(xbmc.getInfoLabel('Window.Property(xmlfile)'))
        if str(simple_path.name) != 'script-tts-settings-dialog.xml':
            return None
        if cls.current_reader is None:
            from service_worker import TTSService
            cls.current_reader = CustomTTSReader(window_id, TTSService.instance)
        if cls.current_reader is not None:
            #  cls._logger.debug(f'running: {cls.current_reader.is_running(window_id)}')
            return cls.current_reader
        return None


    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            # cls._logger = module_logger.getChild(cls.__class__.__name__)
            WindowStateMonitor.register_window_state_listener(cls.determine_focus_change,
                                                              "special")

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None) -> None:
        super().__init__(win_id, service)
        clz = type(self)
        # Disable old reader
        clz.current_reader = None
        simple_path: Path = Path(xbmc.getInfoLabel('Window.Property(xmlfile)'))
        # Refresh Window, Dialog, control and focus info
        WindowStateMonitor.check_win_dialog_state()
        clz._logger.debug(f'simple_path: {simple_path}')
        clz._logger.debug(f'simple_path.name: {simple_path.name}')
        self.window_id: int = WinDialogState.current_window_id
        self.dialog_id: int = WinDialogState.current_dialog_id
        if self.dialog_id != 9999:
            self.control_id = self.dialog_id
        else:
            self.control_id = self.window_id

        clz._logger.debug(f'window_id: {self.control_id}')
        self.window_heading_ctrl: xbmcgui.ControlLabel = None
        self.heading_ctrl: int = -1
        self.window_model: WindowModel | None = None
        self.is_dialog: bool = False

        window_parser: ParseWindow | None = None
        if str(simple_path.name) == 'script-tts-settings-dialog.xml':
            parser: ParseWindow = ParseWindow()
            parser.parse_window(control_id=self.control_id, xml_path=simple_path,
                                is_addon=True)
            # clz._logger.debug(f'DUMP PARSED:')
            # for result in parser.dump_parsed():
            #     clz._logger.debug(result)
            window_parser = parser
            #  clz._logger.debug(f'Number of parsers2: {len(parser.parsers)}')

            self.window_model: WindowModel = WindowModel(window_parser)
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'DUMP MODEL: \n{self.window_model}')

        clz.current_reader = self
        return

    def is_running(self, control_id: int) -> bool:
        clz = type(self)
        return clz.current_reader == self

    def direct_voicing_topics(self, topics_to_voice: List[TopicModel],
                              sequence_number: int,
                              focus_changed: bool = True) -> None:
        """
        Voice the controls/labels, etc. identified by topics_to_voice.

        :param topics_to_voice  A list of 'Topics' (labels, headings, values)
                                that need to be voiced in order (from
                                window headings down to details). Already
                                voiced items (such as window headings) have been
                                removed.
        :param sequence_number  Used to cancel stale tasks
        :param focus_changed  If True, voice every changed topic.
                                If False, voice any change in value for the
                                single topic

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
            parent: BaseModel = topic.parent
            success = parent.voice_control(phrases, focus_changed)

        # Rework interrupt so that window, heading, other levels can be individually
        # interrupted. In other words, if window stays the same, then you don't
        # have to interrupt voicing a window heading (just don't repeat it either).
        # Similar for other headings/groups. Requires some thought. Probably base
        # on how much 'topic chain' is altered.

        if not phrases.is_empty():
            phrase: Phrase = phrases[0]
            phrase.set_interrupt(True)
            self.service.sayText(phrases)

    """
        From DefaultReader
        def getHeading(self) -> PhraseList:
            text: str | None = xbmc.getInfoLabel('Control.GetLabel(1)')
            if text is None:
                text = ''
            return PhraseList.create(texts=text)
    """
    def getHeading(self, phrases: PhraseList) -> bool:
        return False

    def read_group_list(self, topic: TopicModel, phrases: PhraseList) -> bool:
        """
        Voice the UI type (value of 'alt_type' which is 'group list' by
        default)
        Next, voice alt_label.
        If no alt_label, voice any labeled_by
        Group Lists don't have a label to fall back on.
        """

        clz = type(self)
        success: bool = AltCtrlType.get_message(topic.alt_type, phrases)
        if not success:
            phrase = Phrase("Need to add support for non-topics")
            phrases.append(phrase)

        # Hint voice only when requested. Voice AFTER any label

        # Alt-Label Prefer if available
        # Label Second choice
        # Info Third choice
        # Labeled_by  Last choice
        #
        # What about extra voicing? label2, Info_labels?
        #
        # An alt-label has same syntax and symantics as a regular label:
        #  If int, then it is a message ID
        #
        # Message could be:
        #   An info expression
        # Messages are influenced by:
        # focusedlayouts
        # can come from label, fadelabel and textbox
        # more text can come from visibile children

        if topic.alt_label_expr != '':
            try:
                alt_msg_number: int = int(topic.alt_label_expr)
                success = Messages.add_msg_by_id(phrases, alt_msg_number,
                                                 empty_on_error=False)
            except:
                success = False
            if not success:
                success = True
                try:
                    text = xbmc.getInfoLabel(topic.alt_label_expr)
                    clz._logger.debug(f'geInfoLabel: {text}')
                    phrases.append(Phrase(text))
                except:
                    failed = True

        if not success and topic.labeled_by_expr != '':
            label_cntrl: BaseModel = self.window_model.get_control(topic.labeled_by_expr)
            label_cntrl: LabelModel
            clz._logger.debug(f'labeled_by: {topic.labeled_by_expr}')
            clz._logger.debug(f'label_cntrl: {label_cntrl is not None}')
            if label_cntrl is not None:
                success = label_cntrl.get_label_value(phrases)
        elif topic.label_expr != '':
            phrase = Phrase(text=f'topic label_expr: {topic.label_expr}')
            phrases.append(phrase)

        # phrases.extend(self.all_controls_speak())
        clz._logger.debug(f'{phrases}')
        return success

    def read_radio_button(self, topic: TopicModel) -> PhraseList:
        """
        Voice the UI type (value of 'alt_type' which is 'group list' by
        default)
        Next, voice alt_label.
        If no alt_label, voice any labeled_by
        Group Lists don't have a label to fall back on.
        """

        clz = type(self)
        phrases: PhraseList = PhraseList()
        phrase: Phrase = None
        success: bool = AltCtrlType.get_message(topic.alt_type, phrases)
        if not success:
            phrase = Phrase("Need to add support for non-topics")
            phrases.append(phrase)

        # Hint voice only when requested. Voice AFTER any label

        # Alt-Label Prefer if available
        # Label Second choice
        # Info Third choice
        # Labeled_by  Last choice
        #
        # What about extra voicing? label2, Info_labels?
        #
        # An alt-label has same syntax and symantics as a regular label:
        #  If int, then it is a message ID
        #
        # Message could be:
        #   An info expression
        # Messages are influenced by:
        # focusedlayouts
        # can come from label, fadelabel and textbox
        # more text can come from visibile children

        success: bool = True
        if topic.alt_label_expr != '':
            try:
                alt_msg_number: int = int(topic.alt_label_expr)
                msg: str = Messages.get_msg_by_id(alt_msg_number)
                phrases.append(Phrase(msg))
            except:
                success = False
            if not success:
                try:
                    text = xbmc.getInfoLabel(topic.alt_label_expr)
                    clz._logger.debug(f'geInfoLabel: {text}')
                    phrases.append(Phrase(text))
                    success = True
                except:
                    success = False

        if not success and topic.labeled_by_expr != '':
            label_cntrl: BaseModel = self.window_model.get_control(topic.labeled_by_expr)
            label_cntrl: LabelModel
            clz._logger.debug(f'labeled_by: {topic.labeled_by_expr}')
            clz._logger.debug(f'label_cntrl: {label_cntrl is not None}')
            if label_cntrl is not None:
                success = label_cntrl.get_label_text(phrases)
        elif topic.label_expr != '':
            phrase = Phrase(text=f'topic label_expr: {topic.label_expr}')
            phrases.append(phrase)

        # phrases.extend(self.all_controls_speak())
        clz._logger.debug(f'{phrases}')
        return phrases

    """

    def getItemExtraTexts(self, control_id) -> PhraseList:
        clz = type(self)
        phrases: PhraseList = guitables.getItemExtraTexts(self.winID)
        text: str | List[str] | None = None
        if phrases.is_empty():
            text = xbmc.getInfoLabel('ListItem.Plot')
            if not text:
                text = xbmc.getInfoLabel('Container.ShowPlot')
            if not text:
                text = xbmc.getInfoLabel('ListItem.Property(Artist_Description)')
            if not text:
                text = xbmc.getInfoLabel('ListItem.Property(Album_Description)')
            if not text:
                text = xbmc.getInfoLabel('ListItem.Property(Addon.Description)')
            if not text:
                text = guitables.getSongInfo()
            if not text:
                tmp_phrases: PhraseList = self.getControlText(control_id)
                tmp_item_extras: PhraseList
                tmp_item_extras = parseItemExtra(control_id, excludes=tmp_phrases)
                phrases.extend(tmp_item_extras)
            if phrases.is_empty() and text is not None:
                if not isinstance(text, list):
                    text = [text]
                for txt in text:
                    phrases.append(Phrase(text=txt))
        return phrases

    """
    """
    def get_section_heading(self, phrases: PhraseList) -> bool:
        clz = type(self)
        success: bool = False
        topic: TopicModel = self.window_model.topic
        # if topic is None:
        #     return self.get_heading_without_topic()

        clz._logger.debug(f'Topic name: {topic.name}')
        topic_type: str = topic.alt_type
        if topic_type != '':
            phrases.add_text(texts=f'{topic_type}')
            success = True
        if topic.labeled_by_expr != '':
            label_cntrl: BaseModel = self.window_model.get_control(topic.labeled_by_expr)
            label_cntrl: LabelModel
            clz._logger.debug(f'labeled_by: {topic.labeled_by_expr}')
            clz._logger.debug(f'label_cntrl: {label_cntrl is not None}')
            if label_cntrl is not None:
                phrase_list: PhraseList = label_cntrl.get_label_text()
                phrases.extend(phrase_list)
        elif topic.label_expr != '':
            phrase = Phrase(text=f'label: {topic.label_expr}')
            phrases.append(phrase)
        return phrases

    def get_hint_text(self) -> PhraseList:
        clz = type(self)
        phrases: PhraseList = PhraseList()
        topic: TopicModel = self.window_model.topic
        if topic is None:
            pass
            return phrases

        clz._logger.debug(f'Topic name: {topic.name}')
        topic_type: str = topic.alt_type
        if topic_type != '':
            try:
                msg_id: int = int(topic_type)
                text: str = xbmc.getLocalizedString(msg_id)
                phrase: Phrase = Phrase(text=text)
                phrases.append(phrase)
            except ValueError as e:
                reraise(*sys.exc_info())

        if topic.hint_text_expr != '':
            try:
                msg_id: int = int(topic.hint_text_expr)
                text: str = xbmc.getLocalizedString(msg_id)
                phrase: Phrase = Phrase(text=text)
                phrases.append(phrase)
            except ValueError as e:
                reraise(*sys.exc_info())
        return phrases

        # text: str = xbmc.getInfoLabel(f"Control.GetLabel({heading_id})")
        #
        # clz._logger.debug(f'Control.GetLabel(heading_id): {heading}')
        # return PhraseList.create(texts=f'The heading is: {heading}')

    def get_heading_without_topic(self) -> PhraseList:
        clz = type(self)
        heading_id_expr: str = self.window_model.get_window_heading_id()
        heading_id: int = -1
        try:
            heading_id = int(heading_id_expr)
        except Exception as e:
            clz._logger.exception('')

        # Getting heading via copy of window doesn't work

        clz._logger.debug(f'dialog_id: {self.dialog_id} heading_id: {heading_id}')
        self.window_heading_ctrl = self.window.getControl(heading_id)
        self.window_heading_ctrl: xbmcgui.ControlLabel
        heading: str = self.window_heading_ctrl.getLabel()
        clz._logger.debug(f'heading: {heading}')
        clz._logger.debug(f'label_id: {heading_id}')
        clz._logger.debug(f'control: {self.window_heading_ctrl}')

        if SettingsGUI.gui is not None:
            window: xbmcgui.WindowDialog
            if WinDialogState.current_windialog == WinDialog.DIALOG:
                window = WinDialogState.current_dialog_instance
            else:
                window: xbmcgui.Window  = WinDialogState.current_window_instance

        # Works
        addon_id: str = getWindowAddonID(self.dialog_id)
        clz._logger.debug(f'addon_id: {addon_id}')

        # Works, but at whim of currentControl
        text: str = xbmc.getInfoLabel('System.CurrentControl')
        clz._logger.debug(f'System.CurrentControl: {text}')

        # CurrentWindow: 'System'
        window_name: str = xbmc.getInfoLabel('System.CurrentWindow')
        clz._logger.debug(f'System.CurrentWindow: {window_name}')

        # At default control: 100
        text: str = xbmc.getInfoLabel('System.CurrentControlId')
        clz._logger.debug(f'System.CurrentControlId: {text}')

        # Can't Find Window System?
        window_is: str = xbmc.getInfoLabel(f"Window.IS('{window_name}')")
        clz._logger.debug(f'Window.IS({window_name}):'
                          f' {window_is}')
        window_is = xbmc.getInfoLabel(f"Window.ISVisible('{window_name}')")
        clz._logger.debug(f"Window.ISVisible({window_name}): "
                          f'{window_is}')
        window_is = xbmc.getInfoLabel(f"Window.ISTopmost('{window_name}')")
        clz._logger.debug(f"Window.ISTopmost({window_name}): "
                          f'{window_is}')
        window_is = xbmc.getInfoLabel(f"Window.ISDialogTopmost('{window_name}')")
        clz._logger.debug(f"Window.ISDialogTopmost({window_name}): "
                          f'{window_is}')

        # BEST solution:

        text: str = xbmc.getInfoLabel(f"Control.GetLabel({heading_id})")
        clz._logger.debug(f'Control.GetLabel(heading_id): {text}')
        '''
        control_id: int = 1
        Control.HasFocus(control_id)
        Control.IsVisible(control_id)
        Control.IsEnabled(control_id)

        Control.GetLabel(control_id)

        # Only for Edit controls:
        Control.GetLabel(control_id).index(0)
        Control.GetLabel(control_id).index(1)

        ActivateWindow(dialog_id)
        ActivateWindowAndFocus(dialog_id, control_1, control2)
        Dialog.Close(dialog_id, force=True)
        ReplaceWindow(dialog_id)
        ReplaceWindowAndFocus(dialog_id, control_id)
        control.setfocus(control_id)
        '''

        # window: xbmcgui.Window = xbmcgui.Window(addon_id)
        # clz._logger.debug(f'window: {window}')
        # heading_ctrl = window.getControl(1)
        # clz._logger.debug(f'heading_ctrl: {heading_ctrl}')
        # heading: str = heading_ctrl.getLabel()
        # clz._logger.debug(f'heading: {heading}')

        heading: str = xbmc.getInfoLabel(f"Control.GetLabel({heading_id})")
        clz._logger.debug(f'Control.GetLabel(heading_id): {heading}')
        return PhraseList.create(texts=f'The heading is: {heading}')

    def get_topic_heading(self, control_id_expr: str) -> PhraseList:
        clz = type(self)
        heading_id_expr: str = self.window_model.get_window_heading_id()
        heading_id: int = -1
        try:
            heading_id = int(heading_id_expr)
        except Exception as e:
            clz._logger.exception('')

        # Getting heading via copy of window doesn't work

        clz._logger.debug(f'dialog_id: {self.dialog_id} heading_id: {heading_id}')
        self.window_heading_ctrl = self.window.getControl(heading_id)
        self.window_heading_ctrl: xbmcgui.ControlLabel
        heading: str = self.window_heading_ctrl.getLabel()
        clz._logger.debug(f'heading: {heading}')
        clz._logger.debug(f'label_id: {heading_id}')
        clz._logger.debug(f'control: {self.window_heading_ctrl}')

        if SettingsGUI.gui is not None:
            # Using original Window DOES work, but frequently we can't access it

            self.window_heading_ctrl: xbmcgui.Control = SettingsGUI.gui.getControl(heading_id)
            self.window_heading_ctrl: xbmcgui.ControlLabel
            heading: str = self.window_heading_ctrl.getLabel()
            clz._logger.debug(f'heading: {heading}')
            clz._logger.debug(f'label_id: {heading_id}')
            clz._logger.debug(f'control: {self.window_heading_ctrl}')

        # Works
        addon_id: str = getWindowAddonID(self.dialog_id)
        clz._logger.debug(f'addon_id: {addon_id}')

        # Works, but at whim of currentControl
        text: str = xbmc.getInfoLabel('System.CurrentControl')
        clz._logger.debug(f'System.CurrentControl: {text}')

        # CurrentWindow: 'System'
        window_name: str = xbmc.getInfoLabel('System.CurrentWindow')
        clz._logger.debug(f'System.CurrentWindow: {window_name}')

        # At default control: 100
        text: str = xbmc.getInfoLabel('System.CurrentControlId')
        clz._logger.debug(f'System.CurrentControlId: {text}')

        # Can't Find Window System?
        window_is: str = xbmc.getInfoLabel(f"Window.IS('{window_name}')")
        clz._logger.debug(f'Window.IS({window_name}):'
                          f' {window_is}')
        window_is = xbmc.getInfoLabel(f"Window.ISVisible('{window_name}')")
        clz._logger.debug(f"Window.ISVisible({window_name}): "
                          f'{window_is}')
        window_is = xbmc.getInfoLabel(f"Window.ISTopmost('{window_name}')")
        clz._logger.debug(f"Window.ISTopmost({window_name}): "
                          f'{window_is}')
        window_is = xbmc.getInfoLabel(f"Window.ISDialogTopmost('{window_name}')")
        clz._logger.debug(f"Window.ISDialogTopmost({window_name}): "
                          f'{window_is}')

        # BEST solution:

        text: str = xbmc.getInfoLabel(f"Control.GetLabel({heading_id})")
        clz._logger.debug(f'Control.GetLabel(heading_id): {text}')
        '''
        control_id: int = 1
        Control.HasFocus(control_id)
        Control.IsVisible(control_id)
        Control.IsEnabled(control_id)

        Control.GetLabel(control_id)

        # Only for Edit controls:
        Control.GetLabel(control_id).index(0)
        Control.GetLabel(control_id).index(1)

        ActivateWindow(dialog_id)
        ActivateWindowAndFocus(dialog_id, control_1, control2)
        Dialog.Close(dialog_id, force=True)
        ReplaceWindow(dialog_id)
        ReplaceWindowAndFocus(dialog_id, control_id)
        control.setfocus(control_id)
        '''

        # window: xbmcgui.Window = xbmcgui.Window(addon_id)
        # clz._logger.debug(f'window: {window}')
        # heading_ctrl = window.getControl(1)
        # clz._logger.debug(f'heading_ctrl: {heading_ctrl}')
        # heading: str = heading_ctrl.getLabel()
        # clz._logger.debug(f'heading: {heading}')

        heading: str = xbmc.getInfoLabel(f"Control.GetLabel({heading_id})")
        clz._logger.debug(f'Control.GetLabel(heading_id): {heading}')
        return PhraseList.create(texts=f'The heading is: {heading}')
    """
    """
        From DefaultReader
        def getWindowTexts(self) -> PhraseList:
            return guitables.getWindowTexts(self.winID)
    """

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        """
            Add param to indicate how much text (topic titles, content of
            particular top, etc.)
        :return:
        """
        return False

        '''
        clz = type(self)
        clz._logger.debug(f'In getWindowTexts')
        """
        This information comes from <topic> element. Can also provide values
        through control attributes. That means we need access to the appropriate
        controls. The question is how?

        A control with a topic element, is diretly associated with that topic,
        even if the topic does not use anything from that element. Similarly,
        a control with topic attributes is similarly bound. What happens when
        there are both topic attributes and topic element?

        To simply voice focused objects (and any non-focused controls that
        topic references) We could simply look for a topic for the current
        control.

        However, to traverse a window that does not have objects with focus,
        or even to traverse one that has focus objects, you need a navigation map.
        You need to know the order to traverse topics. Also, you need to be able
        to go down into more detail, or up into less. To accomplish this you need
        a map, indexed by topic-id. The window must have a topic that begins the
        navigation. Controls that need to be voiced must also have a topic that
        is placed in the window's map of topics.

           self.parent: BaseModel = parent  # Refers to original control
        self.name: str = parsed_topic.name
        self.label_expr: str = parsed_topic.label_expr
        self.description: str = parsed_topic.description
        self.hint_text_expr: str = parsed_topic.hint_text_expr
        self.info_expr: str = parsed_topic.info_expr
        self.topic_left: str = parsed_topic.topic_left
        self.topic_right: str = parsed_topic.topic_right
        self.topic_up: str = parsed_topic.topic_up
        self.topic_down: str = parsed_topic.topic_down
        self.alt_type: str = parsed_topic.alt_type
        self.rank: int = parsed_topic.rank
        Children can be Descriptions
        
        phrases: PhraseList = PhraseList.create(texts='Get Window Texts')
        """
        for topic_name, topic in self.get_ordered_topics():
            topic_name: str
            topic: TopicModel
            clz._logger.debug(f'Topic name: {topic_name}')
            phrase: Phrase = None
            if topic.label_expr != '':
                phrase = Phrase(text=f'label: {topic.label_expr}')
                phrases.append(phrase)
            if topic.info_expr != '':
                phrase = Phrase(text=f'info: {topic.info_expr}')
                phrases.append(phrase)
            if topic.hint_text_expr != '':
                phrase = Phrase(text=f'hint: {topic.hint_text_expr}')
                phrases.append(phrase)
            if topic.alt_type != '':
                phrase = Phrase(f'alt_type: {topic.alt_type}')
                phrases.append(phrase)
            if topic.name != '':
                phrase = Phrase(f'name: {topic.name}')
                phrases.append(phrase)
            if topic.description != '':
                phrase = Phrase(f'description: {topic.description}')
                phrases.append(phrase)
            if topic.topic_left != '':
                phrase = Phrase(f'topic_left: {topic.topic_left}')
                phrases.append(phrase) `
            #                self.topic_right: str = parsed_topic.topic_right
            #    self.topic_up: str = parsed_topic.topic_up
            #    self.topic_down: str = parsed_topic.topic_down
            #     self.rank: int = parsed_topic.rank
            """

        for topic_name, topic in self.get_ordered_topics().items():
            topic_name: str
            topic: TopicModel
            phrase: Phrase = None

            clz._logger.debug(f'Topic name: {topic_name}')
            topic_type: str = topic.alt_type
            if topic_type != '':
                phrase = Phrase(f'{topic_type}')
                phrases.append(phrase)

            if topic.label_expr != '':
                phrase = Phrase(text=f'label: {topic.label_expr}')
                phrases.append(phrase)
            #                self.topic_right: str = parsed_topic.topic_right
            #    self.topic_up: str = parsed_topic.topic_up
            #    self.topic_down: str = parsed_topic.topic_down
            #     self.rank: int = parsed_topic.rank
        return phrases
        '''
        return PhraseList()

    def all_controls_speak(self) -> PhraseList:
        clz = type(self)
        phrases: PhraseList = PhraseList()
        phrase: Phrase
        current_item: int = 0
        """
            Since many controls don't have ids we have to resort
            to our own 'topic' elements to get needed label and
            other info. Prefer to use topic information, with backup
            to use control info (not yet implemented). 
            
            Topic.parent references the control which it is also a 
            child of. By having a topic for each control, we can use
            topics to traverse all controls/elements. While it is 
            much prefered to have hand-built topics, they can be 
            generated from controls. The advantage with topics is
            that they are all named (although the synthesized name
            is not the best). Naming allows using maps to find what you
            need without combersome searches. 
            
            Note that topic elements are children of the control.
            There can be only one topic per control. Perhaps there
            should be a control.topic field instead of them being 
            a child. Anyway, depending upon context and 
            availability, a label may come from a topic or a control.
            The preference is to use a label from a topic, since it
            is more granular (alt-label, hint, heading, etc.). But
            labels can come from controls (infolabel, label, etc.)
        """
        for topic_name, topic in self.get_ordered_topics().items():
            topic_name: str
            topic: TopicModel
            # phrase = Phrase('Topic:')
            # phrases.append(phrase)
            # phrase = Phrase(topic.name)
            # phrases.append(phrase)

            """
               Voice the control type. Prefer to get from topic, 
               since it can be customized.
               Next, voice any heading for the control ("Dialog, Heading:
               TTS Settings")
               Proceed to zoom in to the item with focus, voicing each
               category/heading/control/ item along the way.
            """

            # Voice type of control Prefer alt_type from topic

            alt_type: AltCtrlType = None
            if topic.alt_type != '':
                success: bool = AltCtrlType.get_message(topic.alt_type, phrases)

            """
               After voicing control type ("Button List, 5 items")
               Voice the control's / category's  label. ("Item one, 
               Engine Settings,")
               
               Prefer alt_label from topic, but fall back to label (if
               it has an id, or if we can grab the msg#, etc. from the 
               control's xml). Rmember, a topic's control is the topic's
               parent.
            """

            if topic.alt_label_expr != '':
                success = topic.get_alt_label(phrases)
            elif (hasattr(topic.parent, 'label_expr') and
                  topic.parent.label_expr != ''):
                clz._logger.debug(f'parent: {topic.parent}')
                clz._logger.debug(f'label_expr: {topic.parent.label_expr}')
                parent_model: BaseModel = topic.parent
                parent_model: BaseLabelModel
                success = parent_model.get_label_text(phrases)

            # Only controls with multiple visible items have item counts

            if alt_type == AltCtrlType.BUTTON_LIST:
                group_list: GroupListModel = topic.parent
                success = group_list.read_group_list(phrases)

        return phrases

    def get_ordered_topics(self) -> Dict[str, TopicModel]:
        return self.window_model.ordered_topics_by_name

    """
    From Default reader
    def getControlDescription(self, control_id) -> PhraseList:
        clz = type(self)
        phrases: PhraseList
        phrases = skintables.getControlText(self.winID, control_id)
        return phrases
    """

    def getControlDescription(self, control_id) -> PhraseList:
        return PhraseList()
        '''
        clz = type(self)
        phrases: PhraseList
        clz._logger.debug(f'In getControlDescription')

        return PhraseList.create(texts=f'Missing control description for id: '
                                 f'{control_id}')
        '''
    """
    From Default Reader    
    def getControlText(self, control_id: int) -> PhraseList:
        clz = type(self)
        text: str
        if self.slideoutHasFocus():
          return self.getSlideoutText(control_id)
        
        if control_id is not None:
          return PhraseList()
        text: str | None = xbmc.getInfoLabel('ListItem.Title')
        text2: str | None = None
        if text and clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
          clz._logger.debug_extra_verbose(f'text: {text}')
        if not text:
          text = xbmc.getInfoLabel(f'Container({control_id}).ListItem.Label')
          text2 = xbmc.getInfoLabel(f'Container({control_id}).ListItem.Label2')
          if text and clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
              clz._logger.debug_extra_verbose(f'text: {text} text2: {text2}')
        if not text:
          text = xbmc.getInfoLabel(f'Control.GetLabel({control_id})')
          if text and clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
              clz._logger.debug_extra_verbose(f'text: {text}')
        if not text:
          text = xbmc.getInfoLabel('System.CurrentControl')
          if text and clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
              clz._logger.debug_extra_verbose(f'text: {text}')
        if not text:
          return PhraseList()
        text_id: str = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel(
              'ListItem.EndTime')
        texts: List[str] = [text]
        if text2 is not None:
          texts.append(text2)
        phrases: PhraseList = PhraseList.create(texts=texts)
        phrase: Phrase
        for phrase in phrases:
          phrase.set_text_id(text_id)
        return phrases
    """

    def getControlText(self, control_id: int) -> PhraseList:
        """
            Prefer alt-label over label. Use labeled_by and label_for if
            needed.
        :param control_id:
        :return:

        BasicReader returns xbmc.getInfoLabel('System.CurrentControl')
        DefaultReader is MUCH more involved.
        LibraryViews does more stuff
        pvr does special stuff
        ... other specialized stuff
        """
        return PhraseList()
        '''
        clz = type(self)
        clz._logger.debug(f'In getControlText')
        if control_id == 0:
            return 5 / control_id
        control_model: BaseModel = self.window_model.control_id_map.get(control_id)
        clz._logger.debug(f'Got control_model: {control_model} for control_id: '
                          f'{control_id}')

        text: str = xbmc.getInfoLabel(f'Control.GetLabel({control_id})')
        clz._logger.debug(f'Control.GetLabel(control_id): {control_id} text: {text}')
        return PhraseList.create(texts=f'The control text for {control_id} is: {text}')
        '''
    """
        From Default Reader
    def getSecondaryText(self) -> PhraseList:
        clz = type(self)
        phrases: PhraseList = PhraseList()
        phrase: Phrase = guitables.getListItemProperty(self.winID)
        if not phrase.is_empty():
            phrases.append(phrase)
        return phrases
    """

    def getSecondaryText(self) -> PhraseList:
        """
        Current code tries to get ListItem.Property(Addon.Status)

        :return:
        """
        return PhraseList()
        '''
        clz = type(self)
        clz._logger.debug(f'In getSecondaryText')
        phrases: PhraseList = PhraseList()
        text: str = xbmc.getInfoLabel(f'Control.GetLabel(ListItem.Property(Addon.Status))')
        phrase: Phrase = Phrase(text=f'{text}')
        phrases.append(phrase)
        return phrases
        '''

    def getItemExtraTexts(self, control_id) -> PhraseList:
        return PhraseList()
        '''
        clz = type(self)
        clz._logger.debug(f'getItemExtraTexts')
        return PhraseList.create(texts='Missing get Item Extra Texts for '
                                       f'control {control_id}')
        '''

    # HACK

    #  determine_focus_change_first_time: bool = True
