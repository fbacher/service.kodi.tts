# -*- coding: utf-8 -*-

from typing import List, Any, Union, Type

import xbmc
import xbmcgui
import xbmcaddon

from windowNavigation.action_map import Action
from windowNavigation.selection_dialog import SelectionDialog
import backends
from common.constants import Constants
from common.settings import Settings
from common.messages import Messages
from common.setting_constants import Backends, Players, Genders
from common.logger import LazyLogger

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = LazyLogger.get_addon_module_logger().getChild(
        'lib.windowNavigation')
else:
    module_logger = LazyLogger.get_addon_module_logger()


class SettingsDialog(xbmcgui.WindowXMLDialog):

    HEADER_LABEL = 2
    ENGINE_TAB = 100
    OPTIONS_TAB = 200
    KEYMAP_TAB = 300
    ADVANCED_TAB = 400
    OK_BUTTON = 28
    CANCEL_BUTTON = 29
    DEFAULTS_BUTTON = 30
    ENGINE_GROUP_LIST = 101
    FIRST_SELECT_ID = SELECT_ENGINE_BUTTON = 102
    SELECT_ENGINE_VALUE_LABEL = 103
    SELECT_LANGUAGE_GROUP = 1104
    SELECT_LANGUAGE_BUTTON = 104
    SELECT_LANGUAGE_VALUE_LABEL = 105
    SELECT_VOICE_BUTTON = 106
    SELECT_VOICE_VALUE_LABEL = 107
    SELECT_GENDER_BUTTON = 108
    SELECT_GENDER_VALUE_LABEL = 109
    SELECT_PLAYER_BUTTON = 110
    SELECT_PLAYER_VALUE = 111
    SELECT_VOLUME_GROUP = 1112
    SELECT_VOLUME_LABEL = 112
    SELECT_VOLUME_SLIDER = 113
    SELECT_PITCH_GROUP = 1114
    SELECT_PITCH_LABEL = 114
    SELECT_PITCH_SLIDER = 115
    SELECT_SPEED_GROUP = 1116
    SELECT_SPEED_LABEL = 116
    SELECT_SPEED_SLIDER = 117
    SELECT_CACHE_GROUP = 1118
    SELECT_CACHE_BUTTON = 118
    SELECT_PIPE_GROUP = 1120
    SELECT_PIPE_BUTTON = 120
    SELECT_API_KEY_GROUP = 1122
    SELECT_API_KEY_EDIT = 122
    LAST_SELECT_ID = SELECT_API_KEY_EDIT
    OPTIONS_GROUP = 201
    OPTIONS_DUMMY_BUTTON = 202
    KEYMAP_GROUP = 301
    KEYMAP_DUMMY_BUTTON = 302
    ADVANCED_GROUP = 401
    ADVANCED_DUMMY_BUTTON = 402

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        """

        :param args:
        """
        # xbmc.executebuiltin('Skin.ToggleDebug')

        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: LazyLogger
        self._initialized = False
        self.exit_dialog = False
        super().__init__(*args)
        self.api_key = None
        self.engine = None
        self.backend_instance = None
        self.backend_class = None
        self.backend_changed = False
        self.gender = None
        self.language = None
        self.pitch = None
        self.player = None
        self.speed = None
        self.volume = None
        self._configure_temp_settings_enabled = False
        self.settings_changed = False
        self.previous_backend = None
        initial_backend = Settings.getSetting(Settings.BACKEND,
                                              Settings.BACKEND_DEFAULT)

        if initial_backend == Settings.BACKEND_DEFAULT:   # 'auto'
            initial_backend = backends.getAvailableBackends()[0].provider
            self.set_backend(initial_backend)
        else:
            self.get_backend_class(backend_id=initial_backend)

        self._logger.debug_extra_verbose('SettingsDialog.__init__')
        self.header = None  # type: Union[None, xbmcgui.ControlLabel]

        self.engine_tab = None  # type: Union[None, xbmcgui.ControlButton]
        self.options_tab = None  # type: Union[None, xbmcgui.ControlButton]
        self.keymap_tab = None  # type: Union[None, xbmcgui.ControlButton]
        self.advanced_tab = None  # type: Union[None, xbmcgui.ControlButton]

        self.engine_group = None  # type: Union[None, xbmcgui.Control]
        self.options_group = None  # type: Union[None, xbmcgui.ControlGroup]
        self.keymap_group = None  # type: Union[None, xbmcgui.ControlGroup]
        self.advanced_group = None  # type: Union[None, xbmcgui.ControlGroup]

        self.ok_button = None  # type: Union[None, xbmcgui.ControlButton]
        self.cancel_button = None  # type: Union[None, xbmcgui.ControlButton]
        self.defaults_button = None  # type: Union[None, xbmcgui.ControlButton]

        # type: Union[None, xbmcgui.ControlButton]
        self.engine_engine_button = None
        # type: Union[None, xbmcgui.ControlLabel]
        self.engine_engine_value: Union[None, xbmcgui.ControlButton] = None

        self.engine_language_group = None
        self.engine_language_button = None
        # type: Union[None, xbmcgui.ControlLabel]
        self.engine_language_value = None

        # type: Union[None, xbmcgui.ControlButton]
        self.engine_voice_button = None
        # type: Union[None, xbmcgui.ControlLabel]
        self.engine_voice_value = None

        # type: Union[None, xbmcgui.ControlButton]
        self.engine_gender_button = None
        # type: Union[None, xbmcgui.ControlLabel]
        self.engine_gender_value = None

        # type: Union[None, xbmcgui.ControlGroup]
        self.engine_pitch_group = None
        # type: Union[None, xbmcgui.ControlSlider]
        self.engine_pitch_slider = None
        # type: Union[None, xbmcgui.ControlLabel]
        self.engine_pitch_label = None

        # type: Union[None, xbmcgui.ControlButton]
        self.engine_player_button = None
        # type: Union[None, xbmcgui.ControlLabel]
        self.engine_player_value = None

        # type: Union[None, xbmcgui.ControlGroup]
        self.engine_pipe_audio_group = None
        # type: Union[None, xbmcgui.ControlRadioButton]
        self.engine_pipe_audio_radio_button = None

        # type: Union[None, xbmcgui.ControlGroup]
        self.engine_speed_group = None
        # type: Union[None, xbmcgui.ControlSlider]
        self.engine_speed_slider = None
        # type: Union[None, xbmcgui.ControlLabel]
        self.engine_speed_label = None

        # type: Union[None, xbmcgui.ControlGroup]
        self.engine_volume_group = None
        # type: Union[None, xbmcgui.ControlSlider]
        self.engine_volume_slider = None
        # type: Union[None, xbmcgui.ControlLabel]
        # type: Union[None, xbmcgui.ControlLabel]
        self.engine_volume_label = None

        # type: Union[None, xbmcgui.ControlGroup]
        self.engine_api_key_group = None
        # self.engine_api_key_label = None
        # type: Union[None, xbmcgui.ControlEdit]
        # type: Union[None, xbmcgui.ControlEdit]
        self.engine_api_key_edit = None

        self.options_dummy_button = None

        # type: Union[None, xbmcgui.ControlButton]
        self.keymap_dummy_button = None

        # type: Union[None, xbmcgui.ControlButton]
        self.advanced_dummy_button = None

        self._initialized = False

    def onInit(self):
        # type: () -> None
        """

        :return:
        """
        # super().onInit()
        self._logger.debug_verbose('SettingsDialog.onInit')

        if not self._initialized:
            # type: xbmcgui.ControlLabel
            self.header = self.getControl(type(self).HEADER_LABEL)
            addon_id = xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('id')
            addon_name = xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('id')
            self.header.setLabel('{} - {}'.format(Messages.get_msg(Messages.SETTINGS),
                                                  addon_name))

            # type: xbmcgui.ControlRadioButton
            self.engine_tab = self.getControl(type(self).ENGINE_TAB)
            self.engine_tab.setLabel(Messages.get_msg(Messages.ENGINE))
            self.engine_tab.setRadioDimension(x=0, y=0, width=186, height=40)

            self.engine_tab.setVisible(True)

            self.options_tab = self.getControl(
                type(self).OPTIONS_TAB)  # type: xbmcgui.ControlButton
            self.options_tab.setLabel(Messages.get_msg(Messages.OPTIONS))
            self.options_tab.setVisible(True)

            self.keymap_tab = self.getControl(
                type(self).KEYMAP_TAB)  # type: xbmcgui.ControlButton
            self.keymap_tab.setLabel(Messages.get_msg(Messages.KEYMAP))
            self.keymap_tab.setVisible(True)

            self.advanced_tab = self.getControl(
                type(self).ADVANCED_TAB)  # type: xbmcgui.ControlButton
            self.advanced_tab.setLabel(Messages.get_msg(Messages.ADVANCED))
            self.advanced_tab.setVisible(True)

            self.ok_button = self.getControl(
                type(self).OK_BUTTON)  # type: xbmcgui.ControlButton
            self.ok_button.setLabel(Messages.get_msg(Messages.OK))
            self.ok_button.setVisible(True)

            self.cancel_button = self.getControl(
                type(self).CANCEL_BUTTON)  # type: xbmcgui.ControlButton
            self.cancel_button.setLabel(Messages.get_msg(Messages.CANCEL))
            self.cancel_button.setVisible(True)

            self.defaults_button = self.getControl(
                type(self).DEFAULTS_BUTTON)  # type: xbmcgui.ControlButton
            self.defaults_button.setLabel(Messages.get_msg(Messages.DEFAULTS))
            self.defaults_button.setVisible(True)

            # self.engine_group = self.getControl(101)  # type: xbmcgui.ControlGroup
            # self.engine_group.setVisible(True)

            self.engine_engine_button = self.getControl(
                type(self).SELECT_ENGINE_BUTTON)  # type: xbmcgui.ControlButton
            self.engine_engine_button.setLabel(
                Messages.get_msg(Messages.DEFAULT_TTS_ENGINE))

            self.engine_engine_value = self.getControl(
                type(self).SELECT_ENGINE_VALUE_LABEL)  # type: xbmcgui.ControlLabel
            engine_label = Backends.get_label(self.get_engine())
            self.engine_engine_value.setLabel(engine_label)

            self.engine_language_group = self.getControl(
                type(self).SELECT_LANGUAGE_GROUP)
            self.engine_language_button = self.getControl(
                type(self).SELECT_LANGUAGE_BUTTON)  # type: xbmcgui.ControlButton
            self.engine_language_button.setLabel(
                Messages.get_msg(Messages.SELECT_LANGUAGE))

            self.engine_language_value = self.getControl(
                type(self).SELECT_LANGUAGE_VALUE_LABEL)  # type: xbmcgui.ControlLabel
            self.engine_language_value.setLabel(self.get_language())

            self.engine_voice_button = self.getControl(
                type(self).SELECT_VOICE_BUTTON)  # type: xbmcgui.ControlButton
            self.engine_voice_button.setLabel(
                Messages.get_msg(Messages.SELECT_VOICE))

            self.engine_voice_value = self.getControl(
                type(self).SELECT_VOICE_VALUE_LABEL)  # type: xbmcgui.ControlLabel
            self.engine_voice_value.setLabel(self.get_language())

            self.engine_gender_button = self.getControl(
                type(self).SELECT_GENDER_BUTTON)  # type: xbmcgui.ControlButton
            self.engine_gender_button.setLabel(
                Messages.get_msg(Messages.SELECT_VOICE_GENDER))

            self.engine_gender_value = self.getControl(
                type(self).SELECT_GENDER_VALUE_LABEL)  # type: xbmcgui.ControlLabel
            self.engine_gender_value.setLabel(self.get_gender())

            self.engine_pitch_group = self.getControl(
                type(self).SELECT_PITCH_GROUP)  # type: xbmcgui.ControlGroup
            self.engine_pitch_label = self.getControl(
                type(self).SELECT_PITCH_LABEL)  # type: xbmcgui.ControlLabel
            self.engine_pitch_label.setLabel(
                Messages.get_msg(Messages.SELECT_PITCH))

            self.engine_pitch_slider = self.getControl(
                type(self).SELECT_PITCH_SLIDER)  # type: xbmcgui.ControlSlider

            self.engine_player_button = self.getControl(
                type(self).SELECT_PLAYER_BUTTON)  # type: xbmcgui.ControlLabel
            self.engine_player_button.setLabel(
                Messages.get_msg(Messages.SELECT_PLAYER))

            self.engine_player_value = self.getControl(
                type(self).SELECT_PLAYER_VALUE)  # type: xbmcgui.ControlButton
            self.engine_player_value.setLabel(self.get_player())

            self.engine_cache_speech_group = self.getControl(
                type(self).SELECT_CACHE_GROUP)
            self.engine_cache_speech_radio_button = self.getControl(
                type(self).SELECT_CACHE_BUTTON)  # type: xbmcgui.ControlRadioButton
            self.engine_cache_speech_radio_button.setLabel(
                Messages.get_msg(Messages.CACHE_SPEECH))

            self.engine_pipe_audio_group = self.getControl(
                type(self).SELECT_PIPE_GROUP)
            self.engine_pipe_audio_radio_button = self.getControl(
                type(self).SELECT_PIPE_BUTTON)  # type: xbmcgui.ControlRadioButton
            self.engine_pipe_audio_radio_button.setLabel(
                Messages.get_msg(Messages.PIPE_AUDIO))

            self.engine_speed_group = self.getControl(
                type(self).SELECT_SPEED_GROUP)  # type: xbmcgui.ControlGroup
            self.engine_speed_label = self.getControl(
                type(self).SELECT_SPEED_LABEL)  # type: xbmcgui.ControlLabel
            self.engine_speed_label.setLabel(
                Messages.get_msg(Messages.SELECT_SPEED))

            self.engine_speed_slider = self.getControl(
                type(self).SELECT_SPEED_SLIDER)  # type: xbmcgui.ControlSlider

            self.engine_volume_group = self.getControl(
                type(self).SELECT_VOLUME_GROUP)  # type: xbmcgui.ControlGroup
            self.engine_volume_label = self.getControl(
                type(self).SELECT_VOLUME_LABEL)  # type: xbmcgui.ControlLabel
            self.engine_volume_label.setLabel(
                Messages.get_msg(Messages.SELECT_VOLUME_DB))

            self.engine_volume_slider = self.getControl(
                type(self).SELECT_VOLUME_SLIDER)  # type: xbmcgui.ControlSlider

            self.engine_api_key_group = self.getControl(
                type(self).SELECT_API_KEY_GROUP)  # type: xbmcgui.ControlGroup
            # self.engine_api_key_label = self.getControl(
            #    118  # type: xbmcgui.ControlLabel
            # self.engine_api_key_label.setLabel(util.T(32233))

            self.engine_api_key_edit = self.getControl(
                type(self).SELECT_API_KEY_EDIT)  # type: xbmcgui.ControlEdit
            self.engine_api_key_edit.setLabel(
                Messages.get_msg(Messages.API_KEY))

            self.options_group = self.getControl(
                type(self).OPTIONS_GROUP)  # type: xbmcgui.ControlGroup
            self.options_group.setVisible(True)

            self.options_dummy_button = self.getControl(
                type(self).OPTIONS_DUMMY_BUTTON)  # type: xbmcgui.ControlLabel
            self.options_dummy_button.setLabel('Options Trader')

            self.keymap_group = self.getControl(
                type(self).KEYMAP_GROUP)  # type: xbmcgui.ControlGroup
            self.keymap_group.setVisible(True)

            self.keymap_dummy_button = self.getControl(
                type(self).KEYMAP_DUMMY_BUTTON)  # type: xbmcgui.ControlLabel
            self.keymap_dummy_button.setLabel('KeyMap finder')

            self.advanced_group = self.getControl(
                type(self).ADVANCED_GROUP)  # type: xbmcgui.ControlGroup
            self.advanced_group.setVisible(True)

            self.advanced_dummy_button = self.getControl(
                type(self).ADVANCED_DUMMY_BUTTON)  # type: xbmcgui.ControlLabel
            self.advanced_dummy_button.setLabel('Advanced degree')
            self.update_engine_values()

            self._initialized = True
            self.settings_changed = False

    def update_engine_values(self):
        #
        # This assumes that changes to a setting does not impact a previous
        # setting.
        #
        self.set_backend_field()
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

        if self.backend_changed:
            from service import TTSService
            TTSService.get_instance().checkBackend()
            # cmd ='XBMC.NotifyAll({},RELOAD_ENGINE)'.format(Constants.ADDON_ID)
            # xbmc.executebuiltin(cmd)
            self.backend_changed = False

    def doModal(self):
        # type: () -> False
        """

        :return:
        """
        self.show()
        super().doModal()
        return

    def show(self):
        # type: () -> None
        """

        :return:
        """
        self._logger.debug_verbose('SettingsDialog.show')
        super().show()

    def close(self):
        # type: () -> None
        """

        :return:
        """
        super().close()

    def getFocus(self):
        # type: () -> None
        """

        :return:
        """
        pass

        super().getFocus()

    def onAction(self, action):
        # type: (xbmcgui.Action) -> None
        """

        :param action:
        :return:
        """
        action_id = action.getId()
        if action_id == xbmcgui.ACTION_MOUSE_MOVE:
            return

        if self._logger.isEnabledFor(LazyLogger.DEBUG_EXTRA_VERBOSE):
            action_mapper = Action.get_instance()
            matches = action_mapper.getKeyIDInfo(action)

            for line in matches:
                self._logger.debug_extra_verbose(line)

            button_code = action.getButtonCode()

            # These return empty string if not found
            action_key = action_mapper.getActionIDInfo(action)
            remote_button = action_mapper.getRemoteKeyButtonInfo(action)
            remote_key_id = action_mapper.getRemoteKeyIDInfo(action)

            # Returns found button_code, or 'key_' +  action_button
            action_button = action_mapper.getButtonCodeId(action)

            key_codes = []

            if action_key != '':
                key_codes.append(action_key)
            if remote_button != '':
                key_codes.append(remote_button)
            if remote_key_id != '':
                key_codes.append(remote_key_id)
            if len(key_codes) == 0:
                key_codes.append(str(action_button))
            self._logger.debug_extra_verbose('Key found:', ','.join(key_codes))

        self._logger.debug_verbose('action_id: {}'.format(action_id))
        if (action_id == xbmcgui.ACTION_PREVIOUS_MENU
                or action_id == xbmcgui.ACTION_NAV_BACK):
            exit_dialog = True
            self.close()

    def onClick(self, controlId):
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

    def handle_engine_tab(self, controlId):
        '''

        :param controlId:
        :return:
        '''

        if controlId == type(self).SELECT_ENGINE_BUTTON:
            self.select_backend()

        elif controlId == type(self).SELECT_LANGUAGE_BUTTON:
            self.select_language()

        elif controlId == type(self).SELECT_VOICE_BUTTON:
            self.select_voice()

        elif controlId == type(self).SELECT_GENDER_BUTTON:
            self.select_gender()

        elif controlId == type(self).SELECT_PITCH_SLIDER:
            self.select_pitch()

        elif controlId == type(self).SELECT_PLAYER_BUTTON:
            self.select_player()

        elif controlId == type(self).SELECT_CACHE_BUTTON:
            self.select_cache_speech()

        elif controlId == type(self).SELECT_PIPE_BUTTON:
            self.select_pipe_audio()

        elif controlId == type(self).SELECT_SPEED_SLIDER:
            self.select_speed()

        elif controlId == type(self).SELECT_VOLUME_SLIDER:
            self.select_volume()

        elif controlId == type(self).SELECT_API_KEY_EDIT:
            self.select_api_key()

    def set_backend_field(self):
        choices, current_choice_index = self.get_backend_choices()
        backend = choices[current_choice_index]
        self.engine_engine_value.setLabel(backend.getLabel())
        if len(choices) < 2:
            self.engine_engine_value.setEnabled(False)
        else:
            self.engine_engine_value.setEnabled(True)

        self.set_backend(backend.getLabel2())

    def get_backend_choices(self):
        self._logger.debug_verbose('get_backend_choices')
        auto_choice_label = Messages.get_msg(Messages.AUTO)
        choices = list()
        list_item = xbmcgui.ListItem(auto_choice_label)
        list_item.setLabel2(Settings.BACKEND_DEFAULT)
        choices.append(list_item)
        current_value = self.getSetting(
            Settings.BACKEND, Settings.BACKEND_DEFAULT)
        current_choice_index = 0
        for b in backends.getAvailableBackends():
            self._logger.debug_verbose(Settings.BACKEND, b.displayName)
            list_item = xbmcgui.ListItem(b.displayName)
            list_item.setLabel2(b.provider)
            choices.append(list_item)
            if b.provider == current_value:
                current_choice_index = len(choices) - 1

        return choices, current_choice_index

    def select_backend(self):
        self._logger.enter()
        choices, current_choice_index = self.get_backend_choices()
        if current_choice_index < 0:
            current_choice_index = 0
        script_path = Constants.ADDON_PATH
        self._logger.debug_verbose(
            'SettingsDialog ADDON_PATH: {}'.format(Constants.ADDON_PATH))
        selection_dialog = SelectionDialog('selection-dialog.xml',
                                           script_path, 'Default',
                                           title=Messages.get_msg(
                                               Messages.SELECT_SPEECH_ENGINE),
                                           choices=choices, initial_choice=current_choice_index)

        selection_dialog.show()
        selection_dialog.doModal()
        idx = selection_dialog.getCurrentListPosition()
        self._logger.debug_verbose('SelectionDialog value:',
                                   Messages.get_msg(Messages.CHOOSE_BACKEND),
                                   'idx:', str(idx))
        if idx < 0:
            return None

        engine = choices[idx]
        self._logger.debug_verbose('select_backend value: {} idx: {}'
                                   .format(engine.getLabel(),
                                           str(idx)))

        self.engine_engine_value.setLabel(engine.getLabel())
        new_backend = engine.getLabel2()
        if new_backend != self.previous_backend:
            self.set_backend(new_backend)

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

        languages, default_setting = backends.getSettingsList(
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

        voices = backends.getSettingsList(
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
        supported_genders = backends.getSettingsList(engine, Settings.GENDER)
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

        supported_players, default_player = backends.getSettingsList(
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
        constraints = self.get_backend_class().get_volume_constraints()
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
        if not self.get_backend_class().isSettingSupported(Settings.PITCH):
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
        pitch_constraints = self.get_backend_class().get_pitch_constraints()
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
        if self.get_backend_class().isSettingSupported(Settings.SPEED):
            lower, upper, current = self.get_speed_range()
            if lower == upper:
                self.engine_speed_group.setVisible(False)
            else:
                increment = int((upper - lower + 19) / 20)
                self.engine_speed_slider.setInt(
                    current, lower, increment, upper)
                self.engine_speed_group.setVisible(True)

    def get_speed_range(self):
        constraints = self.get_backend_class().get_speed_constraints()
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
        if self.get_backend_class().isSettingSupported(Settings.CACHE_SPEECH):
            self.engine_cache_speech_group.setVisible(True)
            cache_speech = self.engine_cache_speech_radio_button.isSelected()
            self.setSetting(Settings.CACHE_SPEECH, cache_speech)
            # self.update_engine_values()
        else:
            self.engine_cache_speech_group.setVisible(False)

    def set_cache_speech_field(self):
        if self.get_backend_class().isSettingSupported(Settings.CACHE_SPEECH):
            cache_speech = bool(self.getSetting(Settings.CACHE_SPEECH))
            self.engine_cache_speech_group.setVisible(True)
            self.engine_cache_speech_radio_button.setVisible(True)
            self.engine_cache_speech_radio_button.setSelected(cache_speech)
        else:
            self.engine_cache_speech_group.setVisible(False)

    def select_pipe_audio(self):
        if self.get_backend_class().isSettingSupported(Settings.PIPE):
            self.engine_pipe_audio_group.setVisible(True)
            use_pipe = self.engine_pipe_audio_radio_button.isSelected()
            self.setSetting(Settings.PIPE, use_pipe)
            # self.update_engine_values()
        else:
            self.engine_pipe_audio_group.setVisible(False)

    def set_pipe_audio_field(self):
        if self.get_backend_class().isSettingSupported(Settings.PIPE):
            use_pipe = bool(self.getSetting(Settings.PIPE))
            self.engine_pipe_audio_radio_button.setVisible(True)
            self.engine_pipe_audio_radio_button.setSelected(use_pipe)
        else:
            self.engine_pipe_audio_radio_button.setSelected(False)

    def select_api_key(self):
        api_key = self.engine_api_key_edit.getText()
        self.setSetting(Settings.API_KEY, api_key)

    def set_api_field(self):
        if self.get_backend_class().isSettingSupported(Settings.API_KEY):
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
    def get_engine(self):
        # Deliberately using Settings.getSetting here
        if self.engine is None or self.settings_changed:
            self.engine = Settings.getSetting(Settings.BACKEND,
                                              Settings.BACKEND_DEFAULT)  # type: str

        if self.engine == Settings.BACKEND_DEFAULT:  # 'auto'
            self.engine = backends.getAvailableBackends()[0].provider
            self.set_backend(self.engine)

        return self.engine

    def get_language(self):
        if self.settings_changed:
            self.language = self.get_backend_class().getSetting(Settings.LANGUAGE,
                                                                Settings.LANGUAGE_DEFAULT)  # type: str
        return self.language

    def get_gender(self):
        if self.settings_changed:
            gender_default = self.get_backend_class().get_setting_default(Settings.GENDER)
            self.gender = self.get_backend_class().getSetting(Settings.GENDER,
                                                              gender_default)  # type: str
        return self.gender

    def get_pitch(self):
        if self.settings_changed:
            pitch_default = self.get_backend_class().get_setting_default(Settings.PITCH)
            self.pitch = self.get_backend_class().getSetting(Settings.PITCH,
                                                             pitch_default)  # type: int
        return self.pitch

    def get_player(self):
        if self.settings_changed:
            player_default = self.get_backend_class().get_setting_default(Settings.PLAYER)
            self.player = self.get_backend_class().getSetting(Settings.PLAYER,
                                                              player_default)  # type: str
        return self.player

    def set_player(self, player_id):
        self.player = player_id
        self.setSetting(Settings.PLAYER, player_id)
        self.get_backend_instance().setPlayer(player_id)

    def get_speed(self):
        if self.settings_changed:
            speed_default = self.get_backend_class().get_setting_default(Settings.SPEED)
            self.speed = self.get_backend_class().getSetting(Settings.SPEED,
                                                             speed_default)  # type: int
        return self.speed

    def get_volume(self):
        if self.settings_changed:
            volume_default = self.get_backend_class().get_setting_default(Settings.VOLUME)
            volume_str = self.get_backend_class().getSetting(Settings.VOLUME,
                                                             volume_default)  # type: int
            try:
                volume_int = int(volume_str)  # type: int
            except:
                volume_int = 0
            self.volume = volume_int  # type: int
        return self.volume

    def get_api_key(self):
        if self.settings_changed:
            self.api_key = self.get_backend_class().getSetting(Settings.API_KEY,
                                                               Settings.API_KEY_DEFAULT)  # type: str

        return self.api_key

    # def get_pipe_audio(self):
    #    pipe_default = self.get_backend_class().get_setting_default(Settings.PIPE)
    #    engine_pipe_audio = self.get_backend_class().getSetting(Settings.PIPE,
    #                                                            pipe_default)  # type: bool
    #    cmd = 'Skin.String(engine_pipe_audio,{:b})'.format(engine_pipe_audio)
    #    xbmc.executebuiltin(cmd)
    #    return engine_pipe_audio

    def set_backend(self, backend_id):
        if self.previous_backend != backend_id:
            self.get_backend_class(backend_id=backend_id)
            self.setSetting(Settings.BACKEND, backend_id)
            self.backend_instance = None
            self.engine = backend_id
            Settings.backend_changed(self.get_backend_class())
            self.previous_backend = backend_id
            self.settings_changed = True
            self.backend_changed = True

    def get_backend_class(self, backend_id=None):
        provider_id = backend_id
        if provider_id is None:
            provider_id = self.engine
        if provider_id != self.engine:
            if self.backend_class is None or self.backend_class.provider != provider_id:
                self.backend_class = backends.getBackendByProvider(provider_id)
        return self.backend_class

    def get_backend_instance(self):
        if self.backend_instance is None or self.backend_instance.provider != self.engine:
            self.backend_instance = self.get_backend_class()()

        return self.backend_instance

    def getSetting(self, key, default=None):
        if default is None:
            default = self.get_backend_class().get_setting_default(key)
        value = self.get_backend_class().getSetting(key, default)
        if value is None:
            value = default
        return value

    def setSetting(self, key, value):
        if not self._configure_temp_settings_enabled:
            Settings.backend_changed(self.get_backend_class())
            self._configure_temp_settings_enabled = True

        changed = self.get_backend_class().setSetting(key, value)
        if changed:
            self.settings_changed = True

    def save_settings(self):
        Settings.commit_settings()
        #  TTSService.get_instance().checkBackend()

    def discard_settings(self):
        # Need to load previous settings and then set engine to it
        pass
