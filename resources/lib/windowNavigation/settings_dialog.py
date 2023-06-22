# -*- coding: utf-8 -*-

import xbmcaddon
import xbmcgui
from xbmcgui import (ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider, ListItem)

from backends.backend_info import BackendInfo
from backends.base import *
from backends.settings.settings_map import SettingsMap
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.setting_constants import Backends, Genders, Players
from common.settings import Settings
from common.typing import *
from utils.util import get_language_code
from windowNavigation.action_map import Action
from windowNavigation.selection_dialog import SelectionDialog

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
        self.closing = False
        self._initialized: bool = False
        self.exit_dialog: bool = False
        super().__init__(*args)
        self.api_key = None
        self.engine_id: str | None= None
        self.engine_instance: ITTSBackendBase | None = None
        self.backend_changed: bool = False
        self.gender_id: int | None = None
        self.language: str | None = None
        self.pitch: float | None = None
        self.player: str | None = None
        self.module: str | None = None
        self.speed: float | None = None
        self.volume: int | None = None
        self.settings_changed: bool = False
        self.previous_engine: str | None = None
        initial_backend = Settings.getSetting(SettingsProperties.ENGINE, self.engine_id,
                                              SettingsProperties.ENGINE_DEFAULT)

        if initial_backend == SettingsProperties.ENGINE_DEFAULT:  # 'auto'
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
        self.engine_player_value = None  # player and module
        self.engine_module_value = None  # share button and real-estate
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
        try:
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
                engine_label: str = Backends.get_label(self.get_engine_id(init=True))
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

                self.engine_gender_value: ControlLabel = self.getControlLabel(
                        clz.SELECT_GENDER_VALUE_LABEL)
                try:
                    gender: Genders = Settings.get_gender(self.engine_id)
                    self.engine_gender_value.setLabel(gender.name)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    self._logger.exception('')

                self.engine_pitch_group = self.getControlGroup(
                        clz.SELECT_PITCH_GROUP)
                self.engine_pitch_label = self.getControlLabel(
                        clz.SELECT_PITCH_LABEL)
                self.engine_pitch_label.setLabel(
                        Messages.get_msg(Messages.SELECT_PITCH))

                self.engine_pitch_slider = self.getControlSlider(
                        clz.SELECT_PITCH_SLIDER)

                # NOTE: player and module share control. Only one active at a
                #       time. Probably should create two distinct buttons and
                #       control visibility

                self.engine_player_button = self.getControlLabel(
                        clz.SELECT_PLAYER_BUTTON)
                if BaseServices.is_valid_property(self.engine_id, SettingsProperties.PLAYER):
                    self.engine_player_button.setLabel(
                            Messages.get_msg(Messages.SELECT_PLAYER))
                    self.engine_player_value = self.getControlButton(
                            clz.SELECT_PLAYER_VALUE)
                    self.engine_player_value.setLabel(self.get_player())
                else:
                    self.engine_player_button.setLabel(
                            Messages.get_msg(Messages.SELECT_MODULE))
                    self.engine_module_value = self.getControlButton(
                            clz.SELECT_PLAYER_VALUE)
                    self.engine_module_value.setLabel(self.get_module())

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
        except Exception as e:
            self._logger.exception('')

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
        try:
            # self.setEngineField()
            self.set_language_field()
            self.set_voice_field()
            self.set_gender_field()
            if BaseServices.is_valid_property(self.engine_id, SettingsProperties.PLAYER):
                self.set_player_field()
            elif BaseServices.is_valid_property(self.engine_id, SettingsProperties.MODULE):
                self.set_module_field()
            self.set_pitch_range()
            self.set_speed_range()
            self.set_volume_range()
            self.set_api_field()
            self.set_pipe_audio_field()
            self.set_cache_speech_field()
            self.settings_changed = False
            self.backend_changed = False
            # TTSService.onSettingsChanged()
        except Exception as e:
            self._logger.exception()

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
        if self.closing:
            return

        try:
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
        except Exception as e:
            self._logger.exception()

    def onClick(self, controlId: int) -> None:
        if self.closing:
            return

        try:
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
                self.closing = True
                self.save_settings()
                self._logger.info(f'closing')
                self.close()

            elif controlId == 29:
                # Cancel button
                self.closing = True
                self.discard_settings()
                self.close()

        except Exception as e:
            self._logger.exception('')

    def handle_engine_tab(self, controlId: int) -> None:
        """

        :param controlId:
        :return:
        """
        clz = type(self)
        try:
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
                if SettingsMap.is_valid_property(self.engine_id, SettingsProperties.PLAYER):
                    self.select_player()
                else:
                    self.select_module()
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
        except Exception as e:
            self._logger.exception('')

    def setEngineField(self):
        try:
            choices, current_choice_index = self.getEngineChoices()
            backend_list_item: xbmcgui.ListItem = choices[current_choice_index]
            engine_id: str = backend_list_item.getLabel2()
            self.engine_engine_value.setLabel(backend_list_item.getLabel())
            if len(choices) < 2:
                self.engine_engine_value.setEnabled(False)
            else:
                self.engine_engine_value.setEnabled(True)

            self.set_engine_id(engine_id)
        except Exception as e:
            self._logger.exception('')

    def getEngineChoices(self) -> Tuple[List[xbmcgui.ListItem], int]:
        try:
            self._logger.debug_verbose('getEngineChoices')
            auto_choice_label = Messages.get_msg(Messages.AUTO)
            choices: List[xbmcgui.ListItem] = list()
            list_item = xbmcgui.ListItem(auto_choice_label)
            list_item.setLabel2(SettingsProperties.ENGINE_DEFAULT)
            choices.append(list_item)
            current_value = self.getSetting(
                    SettingsProperties.ENGINE, SettingsProperties.ENGINE_DEFAULT)
            current_choice_index: int = 0
            for b in BackendInfo.getAvailableBackends():
                self._logger.debug(
                        f'Available Backend: {SettingsProperties.ENGINE} {b.displayName}')
                list_item = xbmcgui.ListItem(b.displayName)
                list_item.setLabel2(b.backend_id)
                choices.append(list_item)
                if b.backend_id == current_value:
                    current_choice_index = len(choices) - 1

            return choices, current_choice_index
        except Exception as e:
            self._logger.exception('')

    def selectEngine(self):
        try:
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
                from service_worker import TTSService
                TTSService.get_instance().initTTS(self.engine_id)
                # cmd ='XBMC.NotifyAll({},RELOAD_ENGINE)'.format(Constants.ADDON_ID)
                # xbmc.executebuiltin(cmd)
        except Exception as e:
            self._logger.exception('')

    def set_language_field(self):
        try:
            choices, current_choice_index = self.get_language_choices()
            if current_choice_index < 0:
                current_choice_index = 0

            if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                self.setSetting(SettingsProperties.LANGUAGE, SettingsProperties.UNKNOWN_VALUE)
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

            self.setSetting(SettingsProperties.LANGUAGE, language.getLabel2())
        except Exception as e:
            self._logger.exception('')

    def get_language_choices(self) -> Tuple[List[xbmcgui.ListItem], int]:
        choices: List[xbmcgui.ListItem] = []
        current_choice_index: int = -1
        try:
            current_value = self.getSetting(SettingsProperties.LANGUAGE, 'unknown')

            languages, default_setting = self.getEngineInstance().settingList(
                    SettingsProperties.LANGUAGE)

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

        except Exception as e:
            self._logger.exception('')

        return choices, current_choice_index

    def select_language(self):
        try:
            choices, current_choice_index = self.get_language_choices()
            if len(choices) == 0:
                self.setSetting(SettingsProperties.LANGUAGE, SettingsProperties.UNKNOWN_VALUE)
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
            self.setSetting(SettingsProperties.LANGUAGE, locale)
            #  self.update_engine_values()
        except Exception as e:
            self._logger.exception('')

    def set_voice_field(self):
        try:
            choices, current_choice_index = self.get_voice_choices()
            if current_choice_index < 0:
                current_choice_index = 0

            if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                self.setSetting(SettingsProperties.VOICE, 'unknown')
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

            self.setSetting(SettingsProperties.VOICE, voice.getLabel2())
        except Exception as e:
            self._logger.exception('')

    def get_voice_choices(self) -> Tuple[List[xbmcgui.ListItem], int]:
        choices: List[xbmcgui.ListItem] = []
        current_choice_index: int = -1
        try:
            current_value: str = self.getSetting(SettingsProperties.VOICE, 'unknown')
            voices = BackendInfo.getSettingsList(
                    self.get_engine_id(), SettingsProperties.VOICE)
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
        except Exception as e:
            self._logger.exception('')

        return choices, current_choice_index

    def select_voice(self):
        try:
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
            self.setSetting(SettingsProperties.VOICE, voice_id)
            # self.update_engine_values()
        except Exception as e:
            self._logger.exception('')

    def set_gender_field(self):
        try:
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
        except Exception as e:
            self._logger.exception('')

    def get_gender_choices(self) -> Tuple[List[ListItem], int]:
        current_value: Genders = Settings.get_gender(self.engine_id)
        current_choice_index = -1
        choices: List[ListItem] = []
        try:
            # Fetch settings on every access because it can change

            engine = self.get_engine_id()
            supported_genders = BackendInfo.getSettingsList(engine, SettingsProperties.GENDER)
            if supported_genders is None:
                supported_genders = []
            for gender_id in supported_genders:
                gender_id: str
                display_value = Genders.get_label(gender_id)
                list_item = xbmcgui.ListItem(display_value)
                list_item.setLabel2(str(gender_id))
                list_item.setPath('')
                choices.append(list_item)
                if gender_id == current_value:
                    current_choice_index = len(choices) - 1
        except Exception as e:
            self._logger.exception('')

        return choices, current_choice_index

    def select_gender(self):
        try:
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

            gender_li: ListItem = choices[idx]
            gender_id: int = int(gender_li.getLabel2())
            gender_label = Genders.get_label(gender_id)
            self._logger.debug_verbose(f'select_gender value: {gender_label} '
                                       f'setting: {gender_id} idx: {idx:d}')
            self.engine_gender_value.setLabel(gender_label)
            self.setSetting(SettingsProperties.GENDER, gender_id)
            # self.update_engine_values()
        except Exception as e:
            self._logger.exception('')

    def get_player_choices(self) -> Tuple[List[xbmcgui.ListItem], int]:
        choices: List[xbmcgui.ListItem] = []
        current_choice_index = -1
        try:
            engine_output_formats = SoundCapabilities.get_output_formats(self.get_engine_id())
            current_value = self.get_player()
            candidates: List[str]
            candidates = SoundCapabilities.get_capable_services(ServiceType.PLAYER,
                                                                engine_output_formats,
                                                                [])
            if not BaseServices.is_valid_property(self.engine_id, SettingsProperties.PLAYER):
                return [], -1

            supported_players: List[str]
            supported_players = SettingsMap.get_allowed_values(self.engine_id,
                                                               SettingsProperties.PLAYER)
            default_player: str
            default_player = SettingsMap.get_default_value(self.engine_id,
                                                           SettingsProperties.PLAYER)
            if supported_players is None:
                supported_players = [default_player]

            default_choice_index = -1
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
        except Exception as e:
            self._logger.exception('')

        return choices, current_choice_index

    def select_player(self):
        try:
            (choices, current_choice_index) = self.get_player_choices()
            script_path = Constants.ADDON_PATH
            selection_dialog = SelectionDialog('selection-dialog.xml',
                                               script_path, 'Default',
                                               title=Messages.get_msg(
                                                       Messages.SELECT_PLAYER),
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
        except Exception as e:
            self._logger.exception('')

    def set_player_field(self):
        try:
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
        except Exception as e:
            self._logger.exception('')

    def set_module_field(self):
        try:
            choices, current_choice_index = self.get_module_choices()
            if current_choice_index < 0:
                current_choice_index = 0
            if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                self.engine_module_value.setEnabled(False)
                self.engine_module_value.setLabel(
                        Messages.get_msg(Messages.UNKNOWN))
                return

            player = choices[current_choice_index]
            player_label = player.getLabel()
            module_id = player.getLabel2()
            self.engine_module_value.setLabel(player_label)
            if len(choices) < 2:
                self.engine_module_value.setEnabled(False)
            else:
                self.engine_module_value.setEnabled(True)

            self.set_module(module_id)
        except Exception as e:
            self._logger.exception('')

    def get_module_choices(self) -> Tuple[List[xbmcgui.ListItem], int]:
        choices: List[xbmcgui.ListItem] = []
        current_choice_index: int = -1
        try:
            current_value = self.get_module()
            if not SettingsMap.is_valid_property(self.engine_id, SettingsProperties.MODULE):
                return ([], -1)

            supported_modules: List[Tuple[str, str]]
            default_module: str
            supported_modules, default_module = BackendInfo.getSettingsList(
                    self.get_engine_id(), SettingsProperties.MODULE)
            if supported_modules is None:
                supported_modules = []

            default_choice_index = -1
            for module_name, module_id in supported_modules:
                module_label = module_name  # TODO: Fix
                list_item = xbmcgui.ListItem(module_label)
                list_item.setLabel2(module_id)
                list_item.setPath('')
                choices.append(list_item)
                if module_id == current_value:
                    current_choice_index = len(choices) - 1
                if module_id == default_module:
                    default_choice_index = len(choices) - 1

            if current_choice_index < 0:
                current_choice_index = default_choice_index
        except Exception as e:
            self._logger.exception('')
        return choices, current_choice_index

    def select_module(self):
        try:
            (choices, current_choice_index) = self.get_module_choices()
            script_path = Constants.ADDON_PATH
            selection_dialog = SelectionDialog('selection-dialog.xml',
                                               script_path, 'Default',
                                               title=Messages.get_msg(
                                                       Messages.SELECT_MODULE),
                                               choices=choices,
                                               initial_choice=current_choice_index)

            selection_dialog.show()
            selection_dialog.doModal()
            idx = selection_dialog.getCurrentListPosition()
            if idx < 0:
                return

            module_label = choices[idx].getLabel()
            module_id = choices[idx].getLabel2()
            self._logger.debug_verbose('value: {} setting: {} idx: {:d}'
                                       .format(module_label, module_id, idx))

            self.engine_module_value.setLabel(module_label)
            self.set_module(module_id)
            # self.update_engine_values()
        except Exception as e:
            self._logger.exception('')

    def select_volume(self) -> None:
        try:
            volume = self.engine_volume_slider.getInt()
            constraints: Constraints = self.getEngineClass().get_constraints(SettingsProperties.VOLUME)
            constraints.setSetting(volume, self.engine_id)
        except Exception as e:
            self._logger.exception('')

    def set_volume_range(self):
        try:
            lower, upper, current = self.get_volume_range()
            if lower == upper:
                self.engine_volume_group.setVisible(False)
            else:
                increment = int((upper - lower + 19) / 20)
                self.engine_volume_slider.setInt(current, lower, increment, upper)
                self.engine_volume_group.setVisible(True)
        except Exception as e:
            self._logger.exception('')

    def get_volume_range(self) -> Tuple[int, int, int]:
        minimum_volume: int = 0
        maximum_volume: int = 0
        current_volume: int = 0
        try:
            volume_constraints: Constraints = self.getEngineClass().get_constraints(
                    SettingsProperties.VOLUME)
            if volume_constraints is None:
                raise NotImplementedError
            minimum_volume = int(volume_constraints.minimum)
            default_volume = int(volume_constraints.default)
            maximum_volume = int(volume_constraints.maximum)
            current_volume = self.getSetting(SettingsProperties.VOLUME, default_volume)
            if not volume_constraints.in_range(current_volume):
                current_volume = default_volume
            current_volume = int(current_volume)
        except NotImplementedError:
            pass
        except Exception as e:
            self._logger.exception('')

        return minimum_volume, maximum_volume, current_volume

    def select_pitch(self):
        try:
            pitch = self.engine_pitch_slider.getInt()
            constraints: Constraints = self.getEngineClass().get_constraints(SettingsProperties.PITCH)
            constraints.setSetting(pitch, self.engine_id)
        except Exception as e:
            self._logger.exception('')

    def set_pitch_range(self):
        try:
            if not SettingsMap.is_valid_property(self.engine_id, SettingsProperties.PITCH):
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
        except Exception as e:
            self._logger.exception('')

    def get_pitch_range(self) -> Tuple[int, int, int]:
        try:
            pitch_constraints: Constraints = self.getEngineClass().get_constraints(
                    SettingsProperties.PITCH)
            if pitch_constraints is None:
                raise NotImplementedError
            minimum_pitch: int = int(pitch_constraints.minimum)
            default_pitch: int = int(pitch_constraints.default)
            maximum_pitch: int = int(pitch_constraints.maximum)
            current_value = self.getSetting(SettingsProperties.PITCH, default_pitch)
            if not pitch_constraints.in_range(current_value):
                current_value = default_pitch
            current_value = int(current_value)
        except NotImplementedError:
            return 0, 0, 0

        return minimum_pitch, maximum_pitch, current_value

    def select_speed(self):
        try:
            speed: float = self.engine_speed_slider.getFloat()
            constraints: Constraints = self.getEngineClass().get_constraints(SettingsProperties.SPEED)
            constraints.setSetting(speed, self.engine_id)
        except Exception as e:
            self._logger.exception('')

    def set_speed_range(self):
        try:
            if not SettingsMap.is_valid_property(self.engine_id, SettingsProperties.SPEED):
                lower, upper, current, increment = self.get_speed_range()
                scale: float = 1.0
                if increment > 0.0:
                    scale = 1.0 / increment
                if int(lower * scale) == int(upper * scale):
                    self.engine_speed_group.setVisible(False)
                    return

                self.engine_speed_slider.setFloat(
                        current, lower, increment, upper)
                self.engine_speed_group.setVisible(True)
        except Exception as e:
            self._logger.exception('')

    def get_speed_range(self) -> Tuple[float, float, float, float]:
        try:
            constraints: Constraints = self.getEngineClass().get_constraints(SettingsProperties.SPEED)
            if constraints is None:
                raise NotImplementedError
            minimum: float = constraints.minimum
            default_speed: float = constraints.default
            maximum: float = constraints.maximum
            current_value: float = self.getSetting(SettingsProperties.SPEED, default_speed)
            if not constraints.in_range(current_value):
                current_value = default_speed

            return minimum, maximum, current_value, constraints.increment
        except NotImplementedError:
            return 1, 1, 1, 1

    def select_cache_speech(self):
        try:
            Settings.is_use_cache(self.engine_id)
            self.engine_cache_speech_group.setVisible(True)
            cache_speech = self.engine_cache_speech_radio_button.isSelected()
            self.setSetting(SettingsProperties.CACHE_SPEECH, cache_speech)
            # self.update_engine_values()
        except NotImplementedError:
                self.engine_cache_speech_group.setVisible(False)
        except Exception as e:
            self._logger.exception('')

    def set_cache_speech_field(self):
        try:
            use_cache: bool = Settings.is_use_cache(self.engine_id)
            self.engine_cache_speech_radio_button.setSelected(use_cache)
            self.engine_cache_speech_group.setVisible(True)
            self.engine_cache_speech_radio_button.setVisible(True)
        except NotImplementedError:
            self.engine_cache_speech_group.setVisible(False)
        except Exception as e:
            self._logger.exception('')

    def select_pipe_audio(self):
        try:
            if SettingsMap.is_valid_property(self.engine_id, SettingsProperties.PIPE):
                self.engine_pipe_audio_group.setVisible(True)
                use_pipe = self.engine_pipe_audio_radio_button.isSelected()
                self.setSetting(SettingsProperties.PIPE, use_pipe)
                # self.update_engine_values()
            else:
                self.engine_pipe_audio_group.setVisible(False)
        except Exception as e:
            self._logger.exception('')

    def set_pipe_audio_field(self):
        try:
            use_pipe: bool = Settings.get_pipe(self.engine_id)
            self.engine_pipe_audio_radio_button.setSelected(use_pipe)
            self.engine_pipe_audio_radio_button.setVisible(True)
        except NotImplementedError:
            self.engine_pipe_audio_radio_button.setSelected(False)
        except Exception as e:
            self._logger.exception('')

    def select_api_key(self):
        try:
            api_key = self.engine_api_key_edit.getText()
            self.setSetting(SettingsProperties.API_KEY, api_key)
        except Exception as e:
            self._logger.exception('')

    def set_api_field(self):
        try:
            if SettingsMap.get_validator(self.engine_id,
                                         property_id=SettingsProperties.API_KEY) is not None:
                api_key: str = Settings.get_api_key(self.engine_id)
                self.engine_api_key_edit.setText(api_key)
                self.engine_api_key_edit.setLabel(
                        Messages.get_msg(Messages.ENTER_API_KEY))
                self.engine_api_key_group.setVisible(True)
            else:
                self.engine_api_key_group.setVisible(False)
        except Exception as e:
            self._logger.exception('')

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
    def get_engine_id(self, init: bool = False) -> str:
        # Deliberately using Settings.getSetting here
        if self.engine_id is None or self.settings_changed:
            self.engine_id = Settings.getSetting(SettingsProperties.ENGINE, None,
                                                 SettingsProperties.ENGINE_DEFAULT)

        if (self.engine_id == SettingsProperties.ENGINE_DEFAULT
                or not BackendInfo.isValidBackend(self.engine_id)):
            self.engine_id = BackendInfo.getAvailableBackends()[0].backend_id
            self.set_engine_id(self.engine_id)
        if init:
            self.previous_engine = self.engine_id
        return self.engine_id

    def get_language(self):
        clz = type(self)
        try:
            if self.settings_changed:
                self.language = Settings.get_language(self.engine_id)
            if self.language is None:
                _, default_setting = self.getEngineInstance().settingList(
                    SettingsProperties.LANGUAGE)
                self.language = default_setting
        except Exception as e:
            self._logger.exception('')
            self.language = get_language_code()
        return self.language

    '''
    def get_gender_id(self) -> int:
        gender_default: int = Genders.UNKNOWN
        self.gender_id = Settings.get_gender(self.engine_id)
        if self.settings_changed:
            self.gender_id = self.getSetting(SettingsProperties.GENDER,
                                             gender_default)
        return self.gender_id
    '''

    def get_pitch(self):
        try:
            if self.settings_changed:
                pitch: float = Settings.get_pitch(self.engine_id)
                self.pitch = pitch
        except Exception as e:
            self._logger.exception('')
        return self.pitch

    def get_player(self):
        try:
            player: str | None = self.get_player_setting()
            if player is None:
                player = SettingsMap.get_default_value(self.engine_id,
                                                       SettingsProperties.PLAYER)
            self.player = player
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            self._logger.exception('')

        return self.player

    def set_player(self, player_id):
        try:
            self.player = player_id
            self.setSetting(SettingsProperties.PLAYER, player_id)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            self._logger.exception('')

    def get_module(self):
        try:
            module: str | None = self.get_module_setting()
            if module is None:
                engine: ITTSBackendBase = BackendInfo.getBackend(self.engine_id)
                module = engine.get_setting_default(SettingsProperties.PLAYER)
            self.module = module
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            self._logger.exception('')
        return self.module

    def set_module(self, module_id):
        self.module = module_id
        self.setSetting(SettingsProperties.MODULE, module_id)
        #  self.getEngineInstance().setPlayer(preferred=player_id)

    def get_speed(self):
        if self.settings_changed:
            Settings.getSpeed(self.engine_id)

        return self.speed

    def get_volume(self) -> int:
        if self.settings_changed:
            volume = Settings.get_volume(self.engine_id)
            self.volume = volume
        return self.volume

    def get_api_key(self) -> str:
        if self.settings_changed:
            self.api_key: str = Settings.get_api_key(self.engine_id)
        return self.api_key

    # def get_pipe_audio(self):
    #    pipe_default = self.getSetting(SettingsProperties.PIPE)
    #    engine_pipe_audio = self.getSetting(SettingsProperties.PIPE,
    #                                                            pipe_default)  # type:
    #                                                            bool
    #    cmd = 'Skin.String(engine_pipe_audio,{:b})'.format(engine_pipe_audio)
    #    xbmc.executebuiltin(cmd)
    #    return engine_pipe_audio

    def set_engine_id(self, engine_id):
        try:
            if self.previous_engine != engine_id:
                self.engine_instance: ITTSBackendBase = self.getEngineClass(engine_id=engine_id)

                # Throw away all changes and switch to the current
                # settings for a new backend.

                self.engine_id = engine_id
                if self.previous_engine is not None: # first time don't count
                    self.backend_changed = True

                self.previous_engine = engine_id
                self.settings_changed = True
        except Exception as e:
            self._logger.exception('')

    def getEngineClass(self, engine_id=None) -> ITTSBackendBase:
        if engine_id is None:
            engine_id = self.engine_id
        if self.engine_instance is None or self.engine_instance.backend_id != engine_id:
            self.engine_instance = BaseServices.getService(engine_id)
        return self.engine_instance

    def getEngineInstance(self) -> ITTSBackendBase:
        if self.engine_instance is None or self.engine_instance.backend_id != \
                self.engine_id:
            self.engine_instance:ITTSBackendBase = self.getEngineClass()

        return self.engine_instance

    def getSetting(self, setting_id, default=None):
        engine: ITTSBackendBase = self.getEngineClass(self.engine_id)
        value = None
        try:
            if default is None:
                default = engine.get_setting_default(setting_id)
            value = engine.getSetting(setting_id, default)
        except AttributeError:
            value = None
        return value

    def setSetting(self, key: str, value: Any) -> None:
        try:
            #  engine: ITTSBackendBase = self.getEngineClass(self.engine_id)
            changed: bool = Settings.setSetting(key, value, self.engine_id)

            # changed = self.getEngineClass().setSetting(key, value)
            if changed:
                self.settings_changed = True
        except Exception as e:
            self._logger.exception('')

    def get_player_setting(self, default: str | None = None):
        player: str = Settings.get_player_id(self.engine_id)
        if player is None:
            default: str = SettingsMap.get_default_value(self.engine_id,
                                               SettingsProperties.PLAYER)
            player = default
        return player

    def get_module_setting(self, default: str | None = None):
        engine: ITTSBackendBase = self.getEngineClass(self.engine_id)
        if default is None:
            default = engine.get_setting_default(SettingsProperties.MODULE)
        value = engine.getSetting(SettingsProperties.MODULE, default)
        return value

    def save_settings(self) -> None:
        Settings.commit_settings()
        self._logger.info(f'Settings saved/committed')
        #  TTSService.get_instance().checkBackend()

    def discard_settings(self) -> None:
        try:
            Settings.cancel_changes()
        except Exception as e:
            self._logger.exception('')
