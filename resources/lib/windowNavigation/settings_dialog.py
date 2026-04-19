# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc
import xbmcaddon
import xbmcgui
from xbmcgui import (ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider)

import langcodes
from backends.base import *
from backends.settings.engine_lang import EngineLang
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_manager import EngineVoiceManager
from backends.settings.i_validators import (INumericValidator, UIValues)
from backends.settings.lang_utils import LangUtils
from backends.settings.service_types import EngineType, PlayerType, ServiceID
from backends.settings.settings_helper import SettingsHelper
from backends.settings.settings_map import SettingsMap
from common.constants import Constants
from common.exceptions import ConfigurationError
from common.logger import *
from common.message_ids import MessageId
from common.messages import Messages
from common.setting_constants import (Backends, Genders)
from common.settings import Settings
from utils.util import get_language_code
from windowNavigation.action_map import Action
from windowNavigation.choice import (Choice, Choices, EngineChoice, EngineChoices,
                                     VGChoice, VoiceChoice,
                                     VoiceChoices, VGChoices)
from windowNavigation.configure import Configure, EngineConfig
from windowNavigation.selection_dialog import SelectionDialog

MY_LOGGER = BasicLogger.get_logger(__name__)


class SettingsDialog(xbmcgui.WindowXMLDialog):
    HEADER_LABEL: Final[int] = 1
    BASIC_CONFIG_LABEL: Final[int] = 2
    # ENGINE_TAB: Final[int] = 100
    # OPTIONS_TAB: Final[int] = 200
    # KEYMAP_TAB: Final[int] = 300
    # ADVANCED_TAB: Final[int] = 400
    OK_BUTTON_ID: Final[int] = 28
    CANCEL_BUTTON_ID: Final[int] = 29
    DEFAULTS_BUTTON_ID: Final[int] = 30
    ENGINE_GROUP_LIST: Final[int] = 101
    SELECT_ENGINE_BUTTON: Final[int] = 102
    FIRST_SELECT_ID: Final[int] = SELECT_ENGINE_BUTTON
    SELECT_ENGINE_VALUE_LABEL: Final[int] = 103
    SELECT_VOICE_GROUP: Final[int] = 1104
    SELECT_VOICE_BUTTON: Final[int] = 104
    SELECT_VOICE_VALUE_LABEL: Final[int] = 105
    X_SELECT_VOICE_GROUP: Final[int] = 1106
    X_SELECT_VOICE_BUTTON: Final[int] = 106
    X_SELECT_VOICE_VALUE_LABEL: Final[int] = 107
    SELECT_GENDER_GROUP: Final[int] = 1108
    SELECT_GENDER_BUTTON: Final[int] = 108
    SELECT_GENDER_VALUE_LABEL: Final[int] = 109
    SELECT_PLAYER_GROUP: Final[int] = 1110
    SELECT_PLAYER_BUTTON: Final[int] = 110
    SELECT_PLAYER_VALUE_LABEL: Final[int] = 111
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
    SELECT_PLAYER_MODE_GROUP: Final[int] = 1120
    SELECT_PLAYER_MODE_BUTTON: Final[int] = 120
    SELECT_PLAYER_MODE_LABEL_VALUE: Final[int] = 121
    SELECT_API_KEY_GROUP: Final[int] = 1122
    SELECT_API_KEY_LABEL: Final[int] = 122
    SELECT_API_KEY_EDIT: Final[int] = 123
    LAST_SELECT_ID: Final[int] = SELECT_API_KEY_EDIT
    # OPTIONS_GROUP: Final[int] = 201
    # OPTIONS_DUMMY_BUTTON: Final[int] = 202
    # KEYMAP_GROUP: Final[int] = 301
    # KEYMAP_DUMMY_BUTTON: Final[int] = 302
    # ADVANCED_GROUP: Final[int] = 401
    # ADVANCED_DUMMY_BUTTON: Final[int] = 402

    _selection_dialog: SelectionDialog | None = None

    def __init__(self, *args, **kwargs) -> None:
        """

        :param args:
        """
        # xbmc.executebuiltin('Skin.ToggleDebug')

        Monitor.register_abort_listener(listener=self.on_abort_requested)

        self.closing = False
        self._initialized: bool = False
        self.is_modal: bool = False
        # Makes sure that Settings stack is restored to same depth as
        # when entered. Required due to exit being user input and
        # asynchronous
        # Tracks duplicate calls to onInit. Reset in doModal
        self.init_count: int = 0
        self.exit_dialog: bool = False
        super().__init__(*args)
        self.cfg: Configure = Configure.instance()
        #  self.api_key = None
        self.engine_instance: ITTSBackendBase | None = None
        # self.backend_changed: bool = False
        # self.gender_id: int | None = None
        # self.language: str | None = None
        # self.pitch: float | None = None
        # self.player: str | None = None
        # self.player_mode: str | None = None
        # self.module: str | None = None
        # self.speed: float | None = None
        # self.volume: int | None = None
        # self.settings_changed: bool = False

        # For refresh_tts
        self.prev_engine_key: ServiceID | None = None
        self.prev_player_key: ServiceID | None = None
        self.prev_player_mode: PlayerMode | None = None

        initial_backend: ServiceID
        initial_backend = Settings.get_engine_key()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'initial_backend: {initial_backend}')

        # if initial_backend == ServiceKey.ESPEAK_KEY:  # 'auto'
        #     initial_backend = BackendInfo.getAvailableBackends()[0].engine_id
        self.cfg.getEngineInstance(initial_backend)

        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv('SettingsDialog.__init__')
        self.header: ControlLabel | None = None
        self.basic_config_label: ControlLabel | None = None
        # self.engine_tab: ControlRadioButton | None = None
        # self.options_tab: ControlButton | None = None
        # self.keymap_tab: ControlButton | None = None
        # self.advanced_tab: ControlButton | None = None
        self.engine_group: ControlGroup | None = None
        # self.options_group: ControlGroup | None = None
        # self.keymap_group: ControlGroup | None = None
        # self.advanced_group: ControlGroup | None = None
        self.ok_button: ControlButton | None = None
        self.cancel_button: ControlButton | None = None
        self.defaults_button: ControlButton | None = None
        self.engine_api_key_group: ControlGroup | None = None
        self.engine_api_key_edit: ControlEdit | None = None
        self.engine_api_key_label: ControlLabel | None = None
        self.engine_engine_button: ControlButton | None = None
        self.engine_engine_value: ControlLabel | None = None
        self.engine_voice_group: ControlGroup | None = None
        self.engine_voice_button: ControlButton | None = None
        self.engine_voice_value: ControlLabel | None = None
        self.engine_voice_x_group: ControlGroup | None = None
        self.engine_voice_x_button: ControlButton | None = None
        self.engine_voice_x_value: ControlLabel | None = None
        self.engine_gender_group: ControlGroup | None = None
        self.engine_gender_button: ControlButton | None = None
        self.engine_gender_value: ControlLabel | None = None
        self.engine_pitch_group: ControlGroup | None = None
        self.engine_pitch_slider: ControlSlider | None = None
        self.engine_pitch_label: ControlLabel | None = None
        self.engine_player_group: ControlGroup | None = None
        self.engine_player_button: ControlButton | None = None
        self.engine_player_value: ControlButton | None = None  # player and module
        self.engine_module_value: ControlButton | None = None  # share button real-estate
        self.engine_pipe_audio_group: ControlGroup | None = None
        self.engine_player_mode_group: ControlGroup | None = None
        self.engine_pipe_audio_radio_button: ControlRadioButton | None = None
        self.engine_player_mode_button: ControlButton | None = None
        self.engine_player_mode_label: ControlLabel | None = None
        self.engine_speed_group: ControlGroup | None = None
        self.engine_speed_slider: ControlSlider | None = None
        self.engine_speed_label: ControlLabel | None = None
        self.engine_cache_speech_group: ControlGroup | None = None
        self.engine_cache_speech_radio_button: ControlRadioButton | None = None
        self.engine_volume_group: ControlGroup | None = None
        self.engine_volume_slider: ControlSlider | None = None
        self.engine_volume_label: ControlLabel | None = None
        # self.options_dummy_button: ControlButton | None = None
        # self.keymap_dummy_button: ControlButton | None = None
        # self.advanced_dummy_button: ControlButton | None = None

    @property
    def engine_id(self) -> str:
        """
            Gets the setting_id from Settings. If the value is invalid, substitutes
            with one designated as 'good'. If a substitution is performed, the
            substitute is stored in Settings
        TODO: Review. There should be only one method to get engine_id in consistent
              way.
        :return:
        """
        return self.cfg.engine_key.service_id

    @property
    def engine_key(self) -> ServiceID:
        """
        :return:
        """
        return self.cfg.engine_key

    def re_init(self) -> None:
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'In re-init')
        self.closing = False
        self.exit_dialog = False
        # self.api_key = None

    def onInit(self) -> None:
        """

        :return:
        """
        #  super().onInit()
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v('SettingsDialog.onInit')
        self.re_init()
        engine_key: ServiceID = self.engine_key

        try:
            if not self._initialized:
                self.header = self.get_control_label(clz.HEADER_LABEL)
                # MY_LOGGER.debug(f'Header: {self.header.getLabel()}')
                # self.engine_tab = self.get_control_radio_button(clz.ENGINE_TAB)
                # self.engine_tab.setLabel(Messages.get_msg(Messages.ENGINE))
                # self.engine_tab.setRadioDimension(x=0, y=0, width=186, height=40)
                # self.engine_tab.setVisible(True)
                # self.options_tab = self.get_control_button(
                #         clz.OPTIONS_TAB)
                # self.options_tab.setLabel(Messages.get_msg(Messages.OPTIONS))
                # self.options_tab.setVisible(True)

                # self.keymap_tab = self.get_control_button(
                #         clz.KEYMAP_TAB)
                # self.keymap_tab.setLabel(Messages.get_msg(Messages.KEYMAP))
                # self.keymap_tab.setVisible(True)

                # self.advanced_tab = self.get_control_button(
                #        clz.ADVANCED_TAB)
                # self.advanced_tab.setLabel(Messages.get_msg(Messages.ADVANCED))
                # self.advanced_tab.setVisible(True)

                self.ok_button: ControlButton = self.get_control_button(
                        clz.OK_BUTTON_ID)
                self.ok_button.setLabel(MessageId.OK_BUTTON.get_msg())
                self.ok_button.setVisible(True)

                self.cancel_button = self.get_control_button(
                        clz.CANCEL_BUTTON_ID)
                self.cancel_button.setLabel(MessageId.CANCEL_BUTTON.get_msg())
                self.cancel_button.setVisible(True)

                self.defaults_button: ControlButton = self.get_control_button(
                        clz.DEFAULTS_BUTTON_ID)
                self.defaults_button.setLabel(MessageId.DEFAULTS_BUTTON.get_msg())
                self.defaults_button.setVisible(True)

                # self.engine_group = self.get_control_group(clz.ENGINE_GROUP_LIST)
                # self.engine_group.setVisible(True)

                self.basic_config_label = self.get_control_label(clz.BASIC_CONFIG_LABEL)

                self.engine_engine_button = self.get_control_button(
                        clz.SELECT_ENGINE_BUTTON)

                self.engine_engine_value = self.get_control_label(
                        clz.SELECT_ENGINE_VALUE_LABEL)

                self.engine_voice_group = self.get_control_group(
                        clz.SELECT_VOICE_GROUP)
                self.engine_voice_button: ControlButton = self.get_control_button(
                        clz.SELECT_VOICE_BUTTON)

                self.engine_voice_value = self.get_control_label(
                        clz.SELECT_VOICE_VALUE_LABEL)

                self.engine_voice_x_group = self.get_control_group(
                        clz.X_SELECT_VOICE_GROUP)
                self.engine_voice_x_button: ControlButton = self.get_control_button(
                        clz.X_SELECT_VOICE_BUTTON)
                self.engine_voice_x_value = self.get_control_label(
                        clz.X_SELECT_VOICE_VALUE_LABEL)

                self.engine_gender_group = self.get_control_group(
                        clz.SELECT_GENDER_GROUP)
                self.engine_gender_button: ControlButton = self.get_control_button(
                        clz.SELECT_GENDER_BUTTON)
                self.engine_gender_value = self.get_control_label(
                        clz.SELECT_GENDER_VALUE_LABEL)

                self.engine_pitch_group = self.get_control_group(
                        clz.SELECT_PITCH_GROUP)
                self.engine_pitch_label = self.get_control_label(
                        clz.SELECT_PITCH_LABEL)
                self.engine_pitch_slider = self.get_control_slider(
                        clz.SELECT_PITCH_SLIDER)
                # Disable setting pitch for now
                self.engine_pitch_group.setVisible(False)

                # NOTE: player and module share control. Only one active at a
                #       time. Probably should create two distinct buttons and
                #       control visibility

                self.engine_player_group = self.get_control_group(
                        clz.SELECT_PLAYER_GROUP)
                self.engine_player_button = self.get_control_button(
                        clz.SELECT_PLAYER_BUTTON)
                self.engine_player_group.setVisible(False)
                #   TODO:   !!!!!
                #         Move to where player or module are about to be displayed

                self.engine_player_value = self.get_control_button(
                        clz.SELECT_PLAYER_VALUE_LABEL)
                self.engine_module_value = self.get_control_button(
                        clz.SELECT_PLAYER_VALUE_LABEL)

                self.engine_player_group.setVisible(True)
                self.engine_player_button.setVisible(True)

                self.engine_cache_speech_group = self.get_control_group(
                        clz.SELECT_CACHE_GROUP)
                self.engine_cache_speech_radio_button = \
                    self.get_control_radio_button(
                            clz.SELECT_CACHE_BUTTON)

                self.engine_player_mode_group = self.get_control_group(
                        clz.SELECT_PLAYER_MODE_GROUP)
                self.engine_player_mode_button = \
                    self.get_control_button(
                            clz.SELECT_PLAYER_MODE_BUTTON)
                self.engine_player_mode_label = self.get_control_label(
                        clz.SELECT_PLAYER_MODE_LABEL_VALUE)
                self.engine_api_key_group = self.get_control_group(
                        clz.SELECT_API_KEY_GROUP)
                self.engine_api_key_edit = self.get_control_edit(
                        clz.SELECT_API_KEY_EDIT)
                # self.engine_api_key_label = self.get_control_label(
                #         clz.SELECT_API_KEY_LABEL)

                self.engine_speed_group = self.get_control_group(
                        clz.SELECT_SPEED_GROUP)
                self.engine_speed_label = self.get_control_label(
                        clz.SELECT_SPEED_LABEL)
                self.engine_speed_slider = self.get_control_slider(
                        clz.SELECT_SPEED_SLIDER)
                self.engine_volume_group = self.get_control_group(
                        clz.SELECT_VOLUME_GROUP)
                self.engine_volume_label = self.get_control_label(
                        clz.SELECT_VOLUME_LABEL)
                self.engine_volume_slider = self.get_control_slider(
                        clz.SELECT_VOLUME_SLIDER)

                # self.options_group = self.get_control_group(
                #         clz.OPTIONS_GROUP)
                # self.options_group.setVisible(True)

                # self.options_dummy_button = self.get_control_label(
                #         clz.OPTIONS_DUMMY_BUTTON)
                # self.options_dummy_button.setLabel('Options Trader')

                # self.keymap_group = self.get_control_group(
                #         clz.KEYMAP_GROUP)
                # self.keymap_group.setVisible(True)

                # self.keymap_dummy_button = self.get_control_label(
                #         clz.KEYMAP_DUMMY_BUTTON)
                # self.keymap_dummy_button.setLabel('KeyMap finder')

                # self.advanced_group = self.get_control_group(
                #         clz.ADVANCED_GROUP)
                # self.advanced_group.setVisible(True)

                # self.advanced_dummy_button = self.get_control_label(
                #         clz.ADVANCED_DUMMY_BUTTON)
                # self.advanced_dummy_button.setLabel('Advanced degree')
                self._initialized = True

            # Now, assign values to controls, including all text since it is
            # possible for the kodi language to have changed
            addon_id = xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('id')
            addon_name = xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('id')
            self.header.setLabel(f'{Messages.get_msg(Messages.SETTINGS)} '
                                 f'- {addon_name}')
            self.header.setVisible(True)

            # MY_LOGGER.debug(f'Header: {self.header.getLabel()}')
            # self.engine_tab = self.get_control_radio_button(clz.ENGINE_TAB)
            # self.engine_tab.setLabel(Messages.get_msg(Messages.ENGINE))
            # self.engine_tab.setRadioDimension(x=0, y=0, width=186, height=40)
            # self.engine_tab.setVisible(True)
            # self.options_tab = self.get_control_button(
            #         clz.OPTIONS_TAB)
            # self.options_tab.setLabel(Messages.get_msg(Messages.OPTIONS))
            # self.options_tab.setVisible(True)

            # self.keymap_tab = self.get_control_button(
            #         clz.KEYMAP_TAB)
            # self.keymap_tab.setLabel(Messages.get_msg(Messages.KEYMAP))
            # self.keymap_tab.setVisible(True)

            # self.advanced_tab = self.get_control_button(
            #        clz.ADVANCED_TAB)
            # self.advanced_tab.setLabel(Messages.get_msg(Messages.ADVANCED))
            # self.advanced_tab.setVisible(True)

            self.ok_button.setLabel(MessageId.OK_BUTTON.get_msg())
            self.ok_button.setVisible(True)

            self.cancel_button.setLabel(MessageId.CANCEL_BUTTON.get_msg())
            self.cancel_button.setVisible(True)

            self.defaults_button.setLabel(MessageId.DEFAULTS_BUTTON.get_msg())
            self.defaults_button.setVisible(True)

            # self.engine_group.setVisible(True)

            self.basic_config_label.setLabel(MessageId.BASIC_CONFIGURATION.get_msg())
            self.basic_config_label.setVisible(True)

            engine_label: str = Backends.get_label(engine_key.service_id)
            self.engine_engine_value.setLabel(engine_label)

            e_voice_id: str = Settings.get_voice_id(engine_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'setting_id: {engine_key.service_id} '
                                f'engine_voice: {e_voice_id}')
            self.engine_engine_button.setLabel(MessageId.ENGINE_LABEL.get_msg())

            self.engine_voice_button.setLabel(
                    MessageId.SELECT_VOICE_BUTTON.get_msg())
            #  self.get_voice_label()
            voice_key: ServiceID = engine_key.with_prop(SettingProp.VOICE)
            avail: bool = SettingsMap.is_setting_available(voice_key,
                                                           SettingProp.VOICE)
            valid: bool = SettingsMap.is_valid_setting(voice_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'is voice available engine: {engine_key} {avail}')
                MY_LOGGER.debug(f'is voice valid: {valid}')
            if not valid:
                self.engine_voice_x_group.setVisible(False)
            else:
                self.engine_voice_x_button.setLabel(
                        MessageId.SELECT_VOICE_BUTTON.get_msg())
                self.engine_voice_x_group.setVisible(True)
                self.engine_voice_x_value.setLabel(self.get_language(label=True))
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'engine_voice_x_value: '
                                    f'{self.engine_voice_x_value.getLabel()}')

            if not SettingsMap.is_valid_setting(engine_key.with_prop(SettingProp.GENDER)):
                self.engine_gender_group.setVisible(False)
            else:
                self.engine_gender_button.setLabel(
                        MessageId.VOICE_GENDER_BUTTON.get_msg())
                try:
                    gender: Genders = Settings.get_gender(engine_key)
                    self.engine_gender_value.setLabel(gender.name)
                    self.engine_gender_group.setVisible(False)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    MY_LOGGER.exception('')

            # TODO: Get pitch working again
            #  self.set_pitch_field(update_ui=True, engine_id=service_key,
            #                      pitch=Settings.get_pitch(engine_id=self.engine_id))

            # NOTE: player and module share control. Only one active at a
            #       time. Probably should create two distinct buttons and
            #       control visibility

            #   TODO:   !!!!!
            # Move to where player or module are about to be displayed

            if SettingsMap.is_valid_setting(engine_key.with_prop(SettingProp.PLAYER)):
                self.engine_player_button.setLabel(
                        MessageId.SELECT_PLAYER.get_msg())
                player_id: str = Settings.get_player().service_id
                player: PlayerType = PlayerType(player_id)
                self.set_player_field(update_ui=True,
                                      engine_key=engine_key,
                                      player=player)
            else:
                self.engine_player_button.setLabel(
                        Messages.get_msg(Messages.SELECT_MODULE))
                self.engine_module_value.setLabel(self.cfg.get_module())
                self.engine_module_value.setVisible(True)

            self.engine_player_group.setVisible(True)
            self.engine_player_button.setVisible(True)

            self.engine_cache_speech_radio_button.setLabel(
                    Messages.get_msg(Messages.CACHE_SPEECH))

            self.engine_player_mode_button.setLabel(
                    Messages.get_msg_by_id(32336))
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'player_mode_button label: '
                                f'{Messages.get_msg_by_id(32336)}')
                MY_LOGGER.debug(f'player_mode button label: '
                                f'{Messages.get_msg(Messages.PLAYER_MODE)}')
                MY_LOGGER.debug(f'player_mode button label: '
                                f'{xbmc.getLocalizedString(32336)}')
                MY_LOGGER.debug(f'player_mode button label: '
                                f'{xbmcaddon.Addon().getLocalizedString(32336)}')

            # self.engine_api_key_label = self.get_control_label(
            #         clz.SELECT_API_KEY_LABEL)
            # self.engine_api_key_label.setLabel(util.T(32233))
            # self.engine_api_key_edit.setLabel(
            #         Messages.get_msg(Messages.API_KEY))

            speed: float = Settings.get_speed()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'speed: {speed}')
            self.set_speed_field(update_ui=True, speed=speed)
            volume: float = Settings.get_volume()
            self.set_volume_field(update_ui=True, volume=volume)

            # self.options_group = self.get_control_group(
            #         clz.OPTIONS_GROUP)
            # self.options_group.setVisible(True)

            # self.options_dummy_button = self.get_control_label(
            #         clz.OPTIONS_DUMMY_BUTTON)
            # self.options_dummy_button.setLabel('Options Trader')

            # self.keymap_group = self.get_control_group(
            #         clz.KEYMAP_GROUP)
            # self.keymap_group.setVisible(True)

            # self.keymap_dummy_button = self.get_control_label(
            #         clz.KEYMAP_DUMMY_BUTTON)
            # self.keymap_dummy_button.setLabel('KeyMap finder')

            # self.advanced_group = self.get_control_group(
            #         clz.ADVANCED_GROUP)
            # self.advanced_group.setVisible(True)

            # self.advanced_dummy_button = self.get_control_label(
            #         clz.ADVANCED_DUMMY_BUTTON)
            # self.advanced_dummy_button.setLabel('Advanced degree')
            self.update_engine_values()

            self.setFocus(self.engine_engine_button)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_control_button(self, iControlId: int) -> xbmcgui.ControlButton:
        """

        :param iControlId:
        :return:
        """
        buttonControl: xbmcgui.Control = super().getControl(iControlId)
        buttonControl: xbmcgui.ControlButton
        return buttonControl

    def get_control_edit(self, iControlId: int) -> xbmcgui.ControlEdit:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlEdit
        return control

    def get_control_group(self, iControlId: int) -> xbmcgui.ControlGroup:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlGroup
        return control

    def get_control_label(self, iControlId: int) -> xbmcgui.ControlLabel:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlLabel
        return control

    def get_control_radio_button(self, iControlId: int) -> xbmcgui.ControlRadioButton:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlRadioButton
        return control

    def get_control_slider(self, iControlId: int) -> xbmcgui.ControlSlider:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control = super().getControl(iControlId)
        control: xbmcgui.ControlSlider
        return control

    # def set_radio_dimension(self):
    #   self.engine_tab.setRadioDimension(x=0, y=0, width=186, height=40)

    def update_engine_values(self):
        """
        Applies all updates in response to user changes

        The order is intentional. Each called method is responsible for updating
        the UI and internal state, including preventing any incorrect configurations.

        :return:
        """
        try:
            # Engine, language, voice and gender are very tightly related. Also
            # player_mode is related
            # self.set_engine()
            #  self.get_global_allowed_player_modes()
            engine_key: ServiceID = self.engine_key
            # self.validate_and_set_voice_field()
            self.set_voice_field(update_ui=True,
                                 e_voice=None)
            # self.set_voice_field(update_ui=True)
            # self.set_gender_field() # Not that useful at this time.
            # Player and player_mode are inter-dependent
            # Speed, volume and pitch are also closely related to player, but not as
            # much as player/player-mode
            if SettingsMap.is_valid_setting(engine_key.with_prop(SettingProp.PLAYER)):
                self.set_player_field(update_ui=True)
            elif SettingsMap.is_valid_setting(engine_key.with_prop(SettingProp.MODULE)):
                self.set_module_field()
            self.set_player_mode_field(update_ui=True)
            self.set_pitch_range()
            self.set_speed_field(update_ui=True, speed=None)  # Update ui, not value
            self.set_volume_field(update_ui=True, volume=None)  # Update ui, not value
            self.set_api_field(engine_key)
            # self.set_pipe_audio_field()
            self.set_cache_speech_field(update_ui=True, engine_key=engine_key)
        except Exception as e:
            MY_LOGGER.exception('')

    def doModal(self) -> None:
        """

        :return:
        """
        # About to go modal
        # save (push) current settings onto settings stack. This will be our
        # working set of uncommitted changes. As each individual setting is
        # modified (tts engine), another save will be done to push this copy
        # of settings onto the stack. This allows each setting to have a private
        # copy that can be modified and discarded (by the user entering 'escape'
        # or 'backspace') or saved (via 'enter' or 'select'). When saved, the
        # changes are added to this first stack-frame for SettingsDialog.
        # When exiting SelectionDialog the user can choose to commit the changes
        # to the master settings, or discard all changes once this stack
        # entry is popped.
        clz = type(self)
        self.cfg.save_settings(msg='on entry BEFORE doModal', initial_frame=True)
        # settings saved in individual methods just before changes made
        self.is_modal = True
        super().doModal()
        self.is_modal = False
        # Discard all uncommitted changes
        self.cfg.restore_settings(msg='doModal exit', initial_frame=True)
        return

    def show(self) -> None:
        """

        :return:
        """
        # About to go modal
        # save (push) current settings onto settings stack. This will be our
        # working set of uncommitted changes. As each individual setting is
        # modified (tts engine), another save will be done to push this copy
        # of settings onto the stack. This allows each setting to have a private
        # copy that can be modified and discarded (by the user entering 'escape'
        # or 'backspace') or saved (via 'enter' or 'select'). When saved, the
        # changes are added to this first stack-frame for SettingsDialog.
        # When exiting SelectionDialog the user can choose to commit the changes
        # to the master settings, or discard all changes once this stack
        # entry is popped.
        clz = type(self)
        self.cfg.save_settings(msg='on entry BEFORE doModal', initial_frame=True)
        super().show()
        # Discard all uncommitted changes
        self.cfg.restore_settings(msg='show exit', initial_frame=True)

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

    def onAction(self, action: xbmcgui.Action) -> None:
        """

        :param action:onAction
        :return:
        """
        if self.closing:
            return

        try:
            action_id = action.getId()
            if action_id == xbmcgui.ACTION_MOUSE_MOVE:
                return

            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                action_mapper = Action.get_instance()
                matches = action_mapper.getKeyIDInfo(action)

                # for line in matches:
                #     MY_LOGGER.debug_xv(line)

                button_code: int = action.getButtonCode()
                # These return empty string if not found
                action_key: str = action_mapper.getActionIDInfo(action)
                remote_button: str = action_mapper.getRemoteKeyButtonInfo(action)
                remote_key_id: str = action_mapper.getRemoteKeyIDInfo(action)

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
                #  MY_LOGGER.debug(
                #         f'Key found: {",".join(key_codes)}')

                MY_LOGGER.debug_xv(f'action_id: {action_id}')
            if (action_id == xbmcgui.ACTION_PREVIOUS_MENU
                    or action_id == xbmcgui.ACTION_NAV_BACK):
                exit_dialog = True
                self.close()
        except Exception as e:
            MY_LOGGER.exception('')

    def onClick(self, controlId: int) -> None:
        """

        :param controlId:
        :return:
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'onClick:{controlId} closing: {self.closing}')
        if self.closing:
            return

        try:
            clz = type(self)
            '''
            focus_id = self.getFocusId()
            if controlId == 100:
                # MY_LOGGER.debug_v('Button 100 pressed')
                # self.engine_tab.setSelected(True)
                # self.options_group.setVisible(False)
                # self.keymap_group.setVisible(False)
                # self.advanced_group.setVisible(False)
                # self.engine_group.setVisible(True)

            elif controlId == 200:
                # MY_LOGGER.debug_v('Button 200 pressed')
                # self.engine_tab.setSelected(False)
                # self.engine_group.setVisible(False)
                # self.keymap_group.setVisible(False)
                # self.advanced_group.setVisible(False)
                # self.options_group.setVisible(True)

            elif controlId == 300:
                # MY_LOGGER.debug_v('Button 300 pressed')
                # self.engine_tab.setSelected(False)
                # self.engine_group.setVisible(False)
                # self.options_group.setVisible(False)
                # self.advanced_group.setVisible(False)
                # self.keymap_group.setVisible(True)

            elif controlId == 400:
                # MY_LOGGER.debug_v('Button 400 pressed')
                # self.engine_tab.setSelected(False)
                # self.engine_group.setVisible(False)
                # self.options_group.setVisible(False)
                # self.keymap_group.setVisible(False)
                # self.advanced_group.setVisible(True)
            '''
            if controlId in range(self.FIRST_SELECT_ID, self.LAST_SELECT_ID):
                self.handle_engine_tab(controlId)
            elif controlId == clz.OK_BUTTON_ID:
                # OK button
                self.closing = True
                self.cfg.commit_settings()
                # MY_LOGGER.info(f'ok button closing')
                self.close()

            elif controlId == clz.CANCEL_BUTTON_ID:
                # Cancel button
                # MY_LOGGER.debug(f'cancel button')
                self.closing = True
                self.close()

            elif controlId == clz.DEFAULTS_BUTTON_ID:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'defaults button')
                self.select_defaults()

        except Exception as e:
            MY_LOGGER.exception('')

    def onDoubleClick(self, controlId: int) -> None:
        """

        :param controlId:
        :return:
        """
        try:
            clz = type(self)
            if controlId in range(clz.FIRST_SELECT_ID, clz.LAST_SELECT_ID):
                pass
                #  self.handle_engine_tab(controlId)
            elif controlId == clz.OK_BUTTON_ID:
                self.closing = True
                self.cfg.commit_settings()
                # MY_LOGGER.info(f'ok button closing')
                self.close()

            elif controlId == clz.CANCEL_BUTTON_ID:
                # MY_LOGGER.debug(f'cancel button')
                self.closing = True
                self.close()

            elif controlId == clz.DEFAULTS_BUTTON_ID:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'defaults button')
                self.select_defaults()
                self.closing = True
                self.cfg.commit_settings()
                # MY_LOGGER.info(f'ok button closing')
                self.close()

        except Exception as e:
            MY_LOGGER.exception('')

    def on_abort_requested(self) -> None:
        try:
            self.closing = True
            #  xbmc.log('Received AbortRequested', xbmc.LOGINFO)
            self.close()
        except Exception:
            pass

    def handle_engine_tab(self, controlId: int) -> None:
        """

        :param controlId:
        :return:
        """
        clz = type(self)
        try:
            if controlId == clz.SELECT_ENGINE_BUTTON:
                self.select_engine()
            elif controlId == clz.SELECT_VOICE_BUTTON:
                self.select_voice_from_groups()
            elif controlId == clz.SELECT_GENDER_BUTTON:
                self.select_gender()
            elif controlId == clz.SELECT_PITCH_SLIDER:
                self.select_pitch()
            elif controlId == clz.SELECT_PLAYER_BUTTON:
                if SettingsMap.is_valid_setting(
                        self.engine_key.with_prop(SettingProp.PLAYER)):
                    self.select_player()
                else:
                    self.select_module()
            elif controlId == clz.SELECT_CACHE_BUTTON:
                self.select_cache_speech()
            elif controlId == clz.SELECT_PLAYER_MODE_BUTTON:
                self.select_player_mode()
            elif controlId == clz.SELECT_SPEED_SLIDER:
                self.select_speed()
            elif controlId == clz.SELECT_VOLUME_SLIDER:
                self.select_volume()
            elif controlId == clz.SELECT_API_KEY_EDIT:
                self.select_api_key()

            # if self.backend_changed:
            #     self.update_engine_values()
        except Exception as e:
            MY_LOGGER.exception('')

    def select_engine(self):
        """
            Displays the SelectionDialog for the user to choose the desired
            engine. Also makes the needed changes if the user modifies and saves
            their changes

        :return:
        """
        clz = type(self)
        try:
            engine_key: ServiceID = self.engine_key
            # Make sure that Settings stack depth is the same as when this module
            # was entered (should be 2).
            self.cfg.restore_settings('enter select_engine BEFORE do_modal')
            self.cfg.save_settings('select_engine enter BEFORE do_modal')
            self.refresh_tts(capture_settings=True)
            choices, current_choice_index = self.cfg.get_engine_choices(
                    engine_key=engine_key)
            choices: EngineChoices
            if current_choice_index < 0:
                current_choice_index = 0
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'# choices: {len(choices)} current_choice_idx: '
                                f'{current_choice_index}')
                MY_LOGGER.debug(f'sub_title: {MessageId.SELECT_TTS_ENGINE.get_msg()}')
            dialog: SelectionDialog
            dialog = self.selection_dialog(
                    title=MessageId.CHOOSE_TTS_ENGINE.get_msg(),
                    dialog_subject='Engine',
                    sub_title=MessageId.SELECT_TTS_ENGINE.get_msg(),
                    choices=choices,
                    selection_index=current_choice_index,
                    call_on_focus=self.voice_engine)
            # xbmc.executebuiltin(function=f'control.setHidden(101)', wait=False)
            dialog.doModal()
            """
            At this point the user has either chosen to cancel configuring the
            engine settings by using the BACK button, or similar to return from
            SelectionDialog.
            OR the user exited the SelectionDialog by selecting a configuration.
            In this case the user wants to keep those changes with the opportunity
            to cfg other settings.
            """
            # Revert all changes made during SelectionDialog
            self.cfg.restore_settings(msg='select_engine after doModal')  # Pops one
            # Get selected index
            idx = dialog.sel_data.chosen_idx
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'SelectionDialog value: '
                                  f'{MessageId.TTS_ENGINE.get_msg()} '
                                  f'idx: {str(idx)}')
            if idx < 0:  # No selection made or CANCELED
                return

            # User wants to keep the changes made during selection. The settings have
            # already been reverted to prior to configuring for SelectionDialog.
            #
            # Since a different engine is currently being used, making changes
            # for new engine's settings can safely be done without impacting
            # the current one. Therefore,change settings tightly coupled to
            # engine settings BEFORE switching to use the new engine.
            # First, change: voice, player, player_mode, use of cache, any transcoder.
            # Secondary settings that are less critical to set: speed, volume,

            choice: EngineChoice = choices[idx]
            if choice is not None:
                engine_config: EngineConfig
                engine_config = self.cfg.configure_engine(choice, save_as_current=True)
                if engine_config is not None:
                    engine_config.volume = 0.0
                    engine_config.speed = 1.0
                    self.set_all_engine_fields(engine_config=engine_config)
                    self.refresh_tts()

        except Exception as e:
            MY_LOGGER.exception('')

    def voice_engine(self, choice: EngineChoice,
                     selection_idx: int) -> None:
        """
        Used during engine selection to voice which engine is in focus.

        Uses the voice/dialect closet to the currently configured Kodi locale_id

        :param choice: Choice for instance of engine to be voiced
        :param selection_idx: index of Choice from Choices list. Redundant
        :return:
        """
        if choice is None:
            return
        try:
            self.cfg.configure_engine(choice, save_as_current=True)
            self.refresh_tts()
        except Exception as e:
            MY_LOGGER.exception('')

    def set_all_engine_fields(self, engine_config: EngineConfig) -> None:
        """
        Updates the UI for all engine related fields

        :param engine_config:
        :return:
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'engine_config: {engine_config}')
        try:
            lang: EngineLang = engine_config.lang
            e_voice_id: EngineVoice = engine_config.voice
            engine_key: ServiceID = engine_config.engine_key

            engine_voice: EngineVoice
            engine_voice = EngineVoiceManager.get_eng_voice_by_uid(e_voice_id.uid)
            self.set_voice_field(update_ui=True,
                                 e_voice=engine_voice)
            # self.set_gender_field(update_ui=True,
            #                       engine_key=engine_key)
            self.set_player_mode_field(update_ui=True,
                                       engine_key=engine_key,
                                       player_mode=engine_config.player_mode)
            self.set_player_field(update_ui=True,
                                  engine_key=engine_key,
                                  player=engine_config.player)
            # cache setting visibility depends upon player/player_mode
            self.set_cache_speech_field(update_ui=True,
                                        engine_key=engine_key,
                                        use_cache=engine_config.use_cache)
            Settings.set_transcoder(engine_config.transcoder, engine_key)
            self.set_speed_field(update_ui=True,
                                 speed=engine_config.speed)
            self.set_volume_field(update_ui=True,
                                  volume=engine_config.volume)
            self.set_engine_field(update_ui=True,
                                  engine_key=engine_key)
        except Exception:
            MY_LOGGER.exception('')

    '''
    def validate_and_set_voice_field(self, lang_id: str | None = None,
                                     engine_key: ServiceID | None = None) -> None:
        """
        Configures the Voice UI field, processing the related settings
        and resolving any incompatibility issues with other settings.

        :param lang_id:
        :param engine_key:
        :return:
        """
        try:
            if engine_key is None:
                engine_key = self.engine_key
            if lang_id is None:
                lang_id = Settings.get_language(engine_key)
            vg_choices: VGChoices
            current_vg_idx: int
            result: VGSelectionTuple
            result = SettingsHelper.get_vg_choices(engine_key=engine_key)
            vg_choices = result.vg_choices
            current_vg_idx = result.selected_vg_idx
            current_voice_idx: int = result.selected_voice_idx
            default_vg_idx: int = result.default_vg_idx
            self.cfg.save_current_choices(vg_choices, current_vg_idx)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'# choices: {len(vg_choices)} '
                                f'current_vg_idx: {current_vg_idx} '
                                f'default_vg_idx: {default_vg_idx}')
            if len(vg_choices) == 0:
                self.engine_voice_group.setVisible(True)
                self.engine_voice_value.setEnabled(False)

            selected_voice_idx: int = current_voice_idx
            if selected_voice_idx < 0:
                selected_voice_idx = default_vg_idx
                if selected_voice_idx < 0:
                    selected_voice_idx = 0

                vg_choice: VGChoice = vg_choices[current_vg_idx]
                selected_voice: VoiceChoice = vg_choice.voice_choices[selected_voice_idx]
                voice_name: str = selected_voice.label
                lang_id: str = selected_voice.voice.engine_lang_id
                voice_id: VoiceID = selected_voice.voice.engine_voice
                self.engine_voice_value.setLabel(f'voice_id: {voice_id} '
                                                 f'voice_name: {voice_name}')
                self.engine_voice_group.setVisible(True)
                if len(vg_choices) < 2:  # No point choosing between one choice
                    self.engine_voice_value.setEnabled(False)
                else:
                    self.engine_voice_value.setEnabled(True)
                Settings.set_language(lang_id)
                voice_id.set_current_voice(voice_id)
        except IndexError:
            return None
        except Exception as e:
            MY_LOGGER.exception('')
            return None
    '''

    def select_voice_from_groups(self):
        """
        Presents the user with a list of the engine-specific voice-groups to choose
        a voice from. MOST Voice-Groups have only a single voice in the group,
        so it is fairly simple to treat the group and the voice as the same.

        For those Voice-Groups which contain multiple voices, the process is more
        complicated. When the Selection Dialog focuses on a Voice-Group, then either
        the only voice in the group is voiced, or, the default voice in the group
        is voiced. If the user selects the Voice-Group and confirms their choice,
        a second selection dialog will appear where the user can choose from all
        the voices in that group. If the user selects and commits their choice,
        then both dialogs are exited with the confirmed choice saved as the voice
        to use for the engine.

        All setting changes are applied to the current frame of the Settings
        stack. Only when the SettingsDialog is exited via the OK button are
        they committed to settings.xml and available to the rest of kodi TTS.

        When the TTS engine is chosen (by select engine), you only get the
        calculated 'good-enough' voice. Here you get to fine tune it.

        :return:
        """
        clz = type(self)
        try:
            choices: VGChoices
            engine_key: ServiceID = self.engine_key
            # Gets every VoiceGroup for every lang-territory for the current engine
            # Sorted first by closeness of match to native lang-territory
            # and second by lang-territory name.
            vg_choices: VGChoices
            vg_choices = SettingsHelper.get_vg_choices(engine_key=engine_key)
            current_vg_idx = vg_choices.selected_vg_idx
            MY_LOGGER.debug(f'current_vg_idx: {current_vg_idx} len(vg_choices): '
                            f'{len(vg_choices)}')
            current_vg: VGChoice = vg_choices[current_vg_idx]
            default_vg_idx: int = vg_choices.default_vg_idx

            current_voice_idx: int = current_vg.selected_v_idx

            MY_LOGGER.debug(
                    f'current_vg_idx: {current_vg_idx} current_vg: '
                    f'{current_vg.label} current_voice_idx: '
                    f'{current_voice_idx} default_vg_idx: {default_vg_idx}')
            MY_LOGGER.debug(f'current_voice: '
                            f'{current_vg.v_choices[current_voice_idx].label}')

            if len(vg_choices) == 0:
                # Do NOT change UI. These values will not be committed
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(
                            f'No VoiceGroup choices found. No changes made')
                return
            self.cfg.save_current_choices(vg_choices, current_vg_idx)
            self.refresh_tts(capture_settings=True)
            #  MY_LOGGER.debug(f'In select_voice_from_groups # choices: {len(choices)} '
            #                  f'current_choice_idx {current_choice_idx} '
            #                  f'current_choice: {choices[current_choice_idx]}')
            kodi_language: langcodes.Language
            lang_name: str
            lang_name = LangUtils.get_translated_language_name(
                    LangUtils.kodi_language)
            engine_name: str
            engine_name = EngineType(engine_key.service_id).label
            title: str
            title = MessageId.AVAIL_VOICES_FOR_LANG.get_formatted_msg(
                    lang_name, engine_name)
            sub_title: str
            sub_title = (MessageId.SELECT_VOICE_FROM_GROUP.get_msg())
            self.cfg.restore_settings(
                    msg='select_voice_from_groups BEFORE do_modal')
            self.cfg.save_settings('select_voice_from_groups BEFORE do_modal')
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'sub_title: {sub_title}')

            # If a voiceGroup is selected, then the SelectionDialog will call
            # select_voice_from_group to decide which voice in the group to select
            # MY_LOGGER.debug(f'Calling selection_dialog for choosing voice')
            # MY_LOGGER.debug(f'call_on_select: {self.select_voice_from_group}')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           dialog_subject='VGroups',
                                           sub_title=sub_title,
                                           choices=vg_choices,
                                           selection_index=current_vg_idx,
                                           call_on_focus=self.voice_the_voice,
                                           call_on_select=self.get_voices_from_group)
            dialog.doModal()
            # Restore to state prior to SelectionDialog
            self.cfg.restore_settings(
                    msg='select_voice_from_groups AFTER doModal')

            # Now, apply any desired changes
            MY_LOGGER.debug(f'Voice idx: {dialog.sel_data.chosen_idx} '
                            f'value: {dialog.sel_data.chosen_object}')
            vg_idx: int = dialog.sel_data.chosen_idx
            if vg_idx < 0:  # No selection made or CANCELED
                return

            vg_choice: VGChoice = dialog.sel_data.chosen_object
            e_voice: EngineVoice
            v_choice: VoiceChoice | None = None
            if isinstance(vg_choice, VoiceChoice):
                v_choice = vg_choice
                MY_LOGGER.debug(f'VoiceChoice: {v_choice}')
            else:
                voice_idx = vg_choice.selected_v_idx
                MY_LOGGER.debug(f'voices: {len(vg_choice.v_choices)}')
                v_choice = vg_choice.v_choices[voice_idx]
            e_voice = v_choice.e_voice
            MY_LOGGER.debug(f'Choice is Voice e_voice: {e_voice}')
            self.set_voice_field(update_ui=True,
                                 e_voice=e_voice)
            self.refresh_tts()
        except Exception as e:
            MY_LOGGER.exception('')

    def get_voices_from_group(self, vg_choice: VGChoice, _: int) -> bool:
        """
        Very similar to select_voice_from_groups. This is only called when
        a user selects a VoiceGroup containing multiple voices from
        select_voice_from_groups. When that occurs, this method is called
        causing the SelectionDialog to be updated to contain the Voices of
        the Group. This method returns to select_voice_from_groups, which
        resumes allowing the user to select a voice from the VoiceGroups.

        All setting changes are applied to the current frame of the Settings
        stack. Only when the SettingsDialog is exited via the OK button are
        they committed to settings.xml and available to the rest of kodi TTS.

        When the TTS engine is chosen (by select_engine), you only get the
        calculated 'good-enough' voice. Here you can select a specific voice.

        :return: True if successful, False otherwise
        """
        clz = type(self)
        try:
            v_choices: VoiceChoices = vg_choice.v_choices
            engine_key: ServiceID = self.engine_key
            current_voice_idx: int = vg_choice.selected_v_idx
            default_voice_idx: int = 0
            MY_LOGGER.debug(f'current_voice_idx: {current_voice_idx} '
                            f'default_voice_idx: {default_voice_idx}')

            if len(v_choices) == 0:
                # Do NOT change UI. These values will not be committed
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'No Voice choices found. No changes made')
                return False
            self.cfg.save_current_choices(v_choices, current_voice_idx)
            self.refresh_tts(capture_settings=True)
            kodi_language: langcodes.Language
            vg_name: str
            vg_name = vg_choice.label

            title: str
            title = MessageId.AVAILABLE_VOICES_FOR_GROUP.get_formatted_msg(
                    vg_name)
            sub_title: str
            sub_title = (MessageId.SELECT_VOICE_FROM_GROUP.get_msg())
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'sub_title: {sub_title}')

            clz._selection_dialog.update_data(title=title,
                                              dialog_subject='VoiceChoices',
                                              choices=v_choices,
                                              selection_index=current_voice_idx,
                                              sub_title=sub_title,
                                              call_on_focus=self.voice_the_voice,
                                              call_on_select=None,
                                              disable_tts=False)
            return True
            '''
            # Now, apply any desired changes
            chosen_idx: int = dialog.sel_data.chosen_idx
            #  self.sel_data.chosen_idx = sel_idx
            choice: EngineChoice | VoiceChoice | VGChoice | int
            choice = dialog.sel_data.selected_object
            vg_choice.selected_v_idx = chosen_idx
            MY_LOGGER.debug(f'chosen_idx: {chosen_idx} choice: {choice} '
                            f'selected_v_idx: {vg_choice.selected_v_idx}')
            if chosen_idx < 0:  # No selection made or CANCELED
                return -1

            v_choice: VoiceChoice = v_choices[chosen_idx]
            e_voice: EngineVoice = v_choice.e_voice
            MY_LOGGER.debug(f'Choice v_choice: {v_choice.choice_index}'
                            f' e_voice: {e_voice}')
            self.set_voice_field(update_ui=True,
                                 e_voice=e_voice)
            self.refresh_tts()
            return chosen_idx
            '''

        except Exception as e:
            MY_LOGGER.exception('')
        return False

    def voice_the_voice(self, choice: VGChoice | VoiceChoice,
                        selection_idx: int) -> None:
        """
           Used during voice selection to voice the currently focused voice or
           voice-group.

           :param choice: can be either the chosen VGChoice or VoiceChoice
           :param selection_idx: index selected item (redundant)

           :return:
           """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'idx: {selection_idx}')
        engine_key: ServiceID = self.engine_key
        if choice is None:
            raise ValueError(f'Choice is None')

        e_voice: EngineVoice | None = None
        if isinstance(choice, VGChoice):
            # When a group is selected (and not a voice within it),
            # then select and voice the default voice from the group.

            vg_choice: VGChoice = choice
            e_voice = vg_choice.e_vg.default_e_voice  # Default Voice of group
            vg_choice.set_selected_ev_idx(e_voice.e_voice_id)
            selected_voice: VoiceChoice
            selection_idx: int = vg_choice.selected_v_idx
            selected_voice = vg_choice.v_choices[selection_idx]
            e_voice = selected_voice.e_voice
            MY_LOGGER.debug(f'VGChoice: {vg_choice.label} voice: {e_voice}')
        else:  # choice is a voice
            e_voice = choice.e_voice
            MY_LOGGER.debug(f'VoiceChoice e_voice: {e_voice}')
        self.set_voice_field(update_ui=False,
                             e_voice=e_voice)
        self.refresh_tts()

    '''
    def get_pitch_range(self) -> UIValues:
        return
        

        result: UIValues | None = None
        try:
            pitch_key: ServiceID = ServiceID(ServiceType.ENGINE, Services.GOOGLE_ID,
                                             SettingSettingProp.PITCH)

            pitch_val: INumericValidator
            pitch_val = SettingsMap.get_validator(pitch_key)
            if pitch_val is None:
                raise NotImplementedError
            result = pitch_val.get_tts_values()
        except NotImplementedError:
            result = UIValues()
        return result
        '''

    def select_pitch(self) -> None:
        """

        """
        return
    '''
        try:
            pitch_val: INumericValidator
            pitch_val = SettingsMap.get_validator(self.engine_id,
                                                  SettingProp.PITCH)
            if pitch_val is None:
                raise NotImplementedError

            pitch = self.engine_pitch_slider.getInt()
            pitch_val.set_value(pitch)
        except Exception as e:
            MY_LOGGER.exception('')
    '''

    def set_pitch_range(self):
        """

        """
        return
    '''
        try:
            if not SettingsMap.is_valid_setting(self.engine_id,
                                                 SettingProp.PITCH):
                self.engine_pitch_group.setVisible(False)
            else:
                pitch_val: NumericValidator
                result: UIValues = self.get_pitch_range()
                if result.minimum == result.maximum:
                    self.engine_pitch_group.setVisible(False)
                else:
                    self.engine_pitch_slider.setInt(
                            result.current, result.minimum, result.increment,
                            result.maximum)
                    self.engine_pitch_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')
    '''

    def select_gender(self):
        """

        :return:
        """
        clz = type(self)
        try:
            self.refresh_tts(capture_settings=True)
            engine_key: ServiceID = self.engine_key
            choices: Choices
            choices, current_choice_index = self.cfg.get_gender_choices(engine_key)
            # xbmc.executebuiltin('Skin.ToggleDebug')
            title: str = MessageId.VOICE_GENDER_BUTTON.get_msg()
            self.cfg.restore_settings(msg='select_gender BEFORE doModal')
            self.cfg.save_settings('select_gender BEFORE doModal')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           dialog_subject='Gender',
                                           choices=choices,
                                           selection_index=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.cfg.restore_settings(msg='select_gender AFTER doModal')
            idx = dialog.sel_data.chosen_idx
            if idx < 0:
                return

            choice: Choice = choices[idx]
            gender: Genders = Genders(choice.value)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'select_gender label: {choice.label} '
                                  f'setting: {choice.value} idx: {idx:d}')
            self.engine_gender_value.setLabel(choice.label)
            Settings.set_gender(engine_key=engine_key, gender=gender)
            self.refresh_tts()
        except Exception as e:
            MY_LOGGER.exception(msg='')

    def select_player(self):
        """
        Launches SelectionDialog for user to try out and choose a player.
        Call-back functions (onclick, onfocus, etc.) will respond to user
        actions in real time. For example, if a player is selected which
        does not support PlayerMode.SLAVE_FILE, then the SLAVE_FILE option
        will be disabled and the player mode will be switched from SLAVE_FILE
        if necessary.

        :return:
        """
        try:
            engine_key: ServiceID = self.engine_key
            choices: EngineChoices
            (choices, current_choice_index) = self.cfg.get_player_choices(engine_key)
            title: str = MessageId.SELECT_PLAYER.get_msg()
            sub_title: str = MessageId.SELECT_PLAYER_SUBTITLE.get_msg()
            self.cfg.restore_settings(msg='select_player BEFORE doModal')
            self.cfg.save_settings('select_player BEFORE doModal')
            self.refresh_tts(capture_settings=True)
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           dialog_subject='Player',
                                           sub_title=sub_title,
                                           choices=choices,
                                           selection_index=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.cfg.restore_settings(msg='select_player AFTER doModal')
            idx = dialog.sel_data.chosen_idx
            if idx < 0:
                return

            choice: Choice = choices[idx]
            player_id: str = choice.value
            player: PlayerType = PlayerType(player_id)
            enabled: bool = choice.enabled
            player_label: str = choice.label
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'select_player value: {player_label} '
                                  f'setting: {player_id} idx: {idx:d} '
                                  f'enabled: {enabled}')

            player_mode: PlayerMode
            #  player_mode = Settings.get_player_mode(engine_key)
            engine_config: EngineConfig | None = None
            try:
                engine_config = self.cfg.configure_player(engine_key=engine_key,
                                                          lang=None,
                                                          use_cache=None,
                                                          player=player,
                                                          engine_audio=None,
                                                          player_mode=None)
            except ConfigurationError:
                MY_LOGGER.exception('Config Error')
                return None

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'engine_config: service_key: {engine_config.engine_key} '
                                f'use_cache: {engine_config.use_cache} '
                                f'player: {engine_config.player} '
                                f'engine_audio: {engine_config.engine_audio} '
                                f'player_mode: {engine_config.player_mode} '
                                f'transcoder: {engine_config.transcoder} '
                                f'trans_audio_in: {engine_config.trans_audio_in} '
                                f'trans_audio_out: {engine_config.trans_audio_out}')
            self.set_player_mode_field(update_ui=True,
                                       engine_key=engine_key,
                                       player_mode=engine_config.player_mode)
            #  self.engine_player_value.setLabel(player_label)
            self.set_player_field(update_ui=True,
                                  engine_key=engine_key,
                                  player=engine_config.player)
            self.cfg.set_engine_audio(engine_key=engine_key,
                                      engine_audio=engine_config.engine_audio)
            self.cfg.set_transcoder_field(engine_key=engine_key,
                                          transcoder=engine_config.transcoder)
            self.cfg.set_cache_speech_field(engine_key=engine_key,
                                            use_cache=engine_config.use_cache)
            self.refresh_tts()
        except Exception as e:
            MY_LOGGER.exception('')

    def select_module(self):
        """

        :return:
        """
        clz = type(self)
        try:
            choices: Choices
            engine_key: ServiceID = self.engine_key
            (choices, current_choice_index) = self.cfg.get_module_choices(engine_key)
            title: str = Messages.get_msg(Messages.SELECT_MODULE)
            self.cfg.restore_settings(msg='select_module BEFORE doModal')
            self.cfg.save_settings('select_module BEFORE doModal')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           dialog_subject='Module',
                                           choices=choices,
                                           selection_index=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.cfg.restore_settings(msg='select_module AFTER doModal')
            idx = dialog.sel_data.chosen_idx
            if idx < 0:
                return

            choice: Choice = choices[idx]
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'value: {choice.label} '
                                  f'setting: {choice.value} idx: {idx:d}')
            self.engine_module_value.setLabel(choice.label)
            Settings.set_module(service_key=engine_key, value=choice.value)
            # self.update_engine_values()
        except Exception as e:
            MY_LOGGER.exception('')

    def select_volume(self) -> None:
        """
        Configures the global volume of all engines
        """
        try:
            volume: float = self.engine_volume_slider.getFloat()
            self.set_volume_field(update_ui=True, volume=volume)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_volume_field(self, update_ui: bool, volume: float | None = None):
        """
            :param update_ui: If True, update the UI, otherwise just update
                              Settings
            :param volume: Specifies the volume value to set. If None, then
                           set get volume from Settings
        """
        try:
            if not SettingsMap.is_valid_setting(ServiceKey.TTS_KEY.with_prop(
                                                                     SettingProp.VOLUME)):
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Volume is NOT valid property')
                self.engine_volume_group.setVisible(False)
            else:
                if volume is not None:
                    self.cfg.set_volume_field(volume)  # Saves Setting
                if update_ui:
                    result: UIValues = self.get_volume_range()  # Uses setting just saved
                    if result.minimum == result.maximum:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Volume min == max. NOT visible')
                        self.engine_volume_group.setVisible(False)
                    else:
                        self.engine_volume_slider.setFloat(
                                result.current, result.minimum, result.increment,
                                result.maximum)
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'set volume range current: {result.current} '
                                            f'min: {result.minimum} inc:'
                                            f' {result.increment} '
                                            f'max: {result.maximum}')
                        volume: float = result.current
                        label: str
                        label = MessageId.VOLUME_DB.get_formatted_msg(f'{volume:.1f}')
                        self.engine_volume_label.setLabel(label=label)
                        self.engine_volume_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_volume_range(self) -> UIValues:
        """

        :return:
        """
        result: UIValues | None = None
        try:
            result = self.cfg.volume_val.get_tts_values()
        except NotImplementedError:
            result = UIValues()
            MY_LOGGER.exception(f'service_key: {self.engine_key} volume: {result}')
        return result

    def select_speed(self):
        """
        Configures the speed of all engines (globally shared property)
        """
        try:
            speed: float = self.engine_speed_slider.getFloat()
            self.set_speed_field(update_ui=True, speed=speed)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_speed_field(self, update_ui: bool, speed: float | None = None):
        """
            :param update_ui: if True, update the UI, otherwise just update Settings
            :param speed: Specifies the speed value to set. If None, then get speed
                          from Settings
        """
        try:
            if not SettingsMap.is_valid_setting(ServiceKey.TTS_KEY.with_prop(
                                                                    SettingProp.SPEED)):
                self.engine_speed_group.setVisible(False)
            else:
                if speed is not None:
                    self.cfg.set_speed_field(speed=speed)  # Saves setting
                if update_ui:
                    result: UIValues = self.get_speed_range()  # Uses setting just saved
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'min: {result.minimum} max: {result.maximum} '
                                        f'inc: {result.increment} current: '
                                        f'{result.current}')
                    if result.minimum == result.maximum:
                        self.engine_speed_group.setVisible(False)
                    else:
                        self.engine_speed_slider.setFloat(
                                result.current, result.minimum, result.increment,
                                result.maximum)
                        # Speed is ignored by players that don't support it, such as
                        # SFX.
                        speed: float = result.current
                        label: str = MessageId.SPEED.get_formatted_msg(f'{speed:.1f}')
                        self.engine_speed_label.setLabel(label)
                        self.engine_speed_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_speed_range(self) -> UIValues:
        """

        :return:
        """
        try:
            speed_val: INumericValidator
            speed_val = SettingsMap.get_validator(ServiceKey.TTS_KEY.with_prop(
                                                                    SettingProp.SPEED))
            speed_val: TTSNumericValidator
            if speed_val is None:
                raise NotImplementedError
            result = speed_val.get_values()
        except NotImplementedError:
            result = UIValues()
            MY_LOGGER.debug(f'speed_range: {result}')
        return result

    def select_cache_speech(self):
        """
        TODO: Eliminate this special method for starting ui
        """
        try:
            cache_speech: bool = self.engine_cache_speech_radio_button.isSelected()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting cache_speech for {self.engine_key}'
                                f' to {cache_speech}')
            Settings.set_use_cache(cache_speech)
            self.engine_cache_speech_group.setVisible(True)
            # self.update_engine_values()
        except NotImplementedError:
            self.engine_cache_speech_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def select_player_mode(self):
        """
        Presents user with UI to change Player Mode and updates Settings and
        UI accordingly.
        :return:
        """
        clz = type(self)
        try:
            engine_key = self.engine_key
            player_key = Settings.get_player(engine_key)
            player_id: str = player_key.service_id
            player: PlayerType = PlayerType(player_id)
            choices: Choices
            choices, current_choice_index = self.cfg.get_player_mode_choices(engine_key,
                                                                             player)
            if current_choice_index < 0:
                current_choice_index = 0
            title: str = Messages.get_msg(Messages.SELECT_PLAYER_MODE)
            self.cfg.restore_settings(msg='select_player_mode BEFORE doModal')
            self.cfg.save_settings('select_player_mode BEFORE doModal')
            self.refresh_tts(capture_settings=True)
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           dialog_subject='PlayerMode',
                                           choices=choices,
                                           selection_index=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.cfg.restore_settings(msg='select_player AFTER doModal')

            idx = dialog.sel_data.chosen_idx
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'SelectionDialog value: '
                                  f'{PlayerMode.translated_name} '
                                  f'idx: {str(idx)}')
            if idx < 0:
                return None

            choice: Choice = choices[idx]
            prev_choice: Choice = choices[current_choice_index]
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'engine: {self.engine_key} new player mode:'
                                f' {choice.label}'
                                f' previous: {prev_choice.label} ')
            new_player_mode: PlayerMode = PlayerMode(choice.value)
            previous_player_mode: PlayerMode
            previous_player_mode = PlayerMode(prev_choice.value)

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'new_player_mode: {new_player_mode} type: '
                                f'{type(new_player_mode)}')
            if new_player_mode != previous_player_mode:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'setting player mode to: {new_player_mode}')
                self.set_player_mode_field(update_ui=True,
                                           engine_key=self.engine_key,
                                           player_mode=new_player_mode)
                self.refresh_tts()
        except Exception as e:
            MY_LOGGER.exception('')

    def set_engine_field(self,
                         update_ui: bool,
                         engine_key: ServiceID = None) -> None:
        """
        Saves the given engine_id in Settings. Optionally updates the UI
        engine and language names.

        :param update_ui: If True, then the UI is updated to reflect the
        service_key
        :param engine_key: If None, then service_key is populated with the current
        service_key from Settings.get_engine_key. Updates Settings with the value
        of service_key (yeah, it can just update Settings with the same service_key
        that it just read).
        :return:
        """
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        if update_ui:
            kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
                LangUtils.get_kodi_locale_info()
            kodi_lang: str
            kodi_locale: str
            locale_name: str
            kodi_language: langcodes.Language
            engine_name: str
            engine_name = engine_key.service_id
            lang_name: str = LangUtils.get_translated_language_name(kodi_language)
            self.engine_engine_value.setLabel(engine_name)

        # Start engine LAST, after everything is configured
        self.cfg.set_engine_field(engine_key)

    def select_api_key(self):
        """

        """
        try:
            api_key = self.engine_api_key_edit.getText()
            Settings.set_api_key(api_key)
        except Exception as e:
            MY_LOGGER.exception('')

    def select_defaults(self) -> None:
        """
        Configures TTS with reasonable Default values

        First, try to use GoogleTTS engine. If that fails,
        try eSpeak. Otherwise use the fallback
        :return:
        """
        clz = type(self)
        try:
            self.refresh_tts(capture_settings=True)
            # Make sure that Settings stack depth is the same as when this module
            # was entered (should be 2).
            self.cfg.restore_settings('enter select_defaults')
            choices, current_choice_index = self.cfg.get_engine_choices(
                    engine_key=self.engine_key)
            choices: EngineChoices
            if current_choice_index < 0:
                current_choice_index = 0
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'# choices: {len(choices)} current_choice_idx: '
                                f'{current_choice_index}')
            # The first engine listed should be the best available and universal
            # (GoogleTTS)
            idx = 0
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'SelectionDialog value: '
                                  f'{MessageId.TTS_ENGINE.get_msg()} '
                                  f'idx: {str(idx)}')
            if idx < 0:  # No selection made or CANCELED
                return

            choice: EngineChoice = choices[idx]
            if choice is not None:
                engine_config: EngineConfig
                engine_config= self.cfg.configure_engine(choice, save_as_current=True)
                engine_config.volume = 0.0
                engine_config.speed = 1.0
                self.set_all_engine_fields(engine_config=engine_config)
                self.refresh_tts()
        except Exception as e:
            MY_LOGGER.exception('')

    def set_player_field(self, update_ui: bool,
                         engine_key: ServiceID | None = None,
                         player: PlayerType | None = None) -> None:
        """
        Updates player.engine_id Settings and optionally the UI.

        :param update_ui: if True, then the UI is updated as well as Settings.
                          otherwise, Settings player will be updated.
        :param engine_key: identifies which engine the settings belong to. If
                          None, then the current engine is used
        :param player: identifies the player to set. If None, then
                       the current player for service_key will be 'updated'

        :return:
        """
        try:
            if update_ui is None:
                raise ValueError('update_ui must have a value')
            if engine_key is None:
                engine_key = Settings.get_engine_key()
            if player is None:
                player = PlayerType(Settings.get_player().service_id)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'player: {player}')
            else:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'orig player: {self.prev_player_key}')

            player_str: str = player.label
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting player to {player}')
            self.cfg.set_player_field(engine_key=engine_key, player=player)
            if update_ui:
                allow_cache: bool
                allow_cache = not (
                        Settings.get_player_mode(engine_key) == PlayerMode.ENGINE_SPEAK
                        or Settings.get_player(
                            engine_key).service_id == PlayerType.BUILT_IN_PLAYER)
                #  MY_LOGGER.debug(f'allow_cache: {allow_cache}')
                self.engine_cache_speech_group.setVisible(allow_cache)
                self.engine_cache_speech_radio_button.setVisible(allow_cache)
                self.engine_module_value.setVisible(False)
                self.engine_player_value.setLabel(player_str)
                self.engine_player_value.setVisible(True)
                self.engine_player_button.setVisible(True)
                self.engine_player_group.setVisible(True)
        except NotImplementedError:
            self.engine_player_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_module_field(self):
        """

        :return:
        """
        try:
            choices: List[Choice]
            choices, current_choice_index = self.cfg.get_module_choices(self.engine_key)
            if current_choice_index < 0:
                current_choice_index = 0
            if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                self.engine_module_value.setEnabled(False)
                self.engine_module_value.setLabel(
                        Messages.get_msg(Messages.UNKNOWN))
                return

            choice: Choice = choices[current_choice_index]
            self.engine_module_value.setLabel(choice.label)
            if len(choices) < 2:
                self.engine_module_value.setEnabled(False)
            else:
                self.engine_module_value.setEnabled(True)

            #  self.cfg.set_module_field(choice.value)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_player_mode_field(self, update_ui: bool,
                              engine_key: ServiceID | None = None,
                              player_mode: PlayerMode | None = None) -> None:
        """
        Updates player_mode.engine_id Settings and optionally the UI.

        :param update_ui: if True, then the UI is updated as well as Settings.
                          otherwise, Settings player will be updated.
        :param engine_key: identifies which engine the settings belong to. If
                          None, then the current engine is used
        :param player_mode: identifies the player_mode to set. If None, then
                          the current player_mode for engine_id will be 'updated'
        :return:
        """
        try:
            if engine_key is None:
                engine_key = Settings.get_engine_key()
            if player_mode is None:
                player_mode = Settings.get_player_mode(engine_key)
            player_mode_str: str = player_mode.translated_name
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting player mode to {player_mode_str}')

            self.cfg.set_player_mode_field(engine_key=engine_key,
                                           player_mode=player_mode)
            if update_ui:
                allow_cache: bool
                allow_cache = not (
                        Settings.get_player_mode(engine_key) == PlayerMode.ENGINE_SPEAK
                        or Settings.get_player(
                            engine_key).service_id == PlayerType.BUILT_IN_PLAYER)
                self.engine_cache_speech_group.setVisible(allow_cache)
                self.engine_cache_speech_radio_button.setVisible(allow_cache)
                self.engine_player_mode_label.setLabel(player_mode_str)
                self.engine_player_mode_button.setVisible(True)
                self.engine_player_mode_label.setVisible(True)
                self.engine_player_mode_group.setVisible(True)
        except NotImplementedError:
            self.engine_player_mode_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    '''
    def get_voice_label(self, engine_key: ServiceID | None = None,
                        voice_id: str | None = None) -> str:
        """
        Gets the label of the VoiceGroup object identified by the given parameters

        TODO: Merge with set_lang_field
        :param engine_key: Engine to get the voice for. If None, then the
                           current engine is used.
        :param locale: Locale to get the voice for. If None, then the engine's
                       language setting is used
        :param voice_id: Identifies the voice. If None, then the current voice
                         for the given engine is used.
        """
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        if voice_id is None:
            voice_id = Settings.get_e_voice(engine_key=engine_key)
        voice_uid: str = EngineVoice.get_uid(engine_key=engine_key,
                                             engine_voice=voice_id)
        voice: EngineVoice = EngineVoiceManager.get_eng_voice_by_uid(voice_uid)
        voice_name: str = voice.voice_label
        return voice_name
    '''

    def set_voice_field(self, update_ui: bool = False,
                        e_voice: EngineVoice | None = None) -> None:
        """
        Configures the voice UI field and update settings. No
        validation is performed

        :param update_ui: When True, update UI and Settings, otherwise just
                          update Settings
        :param e_voice: Value to set voice field to. If None, then
                             use value from settings.
        :return:
        """
        try:
            if e_voice is None:
                MY_LOGGER.debug(f'engine_voice is None')
                e_voice = EngineVoiceManager.get_e_voice()

            MY_LOGGER.debug(f'engine_voice: {e_voice}')
            lang_id: str | None = None
            if e_voice is None:
                e_voice = EngineVoiceManager.get_e_voice()
            self.cfg.set_voice_field(engine_voice=e_voice)
            if update_ui:
                voice_name: str = e_voice.full_voice_label(with_group=True)
                visible: bool = lang_id != SettingProp.UNKNOWN_VALUE
                self.engine_voice_group.setVisible(visible)
                self.engine_voice_value.setEnabled(visible)
                self.engine_voice_value.setLabel(voice_name)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'voice_name: {voice_name} visible: {visible}')
        except Exception as e:
            MY_LOGGER.exception('')

    def set_cache_speech_field(self, update_ui: bool,
                               engine_key: ServiceID | None = None,
                               use_cache: bool | None = None) -> None:
        """
        Propagates cache_speech setting to Settings and the UI

        Settings for Engine, player and player_mode MUST all be set prior to
        calling this method to update the UI, since those settings control
        whether caching is an option.

        :param update_ui: If True, update the UI as well as Settings, otherwise,
                          only update Settings
        :param engine_key: Specifies the service_key to update. If None, then the
                          current Settings.service_key will be used
        :param use_cache: Specifies whether the engine is using a cache. If None,
                          then the current Settings.use_cache.engine_id value will
                          be used
        """
        try:
            if engine_key is None:
                engine_key = self.engine_key
            if use_cache is None:
                use_cache = Settings.is_use_cache(engine_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'engine_key: {engine_key} '
                                f'update_ui: {update_ui} player_mode: '
                                f'{Settings.get_player_mode(engine_key)} '
                                f'player_type: '
                                f'{Settings.get_player(engine_key).service_id} '
                                f'use_cache: {use_cache}')
            if update_ui:
                allow_cache: bool
                allow_cache = not (
                    Settings.get_player_mode(engine_key) == PlayerMode.ENGINE_SPEAK
                    or Settings.get_player(engine_key).service_id == PlayerType.BUILT_IN_PLAYER)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'allow_cache: {allow_cache}')
                self.engine_cache_speech_group.setVisible(allow_cache)
                self.engine_cache_speech_radio_button.setVisible(allow_cache)
                self.cfg.set_cache_speech_field(engine_key=engine_key,
                                                use_cache=use_cache)
                self.engine_cache_speech_radio_button.setSelected(use_cache)
        except NotImplementedError:
            self.engine_cache_speech_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_pitch_field(self, update_ui: bool,
                        engine_key: ServiceID,
                        pitch: float) -> None:
        """
        Updates Settings.pitch and optionally the pitch UI.

        :param update_ui: If True, then update the pitch related UI elements
        :param engine_key: Identifies the engine which to update the pitch
        :param pitch: value to set
        :return:
        """
        if update_ui:
            if True or not SettingsMap.is_valid_setting(engine_key.with_prop(
                                                        SettingProp.PITCH)):
                self.engine_pitch_group.setVisible(False)
            else:
                self.cfg.set_pitch_field(engine_key=engine_key, pitch=pitch)
                label: str = MessageId.PITCH.get_formatted_msg(f'{pitch:.1f}')
                self.engine_pitch_label.setLabel(label)
                self.engine_pitch_group.setVisible(True)

    def set_gender_field(self, update_ui: bool, engine_key: ServiceID):
        """
        Sets the given engine's Gender field, if it has one. Also, updates
        the UI if requested.
        :param update_ui: If true, and this engine supports gender, then the UI
               will be updated to reflect the current gender
        :param engine_key: Identifies which engine's settings to work with

        Note that the current gender is calculated by choices made from selecting
        the voice (SUBJECT TO CHANGE). NOTHING IS ACTUALLY SAVED.
        :return:
        """
        try:
            choices: List[Choice]
            valid: bool = SettingsMap.is_valid_setting(engine_key.with_prop(
                                                       SettingProp.GENDER))
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'setting_id: {engine_key} GENDER valid: {valid}')
            if update_ui:
                if not valid:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Gender is not a valid property for '
                                        f'{engine_key}')
                    self.engine_gender_group.setVisible(False)
            else:
                choices, current_choice_index = self.cfg.get_gender_choices(
                        engine_key)
                if current_choice_index < 0:
                    current_choice_index = 0
                if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                    self.engine_gender_value.setEnabled(False)
                    self.engine_gender_value.setLabel(
                            Messages.get_msg(Messages.UNKNOWN))
                    return
                choice: Choice = choices[current_choice_index]
                self.engine_gender_value.setLabel(choice.label)
                if len(choices) < 2:
                    self.engine_gender_value.setEnabled(False)
                    self.engine_gender_button.setEnabled(False)
                else:
                    self.engine_gender_value.setEnabled(True)
                    self.engine_gender_button.setEnabled(True)
                self.engine_gender_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_api_field(self, engine_key: ServiceID) -> None:
        """
            TODO: This is largely a no-op
        """
        try:
            if not SettingsMap.is_setting_available(engine_key,
                                                    SettingProp.API_KEY):
                self.engine_api_key_group.setVisible(False)
                return

            if (SettingsMap.get_validator(engine_key) is not
                    None):
                self.cfg.set_api_field(engine_key=engine_key)
                api_key: str = Settings.get_api_key(engine_key)
                #  self.engine_api_key_edit.setText(api_key)
                self.engine_api_key_edit.setLabel(
                        Messages.get_msg(Messages.ENTER_API_KEY))
                self.engine_api_key_group.setVisible(True)
            else:
                self.engine_api_key_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def refresh_tts(self, capture_settings: bool = False):
        """
        Initiate the rapid adoption of changes so that the user gets fast feedback.
        Called AFTER changes are applied. More or less add a call to this everywhere
        a user changes a setting. Fortunately the code is already designed to apply
        changes in this manner.

        This method is called twice: Once, with capture_settings=True to save
        the state of settings BEFORE changes are made. Second, without arguments
        causing the services using the old settings to be stopped/reset.
        """
        if capture_settings:
            self.prev_engine_key = self.engine_key
            self.prev_player_key = Settings.get_player(self.engine_key)
            self.prev_player_mode = Settings.get_player_mode(self.engine_key)
            MY_LOGGER.debug(f'engine_key: {self.engine_key}\n'
                            f'player_key: {self.prev_player_key}\n'
                            f'player_mode: {self.prev_player_mode}')
            return
        self.cfg.refresh_tts(prev_engine_key=self.prev_engine_key,
                             prev_player_key=self.prev_player_key,
                             prev_player_mode=self.prev_player_mode)
        return

    def selection_dialog(self,
                         title: str,
                         dialog_subject: str,
                         choices: Choices,
                         selection_index: int | str,  # Index or key
                         sub_title: str | None = None,
                         call_on_focus:
                         Callable[[Choice | EngineChoice | VoiceChoice |
                                   VGChoice, int],
                                  None] | None = None,
                         call_on_select:
                         Callable[[Choice | EngineChoice | VoiceChoice |
                                   VGChoice, int],
                                  int] | None = None,
                         disable_tts: bool = False) -> SelectionDialog:
        """
        Wraps the SelectionDialog so that the single instance can be shared.

        :param title:  Heading for the dialog
        :param dialog_subject: Tags the data to help the code determine what
                               it is working on at the moment (ex: VGroups or VoiceGroups)
        :param choices:  List of available choices to present
        :param selection_index:  Index of the current choice in choices, OR it
                                is a key to identify a voice and the group it belongs.
        :param sub_title:  Optional Sub-Heading for the dialog
        :param call_on_focus:  Optional call-back function for on-focus events
                               useful for hearing the difference immediately
        :param call_on_select: Optional call-back function for on-click events
                               useful for voicing the selected item immediately
        :param disable_tts:
        :return: Returns the underlying SelectionDialog so that methods can be
                 called such as doModal

        Note: Any changes made in SettingsDialog are either committed or undone
        on exit. OK commits the changes in Settings to settings.xml.
        Cancel reverts all changes in Settings from a backup-copy.

        Reverting live changes without Cancelling SettingsDialog requires care.
        """
        clz = type(self)
        if clz._selection_dialog is None:
            script_path: Path = Constants.ADDON_PATH
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(
                        f'SelectionDialog ADDON_PATH: {Constants.ADDON_PATH}')
            clz._selection_dialog = SelectionDialog('selection-dialog.xml',
                                                    str(script_path), 'Custom',
                                                    defaultRes='1080i',
                                                    title=title,
                                                    dialog_subject=dialog_subject,
                                                    choices=choices,
                                                    selection_index=selection_index,
                                                    sub_title=sub_title,
                                                    call_on_focus=call_on_focus,
                                                    call_on_select=call_on_select,
                                                    voice_the_voice=self.voice_the_voice,
                                                    disable_tts=disable_tts)

        clz._selection_dialog.update_data(title=title,
                                          dialog_subject=dialog_subject,
                                          choices=choices,
                                          selection_index=selection_index,
                                          sub_title=sub_title,
                                          call_on_focus=call_on_focus,
                                          call_on_select=call_on_select,
                                          disable_tts=disable_tts)
        return clz._selection_dialog

    def get_language(self, label=False) -> str:
        """
        Gets the translated, currently configured language variant for the
        current engine

        :return:
        """
        clz = type(self)
        try:
            language = Settings.get_language(self.engine_key)
            if language is None:
                _, default_setting = self.cfg.getEngineInstance().settingList(
                        SettingProp.LANGUAGE)
                language = default_setting
        except Exception as e:
            MY_LOGGER.exception('')
            language = get_language_code()
        lang: str = language
        if label:
            lang = SettingsHelper.get_formatted_lang(lang)
        return lang
