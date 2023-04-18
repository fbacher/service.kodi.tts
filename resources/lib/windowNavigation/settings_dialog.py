# -*- coding: utf-8 -*-

from common.typing import *

import xbmc
import xbmcgui
from xbmcgui import (Control, ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider, ControlList, ControlImage,
                     ControlTextBox, ListItem)
import xbmcaddon

from windowNavigation.action_map import Action
from windowNavigation.selection_dialog import SelectionDialog
from backends.backend_info import BackendInfo
from backends.base import *
from common.constants import Constants
from common.settings import Settings
from common.messages import Messages
from common.setting_constants import Backends, Players, Genders
from common.logger import *

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()


class SettingsDialog(xbmcgui.WindowXMLDialog):
    HEADER_LABEL: Final[int] = 2
    ENGINE_TAB: Final[int] = 100
    OPTIONS_TAB: Final[int] = 200
    KEYMAP_TAB: Final[int] = 300
    ADVANCED_TAB: Final[int] = 400
    OK_BUTTON: Final[int] = 28
    CANCEL_BUTTON: Final[int] = 29
    DEFAULTS_BUTTON: Final[int] = 30
    ENGINE_GROUP_LIST: Final[int] = 101
    SELECT_ENGINE_BUTTON: Final[int] = 102
    FIRST_SELECT_ID: Final[int] = SELECT_ENGINE_BUTTON
    SELECT_ENGINE_VALUE_LABEL: Final[int] = 103
    SELECT_LANGUAGE_GROUP: Final[int] = 1104
    SELECT_LANGUAGE_BUTTON: Final[int] = 104
    SELECT_LANGUAGE_VALUE_LABEL: Final[int] = 105
    SELECT_VOICE_BUTTON: Final[int] = 106
    SELECT_VOICE_VALUE_LABEL: Final[int] = 107
    SELECT_GENDER_BUTTON: Final[int] = 108
    SELECT_GENDER_VALUE_LABEL: Final[int] = 109
    SELECT_PLAYER_BUTTON: Final[int] = 110
    SELECT_PLAYER_VALUE: Final[int] = 111
    SELECT_VOLUME_GROUP: Final[int] = 1112
    SELECT_VOLUME_LABEL: Final[int] = 112
    SELECT_VOLUME_SLIDER: Final[int] = 113
    SELECT_PITCH_GROUP: Final[int] = 1114
    SELECT_PITCH_LABEL: Final[int] = 114
    SELECT_PITCH_SLIDER: Final[int] = 115
    SELECT_SPEED_GROUP: Final[int] = 1116
    SELECT_SPEED_LABEL: Final[int] = 116
    SELECT_SPEED_SLIDER: Final[int] = 117
    SELECT_CACHE_GROUP: Final[int] = 1118
    SELECT_CACHE_BUTTON: Final[int] = 118
    SELECT_PIPE_GROUP: Final[int] = 1120
    SELECT_PIPE_BUTTON: Final[int] = 120
    SELECT_API_KEY_GROUP: Final[int] = 1122
    SELECT_API_KEY_EDIT: Final[int] = 122
    LAST_SELECT_ID: Final[int] = SELECT_API_KEY_EDIT
    OPTIONS_GROUP: Final[int] = 201
    OPTIONS_DUMMY_BUTTON: Final[int] = 202
    KEYMAP_GROUP: Final[int] = 301
    KEYMAP_DUMMY_BUTTON: Final[int] = 302
    ADVANCED_GROUP: Final[int] = 401
    ADVANCED_DUMMY_BUTTON: Final[int] = 402

    def __init__(self, *args, **kwargs) -> None:
        """

        :param args:
        """
        # xbmc.executebuiltin('Skin.ToggleDebug')

        self._logger: BasicLogger = module_logger.getChild(self.__class__.__name__)
        self._initialized: bool = False
        self.exit_dialog: bool = False
        super().__init__(*args)
        self.api_key = None
        self.engine: str = None
        self.engine_instance = None
        self.engine_class = None
        self.backend_changed: bool = False
        self.gender: str = None
        self.language: str = None
        self.pitch: float = None
        self.player: str = None
        self.speed: float = None
        self.volume: int = None
        self.settings_changed: bool = False
        self.previous_engine: str = None
        initial_backend = Settings.getSetting(Settings.BACKEND, self.engine,
                                              Settings.BACKEND_DEFAULT)

        if initial_backend == Settings.BACKEND_DEFAULT:  # 'auto'
            initial_backend = BackendInfo.getAvailableBackends()[0].backend_id
            self.set_engine_id(initial_backend)
        else:
            self.getEngineClass(engine_id=initial_backend)

        self._logger.debug_extra_verbose('SettingsDialog.__init__')
        self.header: Union[ControlLabel, None] = None
        self.engine_tab: Union[ControlRadioButton, None] = None
        self.options_tab: Union[ControlButton, None] = None
        self.keymap_tab: Union[ControlButton, None] = None
        self.advanced_tab: Union[ControlButton, None] = None
        self.engine_group: Union[ControlGroup, None] = None
        self.options_group: Union[ControlGroup, None] = None
        self.keymap_group: Union[ControlGroup, None] = None
        self.advanced_group: Union[ControlGroup, None] = None
        self.ok_button: Union[ControlButton, None] = None
        self.cancel_button: Union[ControlButton, None] = None
        self.defaults_button: Union[ControlButton, None] = None
        self.engine_engine_button: Union[ControlButton, None] = None
        self.engine_engine_value: Union[ControlButton, None] = None
        self.engine_language_group: Union[ControlGroup, None] = None
        self.engine_language_button: Union[ControlButton, None] = None
        self.engine_language_value = None
        self.engine_voice_button: Union[ControlButton, None] = None
        self.engine_voice_value = None
        self.engine_gender_button: Union[ControlButton, None] = None
        self.engine_gender_value = None
        self.engine_pitch_group: Union[ControlGroup, None] = None
        self.engine_pitch_slider: Union[ControlSlider, None] = None
        self.engine_pitch_label: Union[ControlLabel, None] = None
        self.engine_player_button: Union[ControlLabel, None] = None
        self.engine_player_value = None
        self.engine_pipe_audio_group: Union[ControlGroup, None] = None
        self.engine_pipe_audio_radio_button: Union[ControlRadioButton, None] = None
        self.engine_speed_group: Union[ControlGroup, None] = None
        self.engine_speed_slider: Union[ControlSlider, None] = None
        self.engine_speed_label: Union[ControlLabel, None] = None
        self.engine_cache_speech_group: Union[ControlGroup, None] = None
        self.engine_cache_speech_radio_button: Union[ControlRadioButton, None] = None
        self.engine_volume_group: Union[ControlGroup, None] = None
        self.engine_volume_slider: Union[ControlSlider, None] = None
        self.engine_volume_label: Union[ControlLabel, None] = None
        self.engine_api_key_group: Union[ControlGroup, None] = None
        # self.engine_api_key_label = None
        self.engine_api_key_edit: Union[ControlEdit, None] = None
        self.options_dummy_button: Union[ControlButton, None] = None
        self.keymap_dummy_button: Union[ControlButton, None] = None
        self.advanced_dummy_button: Union[ControlButton, None] = None

    def onInit(self) -> None:
        """

        :return:
        """
        # super().onInit()
        clz = type(self)
        self._logger.debug_verbose('SettingsDialog.onInit')

        if not self._initialized:

            self.header = self.getControlLabel(clz.HEADER_LABEL)
            addon_id = xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('id')
            addon_name = xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('id')
            self.header.setLabel('{} - {}'.format(Messages.get_msg(Messages.SETTINGS),
                                                  addon_name))
            self.engine_tab = self.getControlRadioButton(clz.ENGINE_TAB)
            self.engine_tab.setLabel(Messages.get_msg(Messages.ENGINE))
            self.engine_tab.setRadioDimension(x=0, y=0, width=186, height=40)
            self.engine_tab.setVisible(True)
            self.options_tab = self.getControlButton(
                    clz.OPTIONS_TAB)
            self.options_tab.setLabel(Messages.get_msg(Messages.OPTIONS))
            self.options_tab.setVisible(True)

            self.keymap_tab = self.getControlButton(
                    clz.KEYMAP_TAB)
            self.keymap_tab.setLabel(Messages.get_msg(Messages.KEYMAP))
            self.keymap_tab.setVisible(True)

            self.advanced_tab = self.getControlButton(
                    clz.ADVANCED_TAB)
            self.advanced_tab.setLabel(Messages.get_msg(Messages.ADVANCED))
            self.advanced_tab.setVisible(True)

            self.ok_button: ControlButton = self.getControlButton(
                    clz.OK_BUTTON)
            self.ok_button.setLabel(Messages.get_msg(Messages.OK))
            self.ok_button.setVisible(True)

            self.cancel_button = self.getControlButton(
                    clz.CANCEL_BUTTON)
            self.cancel_button.setLabel(Messages.get_msg(Messages.CANCEL))
            self.cancel_button.setVisible(True)

            self.defaults_button: ControlButton = self.getControlButton(
                    clz.DEFAULTS_BUTTON)
            self.defaults_button.setLabel(Messages.get_msg(Messages.DEFAULTS))
            self.defaults_button.setVisible(True)

            # self.engine_group = self.getControlGroup(101)
            # self.engine_group.setVisible(True)

            self.engine_engine_button = self.getControlButton(
                    clz.SELECT_ENGINE_BUTTON)
            self.engine_engine_button.setLabel(
                    Messages.get_msg(Messages.DEFAULT_TTS_ENGINE))

            self.engine_engine_value = self.getControlLabel(
                    clz.SELECT_ENGINE_VALUE_LABEL)
            engine_label = Backends.get_label(self.get_engine(init=True))
            self.engine_engine_value.setLabel(engine_label)

            self.engine_language_group = self.getControlGroup(
                    clz.SELECT_LANGUAGE_GROUP)
            self.engine_language_button: ControlButton = self.getControlButton(
                    clz.SELECT_LANGUAGE_BUTTON)
            self.engine_language_button.setLabel(
                    Messages.get_msg(Messages.SELECT_LANGUAGE))

            self.engine_language_value = self.getControlLabel(
                    clz.SELECT_LANGUAGE_VALUE_LABEL)
            self.engine_language_value.setLabel(self.get_language())

            self.engine_voice_button: ControlButton = self.getControlButton(
                    clz.SELECT_VOICE_BUTTON)
            self.engine_voice_button.setLabel(
                    Messages.get_msg(Messages.SELECT_VOICE))

            self.engine_voice_value = self.getControlLabel(
                    clz.SELECT_VOICE_VALUE_LABEL)
            self.engine_voice_value.setLabel(self.get_language())

            self.engine_gender_button: ControlButton = self.getControlButton(
                    clz.SELECT_GENDER_BUTTON)
            self.engine_gender_button.setLabel(
                    Messages.get_msg(Messages.SELECT_VOICE_GENDER))

            self.engine_gender_value = self.getControlLabel(
                    clz.SELECT_GENDER_VALUE_LABEL)
            self.engine_gender_value.setLabel(self.get_gender())

            self.engine_pitch_group = self.getControlGroup(
                    clz.SELECT_PITCH_GROUP)
            self.engine_pitch_label = self.getControlLabel(
                    clz.SELECT_PITCH_LABEL)
            self.engine_pitch_label.setLabel(
                    Messages.get_msg(Messages.SELECT_PITCH))

            self.engine_pitch_slider = self.getControlSlider(
                    clz.SELECT_PITCH_SLIDER)

            self.engine_player_button = self.getControlLabel(
                    clz.SELECT_PLAYER_BUTTON)
            self.engine_player_button.setLabel(
                    Messages.get_msg(Messages.SELECT_PLAYER))

            self.engine_player_value = self.getControlButton(
                    clz.SELECT_PLAYER_VALUE)
            self.engine_player_value.setLabel(self.get_player())

            self.engine_cache_speech_group = self.getControlGroup(
                    clz.SELECT_CACHE_GROUP)
            self.engine_cache_speech_radio_button: ControlRadioButton = \
                self.getControlRadioButton(
                        clz.SELECT_CACHE_BUTTON)
            self.engine_cache_speech_radio_button.setLabel(
                    Messages.get_msg(Messages.CACHE_SPEECH))

            self.engine_pipe_audio_group = self.getControlGroup(
                    clz.SELECT_PIPE_GROUP)
            self.engine_pipe_audio_radio_button = self.getControlRadioButton(
                    clz.SELECT_PIPE_BUTTON)
            self.engine_pipe_audio_radio_button.setLabel(
                    Messages.get_msg(Messages.PIPE_AUDIO))

            self.engine_speed_group = self.getControlGroup(
                    clz.SELECT_SPEED_GROUP)
            self.engine_speed_label = self.getControlLabel(
                    clz.SELECT_SPEED_LABEL)
            self.engine_speed_label.setLabel(
                    Messages.get_msg(Messages.SELECT_SPEED))

            self.engine_speed_slider = self.getControlSlider(
                    clz.SELECT_SPEED_SLIDER)

            self.engine_volume_group = self.getControlGroup(
                    clz.SELECT_VOLUME_GROUP)
            self.engine_volume_label = self.getControlLabel(
                    clz.SELECT_VOLUME_LABEL)
            self.engine_volume_label.setLabel(
                    Messages.get_msg(Messages.SELECT_VOLUME_DB))

            self.engine_volume_slider = self.getControlSlider(
                    clz.SELECT_VOLUME_SLIDER)

            self.engine_api_key_group = self.getControlGroup(
                    clz.SELECT_API_KEY_GROUP)
            # self.engine_api_key_label = self.getControlLabel(
            #    118
            # self.engine_api_key_label.setLabel(util.T(32233))

            self.engine_api_key_edit = self.getControlEdit(
                    clz.SELECT_API_KEY_EDIT)
            self.engine_api_key_edit.setLabel(
                    Messages.get_msg(Messages.API_KEY))

            self.options_group = self.getControlGroup(
                    clz.OPTIONS_GROUP)
            self.options_group.setVisible(True)

            self.options_dummy_button = self.getControlLabel(
                    clz.OPTIONS_DUMMY_BUTTON)
            self.options_dummy_button.setLabel('Options Trader')

            self.keymap_group = self.getControlGroup(
                    clz.KEYMAP_GROUP)
            self.keymap_group.setVisible(True)

            self.keymap_dummy_button = self.getControlLabel(
                    clz.KEYMAP_DUMMY_BUTTON)
            self.keymap_dummy_button.setLabel('KeyMap finder')

            self.advanced_group = self.getControlGroup(
                    clz.ADVANCED_GROUP)
            self.advanced_group.setVisible(True)

            self.advanced_dummy_button = self.getControlLabel(
                    clz.ADVANCED_DUMMY_BUTTON)
            self.advanced_dummy_button.setLabel('Advanced degree')
            self.update_engine_values()

            self._initialized = True
            self.settings_changed = False

    def getControlButton(self, iControlId: int) -> xbmcgui.ControlButton:
        buttonControl: xbmcgui.Control = super().getControl(iControlId)
        buttonControl: xbmcgui.ControlButton
        return buttonControl

    def getControlEdit(self, iControlId: int) -> xbmcgui.ControlEdit:
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlEdit
        return control

    def getControlGroup(self, iControlId: int) -> xbmcgui.ControlGroup:
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlGroup
        return control

    def getControlLabel(self, iControlId: int) -> xbmcgui.ControlLabel:
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlLabel
        return control

    def getControlRadioButton(self, iControlId: int) -> xbmcgui.ControlRadioButton:
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlRadioButton
        return control

    def getControlSlider(self, iControlId: int) -> xbmcgui.ControlSlider:
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlSlider
        return control

    def setRadioDimension(self):
        self.engine_tab.setRadioDimension(x=0, y=0, width=186, height=40)

    def update_engine_values(self):
        #
        # This assumes that changes to a setting does not impact a previous
        # setting.
        #
        # self.setEngineField()
        self.set_language_field()
        self.set_voice_field()
        self.set_gender_field()
        self.set_player_field()
        self.set_pitch_range()
        self.set_speed_range()
        self.set_volume_range()
        self.set_api_field()
        self.set_pipe_audio_field()
        self.set_cache_speech_field()
        self.settings_changed = False
        self.backend_changed = False

    def doModal(self) -> None:
        """

        :return:
        """
        self.show()
        super().doModal()
        return

    def show(self) -> None:
        """

        :return:
        """
        self._logger.debug_verbose('SettingsDialog.show')
        super().show()

    def close(self) -> None:
        """

        :return:
        """
        super().close()

    def getFocus(self) -> None:
        """

        :return:
        """
        pass

        super().getFocus()

    def onAction(self, action) -> None:
        """

        :param action:
        :return:
        """
        action_id = action.getId()
        if action_id == xbmcgui.ACTION_MOUSE_MOVE:
            return

        if self._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            action_mapper = Action.get_instance()
            matches = action_mapper.getKeyIDInfo(action)

            for line in matches:
                self._logger.debug_extra_verbose(line)

            button_code: int = action.getButtonCode()
            # These return empty string if not found
            action_key = action_mapper.getActionIDInfo(action)
            remote_button = action_mapper.getRemoteKeyButtonInfo(action)
            remote_key_id = action_mapper.getRemoteKeyIDInfo(action)

            # Returns found button_code, or 'key_' +  action_button
            action_button = action_mapper.getButtonCodeId(action)

            key_codes: List[str] = []

            if action_key != '':
                key_codes.append(action_key)
            if remote_button != '':
                key_codes.append(remote_button)
            if remote_key_id != '':
                key_codes.append(remote_key_id)
            if len(key_codes) == 0:
                key_codes.append(str(action_button))
            self._logger.debug_extra_verbose(
                    f'Key found: {",".join(key_codes)}')

        self._logger.debug_verbose(f'action_id: {action_id}')
        if (action_id == xbmcgui.ACTION_PREVIOUS_MENU
                or action_id == xbmcgui.ACTION_NAV_BACK):
            exit_dialog = True
            self.close()

    def onClick(self, controlId: int) -> None:
        self._logger.debug_verbose(
                'SettingsDialog.onClick id: {:d}'.format(controlId))
        focus_id = self.getFocusId()
        self._logger.debug_verbose('FocusId: ' + str(focus_id))
        if controlId == 100:
            self._logger.debug_verbose('Button 100 pressed')
            self.engine_tab.setSelected(True)
            # self.options_group.setVisible(False)
            # self.keymap_group.setVisible(False)
            # self.advanced_group.setVisible(False)
            # self.engine_group.setVisible(True)

        elif controlId == 200:
            self._logger.debug_verbose('Button 200 pressed')
            self.engine_tab.setSelected(False)
            # self.engine_group.setVisible(False)
            # self.keymap_group.setVisible(False)
            # self.advanced_group.setVisible(False)
            # self.options_group.setVisible(True)

        elif controlId == 300:
            self._logger.debug_verbose('Button 300 pressed')
            self.engine_tab.setSelected(False)
            # self.engine_group.setVisible(False)
            # self.options_group.setVisible(False)
            # self.advanced_group.setVisible(False)
            # self.keymap_group.setVisible(True)

        elif controlId == 400:
            self._logger.debug_verbose('Button 400 pressed')
            self.engine_tab.setSelected(False)
            # self.engine_group.setVisible(False)
            # self.options_group.setVisible(False)
            # self.keymap_group.setVisible(False)
            # self.advanced_group.setVisible(True)

        elif controlId in range(self.FIRST_SELECT_ID, self.LAST_SELECT_ID):
            self.handle_engine_tab(controlId)

        elif controlId == 28:
            # OK button
            self.save_settings()
            self.close()

        elif controlId == 29:
            # Cancel button
            self.discard_settings()
            self.close()

    def handle_engine_tab(self, controlId: int) -> None:
        '''

        :param controlId:
        :return:
        '''
        clz = type(self)
        if controlId == clz.SELECT_ENGINE_BUTTON:
            self.selectEngine()
        elif controlId == clz.SELECT_LANGUAGE_BUTTON:
            self.select_language()
        elif controlId == clz.SELECT_VOICE_BUTTON:
            self.select_voice()
        elif controlId == clz.SELECT_GENDER_BUTTON:
            self.select_gender()
        elif controlId == clz.SELECT_PITCH_SLIDER:
            self.select_pitch()
        elif controlId == clz.SELECT_PLAYER_BUTTON:
            self.select_player()
        elif controlId == clz.SELECT_CACHE_BUTTON:
            self.select_cache_speech()
        elif controlId == clz.SELECT_PIPE_BUTTON:
            self.select_pipe_audio()
        elif controlId == clz.SELECT_SPEED_SLIDER:
            self.select_speed()
        elif controlId == clz.SELECT_VOLUME_SLIDER:
            self.select_volume()
        elif controlId == clz.SELECT_API_KEY_EDIT:
            self.select_api_key()

        if self.backend_changed:
            self.update_engine_values()

    def setEngineField(self):
        choices, current_choice_index = self.getEngineChoices()
        backend_list_item: xbmcgui.ListItem = choices[current_choice_index]
        engine_id: str = backend_list_item.getLabel2()
        self.engine_engine_value.setLabel(backend_list_item.getLabel())
        if len(choices) < 2:
            self.engine_engine_value.setEnabled(False)
        else:
            self.engine_engine_value.setEnabled(True)

        self.set_engine_id(engine_id)

    def getEngineChoices(self) -> Tuple[List[xbmcgui.ListItem], int]:
        self._logger.debug_verbose('getEngineChoices')
        auto_choice_label = Messages.get_msg(Messages.AUTO)
        choices: List[xbmcgui.ListItem] = list()
        list_item = xbmcgui.ListItem(auto_choice_label)
        list_item.setLabel2(Settings.BACKEND_DEFAULT)
        choices.append(list_item)
        current_value = self.getSetting(
                Settings.BACKEND, Settings.BACKEND_DEFAULT)
        current_choice_index: int = 0
        for b in BackendInfo.getAvailableBackends():
            self._logger.debug_verbose(
                    f'Available Backend: {Settings.BACKEND} {b.displayName}')
            list_item = xbmcgui.ListItem(b.displayName)
            list_item.setLabel2(b.backend_id)
            choices.append(list_item)
            if b.backend_id == current_value:
                current_choice_index = len(choices) - 1

        return choices, current_choice_index

    def selectEngine(self):

        choices, current_choice_index = self.getEngineChoices()
        if current_choice_index < 0:
            current_choice_index = 0
        script_path = Constants.ADDON_PATH
        self._logger.debug_verbose(
                f'SettingsDialog ADDON_PATH: {Constants.ADDON_PATH}')
        selection_dialog = SelectionDialog('selection-dialog.xml',
                                           script_path, 'Default',
                                           title=Messages.get_msg(
                                                   Messages.SELECT_SPEECH_ENGINE),
                                           choices=choices,
                                           initial_choice=current_choice_index)

        selection_dialog.show()
        selection_dialog.doModal()
        idx = selection_dialog.getCurrentListPosition()
        self._logger.debug_verbose(f'SelectionDialog value: '
                                   f'{Messages.get_msg(Messages.CHOOSE_BACKEND)} '
                                   f'idx: {str(idx)}')
        if idx < 0:
            return None

        engine_list_item: ListItem = choices[idx]
        self._logger.debug_verbose(f'selectEngine value: {engine_list_item.getLabel()} idx: {str(idx)}')
        self.engine_engine_value.setLabel(engine_list_item.getLabel())
        new_engine = engine_list_item.getLabel2()

        # When engine changes, immediately switch to it since almost every
        # other setting will be impacted by the change.

        if new_engine != self.previous_engine:
            self.set_engine_id(new_engine)
            from service import TTSService
            TTSService.get_instance().initTTS(self.engine)
            # cmd ='XBMC.NotifyAll({},RELOAD_ENGINE)'.format(Constants.ADDON_ID)
            # xbmc.executebuiltin(cmd)

    def set_language_field(self):
        choices, current_choice_index = self.get_language_choices()
        if current_choice_index < 0:
            current_choice_index = 0

        if current_choice_index < 0 or current_choice_index > len(choices) - 1:
            self.setSetting(Settings.LANGUAGE, Settings.UNKNOWN_VALUE)
            self.engine_language_group.setVisible(False)
            self.engine_language_value.setEnabled(False)
            self.engine_language_value.setLabel(
                    Messages.get_msg(Messages.UNKNOWN))
            return
        else:
            self.engine_language_group.setVisible(True)

        language = choices[current_choice_index]
        self.engine_language_value.setLabel(language.getLabel())
        if len(choices) < 2:
            self.engine_language_value.setEnabled(False)
        else:
            self.engine_language_value.setEnabled(True)

        self.setSetting(Settings.LANGUAGE, language.getLabel2())

    def get_language_choices(self):
        current_value = self.getSetting(Settings.LANGUAGE, 'unknown')

        languages, default_setting = BackendInfo.getSettingsList(
                self.get_engine(), Settings.LANGUAGE)
        current_choice_index = -1

        choices = []
        if languages is None:
            languages = []

        languages = sorted(languages, key=lambda entry: entry[0])
        default_setting_index = -1
        for display_value, setting_value in languages:
            list_item = xbmcgui.ListItem(display_value)
            list_item.setLabel2(setting_value)
            list_item.setPath('')
            choices.append(list_item)
            if setting_value == current_value:
                current_choice_index = len(choices) - 1
            if setting_value == default_setting:
                default_setting_index = len(choices) - 1

        if current_choice_index == -1:
            current_choice_index = default_setting_index

        return choices, current_choice_index

    def select_language(self):
        choices, current_choice_index = self.get_language_choices()
        if len(choices) == 0:
            self.setSetting(Settings.LANGUAGE, Settings.UNKNOWN_VALUE)
            self.engine_language_group.setVisible(False)
            self.engine_language_value.setEnabled(False)
            self.engine_language_value.setLabel(
                    Messages.get_msg(Messages.UNKNOWN))
            return
        else:
            self.engine_language_group.setVisible(True)

        script_path = Constants.ADDON_PATH
        selection_dialog = SelectionDialog('selection-dialog.xml',
                                           script_path, 'Default',
                                           title=Messages.get_msg(
                                                   Messages.SELECT_LANGUAGE),
                                           choices=choices,
                                           initial_choice=current_choice_index)

        selection_dialog.show()
        self._logger.debug_verbose('SelectionDialog doModal start')
        selection_dialog.doModal()
        self._logger.debug_verbose('SelectionDialog doModal finished')
        idx = selection_dialog.getCurrentListPosition()
        self._logger.debug_verbose('SelectionDialog value:',
                                   Messages.get_msg(Messages.SELECT_LANGUAGE),
                                   'idx:', str(idx))
        if idx < 0:
            return

        language = choices[idx].getLabel()
        locale = choices[idx].getLabel2()
        self._logger.debug_verbose('select_language value: {} setting: {} idx: {:d}'
                                   .format(language, locale, idx))

        self.engine_language_value.setLabel(language)
        self.setSetting(Settings.LANGUAGE, locale)
        #  self.update_engine_values()

    def set_voice_field(self):
        choices, current_choice_index = self.get_voice_choices()
        if current_choice_index < 0:
            current_choice_index = 0

        if current_choice_index < 0 or current_choice_index > len(choices) - 1:
            self.setSetting(Settings.VOICE, 'unknown')
            self.engine_voice_value.setEnabled(False)
            self.engine_voice_value.setLabel(
                    Messages.get_msg(Messages.UNKNOWN))

            return

        voice = choices[current_choice_index]
        self.engine_voice_value.setLabel(voice.getLabel())
        if len(choices) < 2:
            self.engine_voice_value.setEnabled(False)
        else:
            self.engine_voice_value.setEnabled(True)

        self.setSetting(Settings.VOICE, voice.getLabel2())

    def get_voice_choices(self):
        current_value = self.getSetting(Settings.VOICE, 'unknown')
        current_choice_index = -1

        voices = BackendInfo.getSettingsList(
                self.get_engine(), Settings.VOICE)
        choices = []
        if voices is None:
            voices = []

        voices = sorted(voices, key=lambda entry: entry[0])

        for display_value, setting_value in voices:
            list_item = xbmcgui.ListItem(display_value)
            list_item.setLabel2(setting_value)
            list_item.setPath('')
            choices.append(list_item)
            if setting_value == current_value:
                current_choice_index = len(choices) - 1

        return choices, current_choice_index

    def select_voice(self):
        choices, current_choice_index = self.get_voice_choices()
        script_path = Constants.ADDON_PATH
        selection_dialog = SelectionDialog('selection-dialog.xml',
                                           script_path,
                                           'Default',
                                           title=Messages.get_msg(
                                                   Messages.SELECT_VOICE),
                                           choices=choices,
                                           initial_choice=current_choice_index)

        selection_dialog.show()
        selection_dialog.doModal()
        idx = selection_dialog.getCurrentListPosition()
        self._logger.debug_verbose(
                'SelectionDialog voice idx: {}'.format(str(idx)))
        if idx < 0:
            return

        voice = choices[idx].getLabel()
        voice_id = choices[idx].getLabel2()
        self._logger.debug_verbose('select_voice value: {} setting: {} idx: {:d}'
                                   .format(voice, voice_id, idx))

        self.engine_voice_value.setLabel(voice)
        self.setSetting(Settings.VOICE, voice_id)
        # self.update_engine_values()

    def set_gender_field(self):
        choices, current_choice_index = self.get_gender_choices()

        if current_choice_index < 0:
            current_choice_index = 0
        if current_choice_index < 0 or current_choice_index > len(choices) - 1:
            self.engine_gender_value.setEnabled(False)
            self.engine_gender_value.setLabel(
                    Messages.get_msg(Messages.UNKNOWN))

            return

        gender = choices[current_choice_index]
        self.engine_gender_value.setLabel(gender.getLabel())
        if len(choices) < 2:
            self.engine_gender_value.setEnabled(False)
            self.engine_gender_button.setEnabled(False)
        else:
            self.engine_gender_value.setEnabled(True)
            self.engine_gender_button.setEnabled(True)

    def get_gender_choices(self):
        current_value = self.get_gender()
        current_choice_index = -1

        # Fetch settings on every access because it can change

        engine = self.get_engine()
        supported_genders = BackendInfo.getSettingsList(engine, Settings.GENDER)
        if supported_genders is None:
            supported_genders = []
        choices = []
        for gender_id in supported_genders:
            display_value = Genders.get_label(gender_id)
            list_item = xbmcgui.ListItem(display_value)
            list_item.setLabel2(gender_id)
            list_item.setPath('')
            choices.append(list_item)
            if gender_id == current_value:
                current_choice_index = len(choices) - 1

        return choices, current_choice_index

    def select_gender(self):
        (choices, current_choice_index) = self.get_gender_choices()
        script_path = Constants.ADDON_PATH
        # xbmc.executebuiltin('Skin.ToggleDebug')

        selection_dialog = SelectionDialog('selection-dialog.xml',
                                           script_path, 'Default',
                                           title=Messages.get_msg(
                                                   Messages.SELECT_VOICE_GENDER),
                                           choices=choices,
                                           initial_choice=current_choice_index)

        selection_dialog.show()
        selection_dialog.doModal()
        idx = selection_dialog.getCurrentListPosition()
        if idx < 0:
            return

        gender_id = choices[idx]
        gender_label = Genders.get_label(gender_id)
        self._logger.debug_verbose('select_gender value: {} setting: {} idx: {:d}'
                                   .format(gender_label, gender_id, idx))

        self.engine_gender_value.setLabel(gender_label)
        self.setSetting(Settings.GENDER, gender_id)
        # self.update_engine_values()

    def get_player_choices(self):
        current_value = self.get_player()
        current_choice_index = -1

        supported_players, default_player = BackendInfo.getSettingsList(
                self.get_engine(), Settings.PLAYER)
        if supported_players is None:
            supported_players = []

        default_choice_index = -1
        choices = []
        for player_id in supported_players:
            player_label = Players.get_label(player_id)
            list_item = xbmcgui.ListItem(player_label)
            list_item.setLabel2(player_id)
            list_item.setPath('')
            choices.append(list_item)
            if player_id == current_value:
                current_choice_index = len(choices) - 1
            if player_id == default_player:
                default_choice_index = len(choices) - 1

        if current_choice_index < 0:
            current_choice_index = default_choice_index

        return choices, current_choice_index

    def select_player(self):
        (choices, current_choice_index) = self.get_player_choices()
        script_path = Constants.ADDON_PATH
        selection_dialog = SelectionDialog('selection-dialog.xml',
                                           script_path, 'Default',
                                           title=Messages.get_msg(
                                                   Messages.SELECT_VOICE_GENDER),
                                           choices=choices,
                                           initial_choice=current_choice_index)

        selection_dialog.show()
        selection_dialog.doModal()
        idx = selection_dialog.getCurrentListPosition()
        if idx < 0:
            return

        player_label = choices[idx].getLabel()
        player_id = choices[idx].getLabel2()
        self._logger.debug_verbose('select_player value: {} setting: {} idx: {:d}'
                                   .format(player_label, player_id, idx))

        self.engine_player_value.setLabel(player_label)
        self.set_player(player_id)
        # self.update_engine_values()

    def set_player_field(self):
        choices, current_choice_index = self.get_player_choices()
        if current_choice_index < 0:
            current_choice_index = 0
        if current_choice_index < 0 or current_choice_index > len(choices) - 1:
            self.engine_player_value.setEnabled(False)
            self.engine_player_value.setLabel(
                    Messages.get_msg(Messages.UNKNOWN))
            return

        player = choices[current_choice_index]
        player_label = player.getLabel()
        player_id = player.getLabel2()
        self.engine_player_value.setLabel(player_label)
        if len(choices) < 2:
            self.engine_player_value.setEnabled(False)
        else:
            self.engine_player_value.setEnabled(True)

        self.set_player(player_id)

    def select_volume(self):
        volume = self.engine_volume_slider.getInt()
        self.setSetting(Settings.VOLUME, volume)

    def set_volume_range(self):
        lower, upper, current = self.get_volume_range()
        if lower == upper:
            self.engine_volume_group.setVisible(False)
        else:
            increment = int((upper - lower + 19) / 20)
            self.engine_volume_slider.setInt(current, lower, increment, upper)
            self.engine_volume_group.setVisible(True)

    def get_volume_range(self):
        constraints = self.getEngineClass().get_volume_constraints()
        minimum = constraints[0]
        default = constraints[1]
        maximum = constraints[2]
        current_value = self.getSetting(Settings.VOLUME, default)
        if not isinstance(current_value, int):
            current_value = default
        elif current_value not in range(minimum, maximum):
            current_value = default

        return minimum, maximum, int(current_value)

    def select_pitch(self):
        pitch = self.engine_pitch_slider.getInt()
        self.setSetting(Settings.PITCH, pitch)

    def set_pitch_range(self):
        if not self.getEngineClass().isSettingSupported(Settings.PITCH):
            self.engine_pitch_group.setVisible(False)
        else:
            lower, upper, current = self.get_pitch_range()
            if lower == upper:
                self.engine_pitch_group.setVisible(False)
            else:
                increment = int(((upper - lower) + 19) / 20)
                self.engine_pitch_slider.setInt(
                        current, lower, increment, upper)
                self.engine_pitch_group.setVisible(True)

    def get_pitch_range(self):
        pitch_constraints = self.getEngineClass().get_pitch_constraints()
        minimum_pitch = pitch_constraints[0]
        default_pitch = pitch_constraints[1]
        maximum_pitch = pitch_constraints[2]
        current_value = self.getSetting(Settings.PITCH, default_pitch)
        if current_value < minimum_pitch or current_value > maximum_pitch:
            current_value = default_pitch

        return minimum_pitch, maximum_pitch, current_value

    def select_speed(self):
        speed = self.engine_speed_slider.getInt()
        self.setSetting(Settings.SPEED, speed)

    def set_speed_range(self):
        if self.getEngineClass().isSettingSupported(Settings.SPEED):
            lower, upper, current = self.get_speed_range()
            if lower == upper:
                self.engine_speed_group.setVisible(False)
            else:
                increment = int((upper - lower + 19) / 20)
                self.engine_speed_slider.setInt(
                        current, lower, increment, upper)
                self.engine_speed_group.setVisible(True)

    def get_speed_range(self):
        constraints = self.getEngineClass().get_speed_constraints()
        minimum = constraints[0]
        default_speed = constraints[1]
        maximum = constraints[2]
        current_value = self.getSetting(Settings.SPEED, default_speed)
        if not isinstance(current_value, int):
            current_value = default_speed
        elif current_value not in range(minimum, maximum):
            current_value = default_speed

        return minimum, maximum, current_value

    def select_cache_speech(self):
        if self.getEngineClass().isSettingSupported(Settings.CACHE_SPEECH):
            self.engine_cache_speech_group.setVisible(True)
            cache_speech = self.engine_cache_speech_radio_button.isSelected()
            self.setSetting(Settings.CACHE_SPEECH, cache_speech)
            # self.update_engine_values()
        else:
            self.engine_cache_speech_group.setVisible(False)

    def set_cache_speech_field(self):
        if self.getEngineClass().isSettingSupported(Settings.CACHE_SPEECH):
            cache_speech = bool(self.getSetting(Settings.CACHE_SPEECH))
            self.engine_cache_speech_group.setVisible(True)
            self.engine_cache_speech_radio_button.setVisible(True)
            self.engine_cache_speech_radio_button.setSelected(cache_speech)
        else:
            self.engine_cache_speech_group.setVisible(False)

    def select_pipe_audio(self):
        if self.getEngineClass().isSettingSupported(Settings.PIPE):
            self.engine_pipe_audio_group.setVisible(True)
            use_pipe = self.engine_pipe_audio_radio_button.isSelected()
            self.setSetting(Settings.PIPE, use_pipe)
            # self.update_engine_values()
        else:
            self.engine_pipe_audio_group.setVisible(False)

    def set_pipe_audio_field(self):
        if self.getEngineClass().isSettingSupported(Settings.PIPE):
            use_pipe = bool(self.getSetting(Settings.PIPE))
            self.engine_pipe_audio_radio_button.setVisible(True)
            self.engine_pipe_audio_radio_button.setSelected(use_pipe)
        else:
            self.engine_pipe_audio_radio_button.setSelected(False)

    def select_api_key(self):
        api_key = self.engine_api_key_edit.getText()
        self.setSetting(Settings.API_KEY, api_key)

    def set_api_field(self):
        if self.getEngineClass().isSettingSupported(Settings.API_KEY):
            self.engine_api_key_group.setVisible(True)
            api_key = self.getSetting(Settings.API_KEY, '')
            self.engine_api_key_edit.setText(api_key)
            self.engine_api_key_edit.setLabel(
                    Messages.get_msg(Messages.ENTER_API_KEY))
        else:
            self.engine_api_key_group.setVisible(False)

    # ="output_via_espeak.eSpeak" l
    # ="player.eSpeak Same as above player. Visible if output_via_espeak is  not selected
    # pipe only visible if output_via_espeak is not selected
    #
    # ttsd backend
    #  perl_server.ttsd bool
    #  speakon_server.ttsd  bool
    #  engine.ttsd <- list ttsd, engine
    #
    # voice.Flite.ttsd (espeak, sapi, cepstral, osxsay, festival,
    #
    # remote_speed.ttsd, pitch, volume,
    #
    # player_handler--
    # pipe.ttsd enabled if speak_on_server.ttsd & ttsd backend
    # player_seed.ttsd if player_handler.ttsd is sox, mplayer, afplay
    # player_volume.ttsd enabled if player_handler.ttsd sox, mplayer, paplay,afplay
    #
    #
    #
    def get_engine(self, init: bool = False) -> str:
        # Deliberately using Settings.getSetting here
        if self.engine is None or self.settings_changed:
            self.engine = Settings.getSetting(Settings.BACKEND, None,
                                              Settings.BACKEND_DEFAULT)

        if (self.engine == Settings.BACKEND_DEFAULT
            or not BackendInfo.isValidBackend(self.engine)):
            self.engine = BackendInfo.getAvailableBackends()[0].backend_id
            self.set_engine_id(self.engine)

        if init:
            self.previous_engine = self.engine
        return self.engine

    def get_language(self):
        if self.settings_changed:
            self.language = self.getSetting(Settings.LANGUAGE,
                                            Settings.LANGUAGE_DEFAULT)

        return self.language

    def get_gender(self):
        if self.settings_changed:
            gender_default: str = self.getSetting(Settings.GENDER)
            self.gender = self.getSetting(Settings.GENDER,
                                          gender_default)
        return self.gender

    def get_pitch(self):
        if self.settings_changed:
            pitch_default = self.getSetting(Settings.PITCH)
            self.pitch = self.getSetting(Settings.PITCH,
                                         pitch_default)
        return self.pitch

    def get_player(self):
        if self.settings_changed:
            player_default = self.getSetting(Settings.PLAYER)
            self.player = self.getSetting(Settings.PLAYER,
                                          player_default)
        return self.player

    def set_player(self, player_id):
        self.player = player_id
        self.setSetting(Settings.PLAYER, player_id)
        self.getEngineInstance().setPlayer(preferred=player_id)

    def get_speed(self):
        if self.settings_changed:
            speed_default = self.getSetting(Settings.SPEED)
            self.speed = self.getSetting(Settings.SPEED,
                                         speed_default)
        return self.speed

    def get_volume(self) -> int:
        if self.settings_changed:
            volume_default = self.getSetting(Settings.VOLUME)
            volume_str = self.getSetting(Settings.VOLUME,
                                         volume_default)
            try:
                volume_int: int = int(volume_str)
            except:
                volume_int = 0
            self.volume = volume_int
        return self.volume

    def get_api_key(self) -> str:
        if self.settings_changed:
            self.api_key: str = self.getSetting(Settings.API_KEY,
                                                Settings.API_KEY_DEFAULT)
        return self.api_key

    # def get_pipe_audio(self):
    #    pipe_default = self.getSetting(Settings.PIPE)
    #    engine_pipe_audio = self.getSetting(Settings.PIPE,
    #                                                            pipe_default)  # type:
    #                                                            bool
    #    cmd = 'Skin.String(engine_pipe_audio,{:b})'.format(engine_pipe_audio)
    #    xbmc.executebuiltin(cmd)
    #    return engine_pipe_audio

    def set_engine_id(self, engine_id):
        if self.previous_engine != engine_id:
            engine_instance: ITTSBackendBase = self.getEngineClass(engine_id=engine_id)

            # Throw away all changes and switch to the current
            # settings for a new backend.

            self.engine_instance = None
            self.engine = engine_id
            if self.previous_engine is not None: # first time don't count
                self.backend_changed = True

            self.previous_engine = engine_id
            self.settings_changed = True

    def getEngineClass(self, engine_id=None) -> ITTSBackendBase:
        if engine_id is None:
            engine_id = self.engine
        if engine_id != self.engine:
            if self.engine_class is None or self.engine_class.backend_id != engine_id:
                self.engine_class = BackendInfo.getBackendByProvider(engine_id)
        return self.engine_class

    def getEngineInstance(self) -> ITTSBackendBase:
        if self.engine_instance is None or self.engine_instance.backend_id != \
                self.engine:
            self.engine_instance:ITTSBackendBase = self.getEngineClass()

        return self.engine_instance

    def getSetting(self, setting_id, default=None):
        if default is None:
            default = self.getEngineClass().get_setting_default(setting_id)
        value = self.getEngineClass().getSetting(setting_id, default)
        if value is None:
            value = default
        return value

    def setSetting(self, key: str, value: Any) -> None:
        changed: bool = Settings.setSetting(key, value, self.engine)
        # changed = self.getEngineClass().setSetting(key, value)
        if changed:
            self.settings_changed = True

    def save_settings(self):
        Settings.commit_settings()
        #  TTSService.get_instance().checkBackend()

    def discard_settings(self):
        Settings.cancel_changes()
