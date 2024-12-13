# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import langcodes
import xbmc
import xbmcaddon
import xbmcgui
from xbmcgui import (ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider)

from backends.settings.language_info import LanguageInfo
from backends.settings.service_types import GENERATE_BACKUP_SPEECH
from backends.settings.settings_helper import FormatType, SettingsHelper
from backends.settings.validators import (AllowedValue, BoolValidator, NumericValidator,
                                          StringValidator, TTSNumericValidator, Validator)
from common import *

from backends.backend_info import BackendInfo
from backends.base import *
from backends.settings.i_validators import (IBoolValidator, IConstraintsValidator,
                                            IConstraints,
                                            INumericValidator, IStringValidator, UIValues)
from backends.settings.settings_map import SettingsMap
from common.constants import Constants
from common.lang_phrases import SampleLangPhrases
from common.logger import *
from common.message_ids import MessageId, MessageUtils
from common.messages import Message, Messages
from common.setting_constants import (AudioType, Backends, Genders, GenderSettingsMap,
                                      Players)
from common.settings import Settings
from common.settings_low_level import SettingsLowLevel
from utils import util
from utils.util import get_language_code
from windowNavigation.action_map import Action
from windowNavigation.choice import Choice
from windowNavigation.selection_dialog import SelectionDialog

MY_LOGGER = BasicLogger.get_logger(__name__)


class SettingsDialog(xbmcgui.WindowXMLDialog):
    HEADER_LABEL: Final[int] = 1
    BASIC_CONFIG_LABEL: Final[int] = 2
    # ENGINE_TAB: Final[int] = 100
    # OPTIONS_TAB: Final[int] = 200
    # KEYMAP_TAB: Final[int] = 300
    # ADVANCED_TAB: Final[int] = 400
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
    SELECT_VOICE_GROUP: Final[int] = 1106
    SELECT_VOICE_BUTTON: Final[int] = 106
    SELECT_VOICE_VALUE_LABEL: Final[int] = 107
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

    POP_SETTING_STACK_FOR_EXIT: int = 0
    POP_SETTING_STACK_FOR_CONFIG: int = 1

    _selection_dialog: SelectionDialog | None = None

    def __init__(self, *args, **kwargs) -> None:
        """

        :param args:
        """
        # xbmc.executebuiltin('Skin.ToggleDebug')

        Monitor.register_abort_listener(self.on_abort_requested)

        self.closing = False
        self._initialized: bool = False
        self.is_modal: bool = False
        # Makes sure that Settings stack is restored to same depth as
        # when entered. Required due to exit being user input and
        # asynchronous
        self.settings_pushes: int = 0
        # Tracks duplicate calls to onInit. Reset in doModal
        self.init_count: int = 0
        self.exit_dialog: bool = False
        super().__init__(*args)
        #  self.api_key = None
        self.engine_instance: ITTSBackendBase | None = None
        # self.backend_changed: bool = False
        # self.gender_id: int | None = None
        # self.language: str | None = None
        # elf.pitch: float | None = None
        # elf.player: str | None = None
        # elf.player_mode: str | None = None
        # self.module: str | None = None
        # self.speed: float | None = None
        # self.volume: int | None = None
        # self.settings_changed: bool = False
        # self.previous_engine: str | None = None
        # self.previous_player_mode: PlayerMode | None = None
        initial_backend = SettingsLowLevel.getSetting(SettingsProperties.ENGINE,
                                                      None,
                                                      SettingsProperties.ENGINE_DEFAULT)

        if initial_backend == SettingsProperties.ENGINE_DEFAULT:  # 'auto'
            initial_backend = BackendInfo.getAvailableBackends()[0].engine_id
        self.getEngineInstance(engine_id=initial_backend)

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
        self.engine_language_group: ControlGroup | None = None
        self.engine_language_button: ControlButton | None = None
        self.engine_language_value = None
        self.engine_voice_group: ControlGroup | None = None
        self.engine_voice_button: ControlButton | None = None
        self.engine_voice_value = None
        self.engine_gender_group: ControlGroup | None = None
        self.engine_gender_button: ControlButton | None = None
        self.engine_gender_value = None
        self.engine_pitch_group: ControlGroup | None = None
        self.engine_pitch_slider: ControlSlider | None = None
        self.engine_pitch_label: ControlLabel | None = None
        self.engine_player_group: ControlGroup | None = None
        self.engine_player_button: ControlButton | None = None
        self.engine_player_value = None  # player and module
        self.engine_module_value = None  # share button and real-estate
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
        self.saved_choices: List[Choice] | None = None
        self.saved_selection_index: int | None = None

        # Ensure some structures are built before we need them.
        SettingsHelper.build_allowed_player_modes()

    def re_init(self) -> None:
        MY_LOGGER.debug(f'In re-init')
        return
        self.init_count += 1  # There can be multiple onInit calls before show
        self.closing = False
        self._initialized = False
        self.exit_dialog = False
        # self.api_key = None
        self.engine_instance = None
        # self.backend_changed = False
        # self.gender_id = None
        # self.language = None
        # self.pitch = None
        # self.player = None
        # self.player_mode = None
        # self.module = None
        # self.speed = None
        # self.volume = None
        # self.settings_changed = False
        # self.previous_engine = None
        # self.previous_player_mode: PlayerMode | None = None
        """
        initial_backend = Settings.getSetting(SettingsProperties.ENGINE,
                                              self.service_id,
                                              SettingsProperties.ENGINE_DEFAULT)

        if initial_backend == SettingsProperties.ENGINE_DEFAULT:  # 'auto'
            initial_backend = BackendInfo.getAvailableBackends()[0].service_id
            self.set_engine_id(initial_backend)
        else:
            self.getEngineInstance(service_id=initial_backend)
        """

        MY_LOGGER.debug_xv('SettingsDialog.re_init')
        self.header = None
        self.basic_config_label = None
        # self.engine_tab: ControlRadioButton | None = None
        # self.options_tab: ControlButton | None = None
        # self.keymap_tab: ControlButton | None = None
        # self.advanced_tab: ControlButton | None = None
        # self.engine_group: ControlGroup | None = None
        # self.options_group: ControlGroup | None = None
        # self.keymap_group: ControlGroup | None = None
        # self.advanced_group: ControlGroup | None = None
        self.ok_button = None
        self.cancel_button = None
        self.defaults_button = None
        self.engine_api_key_group = None
        self.engine_api_key_edit = None
        self.engine_api_key_label = None
        self.engine_engine_button = None
        self.engine_engine_value = None
        self.engine_language_group = None
        self.engine_language_button = None
        self.engine_language_value = None
        self.engine_voice_group = None
        self.engine_voice_button = None
        self.engine_voice_value = None
        self.engine_gender_group = None
        self.engine_gender_button = None
        self.engine_gender_value = None
        self.engine_pitch_group = None
        self.engine_pitch_slider = None
        self.engine_pitch_label = None
        self.engine_player_group = None
        self.engine_player_button = None
        self.engine_player_value = None
        self.engine_module_value = None
        self.engine_pipe_audio_group = None
        self.engine_player_mode_group = None
        self.engine_pipe_audio_radio_button = None
        self.engine_player_mode_button = None
        self.engine_player_mode_label = None
        self.engine_speed_group = None
        self.engine_speed_slider = None
        self.engine_speed_label = None
        self.engine_cache_speech_group = None
        self.engine_cache_speech_radio_button = None
        self.engine_volume_group = None
        self.engine_volume_slider = None
        self.engine_volume_label = None
        # self.options_dummy_button = None
        # self.keymap_dummy_button = None
        # self.advanced_dummy_button = None
        self.saved_choices = None
        self.saved_selection_index = None


    def onInit(self) -> None:
        """

        :return:
        """
        #  super().onInit()
        clz = type(self)
        MY_LOGGER.debug_v('SettingsDialog.onInit')
        self.re_init()

        try:
            if not self._initialized:
                self.header = self.get_control_label(clz.HEADER_LABEL)
                addon_id = xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('id')
                addon_name = xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('id')
                self.header.setLabel(f'{Messages.get_msg(Messages.SETTINGS)} '
                                     f'- {addon_name}')
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
                        clz.OK_BUTTON)
                self.ok_button.setLabel(MessageId.OK_BUTTON.get_msg())
                self.ok_button.setVisible(True)

                self.cancel_button = self.get_control_button(
                        clz.CANCEL_BUTTON)
                self.cancel_button.setLabel(MessageId.CANCEL_BUTTON.get_msg())
                self.cancel_button.setVisible(True)

                self.defaults_button: ControlButton = self.get_control_button(
                        clz.DEFAULTS_BUTTON)
                self.defaults_button.setLabel(MessageId.DEFAULTS_BUTTON.get_msg())
                self.defaults_button.setVisible(True)

                # self.engine_group = self.get_control_group(clz.ENGINE_GROUP_LIST)
                # self.engine_group.setVisible(True)

                self.basic_config_label = self.get_control_label(clz.BASIC_CONFIG_LABEL)
                self.basic_config_label.setLabel(MessageId.BASIC_CONFIGURATION.get_msg())
                self.basic_config_label.setVisible(True)

                self.engine_engine_button = self.get_control_button(
                        clz.SELECT_ENGINE_BUTTON)

                self.engine_engine_value = self.get_control_label(
                        clz.SELECT_ENGINE_VALUE_LABEL)
                engine_label: str = Backends.get_label(self.engine_id)
                self.engine_engine_value.setLabel(engine_label)

                engine_voice_id: str = Settings.get_voice(self.engine_id)
                MY_LOGGER.debug(f'service_id: {self.engine_id} '
                                f'engine_voice_id: {engine_voice_id}')
                lang_info = LanguageInfo.get_entry(engine_id=self.engine_id,
                                                   engine_voice_id=engine_voice_id,
                                                   lang_id=None)
                MY_LOGGER.debug(f'lang_info: {lang_info}')
                lang_info: LanguageInfo
                kodi_language: langcodes.Language
                _, _, _, kodi_language = LanguageInfo.get_kodi_locale_info()
                voice_str: str
                voice_str = SettingsHelper.get_formatted_label(
                        lang_info,
                        kodi_language=kodi_language,
                        format_type=FormatType.DISPLAY)
                self.engine_engine_button.setLabel(MessageId.ENGINE_LABEL.get_msg())
                """
                This is a MESS. engine_language_group is really for selecting
                the engine's voice. (see where the language_button is 
                labeled as VOICE). What makes matters worse, is that
                the original engine_voice_group is used when 'voice is
                available' when it likely is not.
                
                The truth is that language and voice are very closely related.
                Language is a broad term ('en'). There are different
                accents in different countries. A person's voice has a language
                and accent. When there are few 'personal voices' then TTS 
                will lump them together with language variations (en-us.nancy).
                If there a many, then use multi-stage selection. Pick the 
                language/country (en-us) then use another 'voice' button to
                choose the specific voice. For now, it is ignored.
                """
                self.engine_language_group = self.get_control_group(
                        clz.SELECT_LANGUAGE_GROUP)
                self.engine_language_button: ControlButton = self.get_control_button(
                        clz.SELECT_LANGUAGE_BUTTON)
                self.engine_language_button.setLabel(
                        MessageId.LANG_VARIANT_BUTTON.get_msg())

                self.engine_language_value = self.get_control_label(
                        clz.SELECT_LANGUAGE_VALUE_LABEL)

                self.refresh_engine_language_value()

                self.engine_voice_group = self.get_control_group(
                        clz.SELECT_VOICE_GROUP)
                avail: bool = SettingsMap.is_setting_available(self.engine_id,
                                                               SettingsProperties.VOICE)
                MY_LOGGER.debug(f'is voice available: {avail}')
                valid: bool = SettingsMap.is_valid_property(self.engine_id,
                                                            SettingsProperties.VOICE)
                MY_LOGGER.debug(f'is voice valid: {valid}')
                if not SettingsMap.is_valid_property(self.engine_id,
                                                     SettingsProperties.VOICE):
                    self.engine_voice_group.setVisible(False)
                else:
                    self.engine_voice_button: ControlButton = self.get_control_button(
                            clz.SELECT_VOICE_BUTTON)
                    self.engine_voice_button.setLabel(
                            MessageId.SELECT_VOICE_BUTTON.get_msg())
                    self.engine_voice_value = self.get_control_label(
                            clz.SELECT_VOICE_VALUE_LABEL)
                    self.engine_voice_group.setVisible(True)
                    self.engine_voice_value.setLabel(self.get_language(label=True))
                    MY_LOGGER.debug(f'engine_voice_value: '
                                    f'{self.engine_voice_value.getLabel()}')

                self.engine_gender_group = self.get_control_group(
                        clz.SELECT_GENDER_GROUP)
                if not SettingsMap.is_valid_property(self.engine_id,
                                                     SettingsProperties.GENDER):
                    self.engine_gender_group.setVisible(False)
                else:
                    self.engine_gender_button: ControlButton = self.get_control_button(
                            clz.SELECT_GENDER_BUTTON)
                    self.engine_gender_button.setLabel(
                            Messages.get_msg(Messages.SELECT_VOICE_GENDER))
                    self.engine_gender_value: ControlLabel = self.get_control_label(
                            clz.SELECT_GENDER_VALUE_LABEL)
                    try:
                        gender: Genders = Settings.get_gender(self.engine_id)
                        self.engine_gender_value.setLabel(gender.name)
                        self.engine_gender_group.setVisible(True)
                    except AbortException:
                        reraise(*sys.exc_info())
                    except Exception as e:
                        MY_LOGGER.exception('')

                self.engine_pitch_group = self.get_control_group(
                        clz.SELECT_PITCH_GROUP)
                if not SettingsMap.is_valid_property(self.engine_id,
                                                     SettingsProperties.PITCH):
                    self.engine_pitch_group.setVisible(False)
                else:
                    self.engine_pitch_label = self.get_control_label(
                            clz.SELECT_PITCH_LABEL)
                    self.engine_pitch_label.setLabel(
                            Messages.get_msg(Messages.SELECT_PITCH))
                    self.engine_pitch_slider = self.get_control_slider(
                            clz.SELECT_PITCH_SLIDER)
                    self.engine_pitch_group.setVisible(True)

                # NOTE: player and module share control. Only one active at a
                #       time. Probably should create two distinct buttons and
                #       control visibility

                self.engine_player_group = self.get_control_group(
                        clz.SELECT_PLAYER_GROUP)
                self.engine_player_group.setVisible(False)
                self.engine_player_button = self.get_control_button(
                        clz.SELECT_PLAYER_BUTTON)

                #   TODO:   !!!!!
                # Move to where player or module are about to be displayed

                if SettingsMap.is_valid_property(self.engine_id,
                                                 SettingsProperties.PLAYER):
                    self.engine_player_button.setLabel(
                            MessageId.SELECT_PLAYER.get_msg())
                    self.engine_player_value = self.get_control_button(
                            clz.SELECT_PLAYER_VALUE_LABEL)
                    self.engine_player_value.setLabel(Settings.get_player_id())
                    self.engine_player_value.setVisible(True)
                else:
                    self.engine_player_button.setLabel(
                            Messages.get_msg(Messages.SELECT_MODULE))
                    self.engine_module_value = self.get_control_button(
                            clz.SELECT_PLAYER_VALUE_LABEL)
                    self.engine_module_value.setLabel(self.get_module())
                    self.engine_module_value.setVisible(True)

                self.engine_player_group.setVisible(True)
                self.engine_player_button.setVisible(True)

                self.engine_cache_speech_group = self.get_control_group(
                        clz.SELECT_CACHE_GROUP)
                self.engine_cache_speech_radio_button = \
                    self.get_control_radio_button(
                            clz.SELECT_CACHE_BUTTON)
                self.engine_cache_speech_radio_button.setLabel(
                        Messages.get_msg(Messages.CACHE_SPEECH))

                self.engine_player_mode_group = self.get_control_group(
                        clz.SELECT_PLAYER_MODE_GROUP)
                self.engine_player_mode_button = \
                    self.get_control_button(
                            clz.SELECT_PLAYER_MODE_BUTTON)
                self.engine_player_mode_button.setLabel(
                        Messages.get_msg_by_id(32336))
                MY_LOGGER.debug(f'player_mode_button label: '
                                f'{Messages.get_msg_by_id(32336)}')
                MY_LOGGER.debug(f'player_mode button label: '
                                f'{Messages.get_msg(Messages.PLAYER_MODE)}')
                MY_LOGGER.debug(f'player_mode button label: '
                                f'{xbmc.getLocalizedString(32336)}')
                MY_LOGGER.debug(f'player_mode button label: '
                                f'{xbmcaddon.Addon().getLocalizedString(32336)}')
                self.engine_player_mode_label = self.get_control_label(
                        clz.SELECT_PLAYER_MODE_LABEL_VALUE)

                self.engine_api_key_group = self.get_control_group(
                        clz.SELECT_API_KEY_GROUP)
                self.engine_api_key_edit = self.get_control_edit(
                        clz.SELECT_API_KEY_EDIT)
                # self.engine_api_key_label = self.get_control_label(
                #         clz.SELECT_API_KEY_LABEL)
                # self.engine_api_key_label.setLabel(util.T(32233))
                # self.engine_api_key_edit.setLabel(
                #         Messages.get_msg(Messages.API_KEY))

                self.engine_speed_group = self.get_control_group(
                        clz.SELECT_SPEED_GROUP)
                self.engine_speed_label = self.get_control_label(
                        clz.SELECT_SPEED_LABEL)
                speed: float = Settings.get_speed()
                self.engine_speed_label.setLabel(
                        Messages.get_formatted_msg(Messages.SELECT_SPEED,
                                                   f'{speed:.1f}'))
                self.engine_speed_slider = self.get_control_slider(
                        clz.SELECT_SPEED_SLIDER)

                self.engine_volume_group = self.get_control_group(
                        clz.SELECT_VOLUME_GROUP)
                self.engine_volume_label = self.get_control_label(
                        clz.SELECT_VOLUME_LABEL)
                result: UIValues = self.get_volume_range()
                self.engine_volume_label.setLabel(
                        MessageId.VOLUME_DB.get_formatted_msg(result.current))
                #        Messages.get_formatted_msg(Messages.VOLUME_DB,
                #                                     result.current))
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
                self.update_engine_values()

                self._initialized = True
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
            self.set_language_field()
            self.set_voice_field()
            # self.set_gender_field() # Not that useful at this time.
            # Player and player_mode are inter-dependent
            # Speed, volume and pitch are also closely related to player, but not as
            # much as player/player-mode
            self.set_player_mode_field()
            if SettingsMap.is_valid_property(self.engine_id, SettingsProperties.PLAYER):
                self.set_player_field()
            elif SettingsMap.is_valid_property(self.engine_id, SettingsProperties.MODULE):
                self.set_module_field()
            self.set_pitch_range()
            self.set_speed_range()
            self.set_volume_range()
            self.set_api_field()
            # self.set_pipe_audio_field()
            self.set_cache_speech_field()
            # TTSService.onSettingsChanged()
        except Exception as e:
            MY_LOGGER.exception('')

    def doModal(self) -> None:
        """

        :return:
        """
        # About to go modal
        # Save ALL settings on settings stack,
        # They will be discarded on exit at doModal
        # User can explicitly commit them at any time
        self.save_settings()
        self.is_modal = True
        super().doModal()
        self.is_modal = False
        # All changes discarded unless explicitly committed sooner
        # reset_settings makes sure the Settings stack is at the same depth
        # as when we entered.
        self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_EXIT)
        return

    def show(self) -> None:
        """

        :return:
        """
        #  MY_LOGGER.debug('SettingsDialog.show')
        # Save ALL settings on settings stack,
        # They will be discarded on exit at doModal
        # User can explicitly commit them at any time
        self.save_settings()
        super().show()
        # All changes discarded unless explicitly committed sooner
        # reset_settings makes sure the Settings stack is at the same depth
        # as when we entered.
        self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_EXIT)

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

            if MY_LOGGER.isEnabledFor(DEBUG):
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

                MY_LOGGER.debug(f'action_id: {action_id}')
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
        MY_LOGGER.debug(f'onClick:{controlId} closing: {self.closing}')
        if self.closing:
            return

        try:
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

            elif controlId == 28:
                # OK button
                self.closing = True
                self.commit_settings()
                # MY_LOGGER.info(f'ok button closing')
                self.close()

            elif controlId == 29:
                # Cancel button
                # MY_LOGGER.debug(f'cancel button')
                self.closing = True
                #  self.restore_settings()
                self.close()

            elif controlId == self.DEFAULTS_BUTTON:
                MY_LOGGER.debug(f'defaults button')
                # TODO: complete

        except Exception as e:
            MY_LOGGER.exception('')

    def on_abort_requested(self):
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
            elif controlId == clz.SELECT_LANGUAGE_BUTTON:
                self.select_language()
            elif controlId == clz.SELECT_VOICE_BUTTON:
                self.select_voice()
            elif controlId == clz.SELECT_GENDER_BUTTON:
                self.select_gender()
            elif controlId == clz.SELECT_PITCH_SLIDER:
                self.select_pitch()
            elif controlId == clz.SELECT_PLAYER_BUTTON:
                if SettingsMap.is_valid_property(self.engine_id,
                                                 SettingsProperties.PLAYER):
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

    '''
    def set_engine(self):
        """
            NOT CURRENTLY CALLED.

            Meant to be called when any setting changes so that any is_required
            changes (perhaps conflicts) can be fixed here.
        """
        try:
            choices: List[Choice]
            current_choice_index: int
            choices, current_choice_index = self.get_engine_choices()
            choice: Choice = choices[current_choice_index]
            self.engine_engine_value.setLabel(choice.label)
            if len(choices) < 2:
                self.engine_engine_value.setEnabled(False)
            else:
                self.engine_engine_value.setEnabled(True)

            self.set_engine_id(choice.value)
        except Exception as e:
            MY_LOGGER.exception('')
    '''

    def get_engine_choices(self) -> Tuple[List[Choice], int]:
        """
            Generates a list of choices for TTS engine that
            can be used by select_engine.

            The choices will be based on the engines which are
            capable of voicing the current Kodi locale and sorted by
            the best langauge match score for each engine.

        :return: A list of all the choices as well as an index to the
                 current engine
        """
        try:
            MY_LOGGER.debug('FOOO get_engine_choices')
            _, _, _, kodi_language = LanguageInfo.get_kodi_locale_info()
            kodi_language: langcodes.Language
            current_engine_idx: int = -1
            choices: List[Choice]
            choices, current_engine_idx = SettingsHelper.get_engines_supporting_lang(
                    self.engine_id)
            idx: int = 0
            for choice in choices:
                choice: Choice
                choice.label = SettingsHelper.get_formatted_label(
                        choice.lang_info,
                        kodi_language=kodi_language,
                        format_type=FormatType.DISPLAY)
                choice.hint = f'choice {idx}'
                idx += 1
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'choices: {choices}')
            self.save_current_choices(choices, current_engine_idx)
            # auto_choice_label: str = Messages.get_msg(Messages.AUTO)
            # current_value = Settings.get_engine_id()
            return choices, current_engine_idx
        except Exception as e:
            MY_LOGGER.exception('')

    def save_current_choices(self, choices: List[Choice], selection_index: int) -> None:
        """
        Simple mechanism to save SelectionDialog's list of choices as well
        as selected index. Used to save results beteween calls. Should change
        to something a bit less crude.

        Use retrieve_current_choices to, um, retrieve the values

        :param choices: List[Choice] choices presented to user
        :param selection_index: Index into choices indicating what user chose
        :return:
        """
        self.saved_choices = choices
        self.saved_selection_index = selection_index

    def retrieve_current_choices(self) -> Tuple[List[Choice], int]:
        """
           Simple mechanism to retrieve SelectionDialog's list of choices as well
           as selected index. Used to save results beteween calls. Should change
           to something a bit less crude.

           Use save_current_choices to, um, retrieve the values
           :return:
           """
        return self.saved_choices, self.saved_selection_index

    def select_engine(self):
        """
            Displays the SelectionDialog for the user to choose the desired
            engine. Also makes the needed changes if the user modifies and saves
            their changes

        :return:
        """
        try:
            MY_LOGGER.debug(f'FOOO select_engine current: {self.engine_id}'
                            f' {Settings.get_engine_id()}')
            self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_CONFIG)
            MY_LOGGER.debug(f'After reset: {Settings.get_engine_id()}')
            self.save_settings()
            MY_LOGGER.debug(f'After save: {Settings.get_engine_id()}')
            choices, current_choice_index = self.get_engine_choices()
            choices: List[Choice]
            if current_choice_index < 0:
                current_choice_index = 0
            MY_LOGGER.debug(f'# choices: {len(choices)} current_choice_idx: '
                            f'{current_choice_index}')
            # self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_CONFIG)
            # self.save_settings()
            MY_LOGGER.debug(f'sub_title: {MessageId.SELECT_TTS_ENGINE.get_msg()}')
            dialog: SelectionDialog
            dialog = self.selection_dialog(
                    title=MessageId.CHOOSE_TTS_ENGINE.get_msg(),
                    sub_title=MessageId.SELECT_TTS_ENGINE.get_msg(),
                    choices=choices,
                    initial_choice=current_choice_index,
                    call_on_focus=self.voice_engine)
            # xbmc.executebuiltin(function=f'control.setHidden(101)', wait=False)
            dialog.doModal()
            """
            At this point the user has either chosen to cancel configuring the 
            engine settings by using the BACK button, or similar to return from
            SelectionDialog.
            OR the user exited the SelectionDialog by selecting a configuration.
            In this case the user wants to keep those changes with the opportunity
            to configure other settings. 
            """
            MY_LOGGER.debug(f'speed should be 1.0: {Settings.get_speed()}')
            # Revert all changes made during SelectionDialog
            self.restore_settings()  # resets settings prior to SelectionDialog
            MY_LOGGER.debug(f'speed should be 1.5: {Settings.get_speed()}')
            # Get selected index
            idx = dialog.close_selected_idx
            MY_LOGGER.debug_v(f'SelectionDialog value: '
                              f'{MessageId.TTS_ENGINE.get_msg()} '
                              f'idx: {str(idx)}')
            if idx < 0:  # No selection made or CANCELED
                return

            # User wants to keep the changes made during selection. The settings have
            # already been reverted to prior to configuring for SelectionDialog.
            # Re-apply those changes.

            choice: Choice = choices[idx]
            if choice is not None:
                engine_id: str = choice.engine_id
                if engine_id is not None:
                    from service_worker import TTSService

                    current_engine_id: str = TTSService.get_instance().tts.engine_id
                    if current_engine_id != engine_id:
                        PhraseList.set_current_expired()  # Changing engines

                lang_info: LanguageInfo = choice.lang_info
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'lang_info: {lang_info}')
                if lang_info is not None:
                    # MY_LOGGER.debug(f'{phrases}')
                    Settings.set_language(lang_info.engine_lang_id,
                                          engine_id=engine_id)
                    voice: str = lang_info.engine_voice_id
                    # voice_name: str = lang_info.translated_voice
                    # engine_name: str = lang_info.translated_engine_name
                    #  text: str = (f'{engine_name} speaking in {language} using voice '
                    #               f'{voice}')
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'engine: {engine_id} voice: {voice}')
                    Settings.set_voice(voice, engine_id=engine_id)

                    #  TODO: Undo- FORCE player and player mode for now
                    target_audio: AudioType = AudioType.MP3
                    player_mode: PlayerMode = PlayerMode.SLAVE_FILE
                    player: str = Players.MPV
                    #
                    # This HACK provides a means to provide a limited set of
                    # audio messages that is shipped with the addon. These
                    # messages are used when either no engine or no player can
                    # be configured. These messages are voiced using Kodi SFX
                    # internal player. The messages should help the user install/
                    # configure an engine or player. See:
                    # GENERATE_BACKUP_SPEECH, sfx_audio_player, no_engine and voicecache

                    if GENERATE_BACKUP_SPEECH:
                        target_audio = AudioType.WAV
                        player_mode = PlayerMode.FILE
                        player = Players.SFX
                    Settings.set_player_mode(player_mode, engine_id)
                    # Player
                    Settings.set_player(player, engine_id)
                    try:
                        tran_id = SoundCapabilities.get_transcoder(
                                                               target_audio=target_audio,
                                                               service_id=engine_id)
                        if tran_id is not None:
                            MY_LOGGER.debug(f'Setting converter: {tran_id} for '
                                            f'{engine_id}')
                            Settings.set_converter(tran_id, engine_id)
                            x = Settings.get_converter(engine_id=engine_id)
                            MY_LOGGER.debug(f'Setting converter: {x}')
                    except ValueError:
                        # Can not find a match. Don't recover, for now
                        reraise(*sys.exc_info())

                    '''
                    if self.service_id != service_id:
                        # Engine changed, pick player and PlayerMode
                        # If player and playermode already set for this player,
                        # then use it.
                        player_id: str = Settings.get_player_id(service_id)
                        if player_id is None or player_id == '':
                            # Try using player from another engine
                            pass

                    # cacheing
                    # Does engine support caching? Is it already set?
                    Settings.set_use_cache(False, service_id)
                    # PlayerMode
                    Settings.set_player_mode(PlayerMode.FILE, service_id)
                    # Player
                    Settings.set_player(Players.MPV, service_id)
                    '''
                    use_cache: bool = True

                    Settings.set_use_cache(use_cache, engine_id)
                    # Settings.set_player_mode(PlayerMode.FILE, service_id)
                    # Player
                    # Settings.set_player(Players.MPV, service_id)
                    # Settings.set_engine_id(service_id)
                    # MY_LOGGER.debug(f'STARTING ENGINE_ID: {service_id}')

                    # Expensive
                    from service_worker import TTSService
                    TTSService.get_instance().initTTS(engine_id)
                    MY_LOGGER.debug(f'speed should be 1.5: {Settings.get_speed()}')

            voice = self.get_current_voice()
            self.engine_language_value.setLabel(voice)
            self.engine_engine_value.setLabel(choice.lang_info.translated_engine_name)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'engine_language_value: '
                                f'{self.engine_language_value.getLabel()}')
            Settings.set_language(choice.lang_info.locale)
        except Exception as e:
            MY_LOGGER.exception('')

    def voice_engine(self, choice: Choice,
                     selection_idx: int) -> None:
        """
        Used during engine selection to voice which engine is in focus.

        Uses the voice/dialect closet to the currently configured Kodi locale

        :param choice: Choice for instance of engine to be voiced
        :param selection_idx: index of Choice from Choices list. Redundant
        :return:
        """
        MY_LOGGER.debug('FOOO voice_engine')

        if choice is not None:
            engine_id: str = choice.engine_id
            # Get an appropriate voice for this engine
            if engine_id is not None:
                from service_worker import TTSService
                current_engine_id: str = TTSService.get_instance().tts.engine_id
                if current_engine_id != engine_id:
                    PhraseList.set_current_expired()  # Changing engines
                lang_info: LanguageInfo = choice.lang_info
                MY_LOGGER.debug(f'lang_info: {lang_info}')
                if lang_info is not None:
                    # language: str = lang_info.ietf.autonym()
                    voice: str = lang_info.engine_voice_id
                    MY_LOGGER.debug(f'engine: {engine_id} voice: {voice} '
                                    f'new_lang: {lang_info.engine_lang_id}')
                    Settings.set_language(lang_info.engine_lang_id,
                                          engine_id=engine_id)
                    Settings.set_voice(voice, engine_id=engine_id)
                    # cacheing
                    Settings.set_use_cache(True, engine_id)
                    # PlayerMode
                    Settings.set_player_mode(PlayerMode.SLAVE_FILE, engine_id)
                    # Player
                    Settings.set_player(Players.MPV, engine_id)
                    # Speed
                    Settings.set_speed(speed=1.0)  # Speed of 1x
                    try:
                        MY_LOGGER.debug(f'current_engine: {current_engine_id} '
                                        f'new_engine: {engine_id}')
                        if current_engine_id != engine_id:
                            # Expensive
                            MY_LOGGER.debug(f'Setting initTTS to {engine_id}')
                            from service_worker import TTSService
                            TTSService.get_instance().initTTS(engine_id)
                            MY_LOGGER.debug('Returned from initTTS. '
                                            f'Engine is: {self.engine_id}')
                    except Exception:
                        MY_LOGGER.exception('')

    def set_language_field(self) -> None:
        """
        Configures the language UI field, processing the related settings
        and resolving any incompatibility issues with other settings.
        :return:
        """
        try:
            MY_LOGGER.debug('FOOO set_language_field')
            #  MY_LOGGER.debug(f'In set_language_field')
            choices: List[Choice]
            # The language setting will always have the same language ('en')
            # as Kodi since Kodi is the source of all messages to be voiced.
            # The territory and voice can be different, as long as the variants
            # are not too far different.
            ietf_lang: langcodes.Language
            _, _, _, ietf_lang = LanguageInfo.get_kodi_locale_info()
            engine_id: str = Settings.get_engine_id()
            current_engine_lang_id: str = Settings.get_language(engine_id)
            current_lang_voice_id: str = Settings.get_voice(engine_id)
            # lang_id = None causes the language code ('en') to come from
            # LanguageInfo.get_kodi_locale_info()
            lang_variant: LanguageInfo
            lang_variant = LanguageInfo.get_entry(engine_id=engine_id,
                                                  engine_voice_id=current_lang_voice_id,
                                                  lang_id=None)
            choices, current_choice_index = SettingsHelper.get_language_choices(
                    engine_id=engine_id, get_best_match=False)
            self.save_current_choices(choices, current_choice_index)
            MY_LOGGER.debug(f'# choices: {len(choices)} current_choice_index: '
                            f'{current_choice_index}')
            if current_choice_index < 0:
                current_choice_index = 0
            idx: int = 0
            for choice in choices:
                if choice.lang_info == lang_variant:
                    current_choice_index = idx
                    break
                idx += 1
            if idx >= len(choices):
                MY_LOGGER.debug(f'Could not find current lang_variant in choices\n'
                                f'service_id: {engine_id}  current_engine_lang_id: '
                                f'{current_engine_lang_id} current_lang_voice_id: '
                                f'{current_lang_voice_id}\n'
                                f'current: {lang_variant} \n choices: {choices}')

            if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                Settings.set_language(SettingsProperties.UNKNOWN_VALUE)
                self.engine_language_group.setVisible(False)
                self.engine_language_value.setEnabled(False)
                self.engine_language_value.setLabel(
                        Messages.get_msg(Messages.UNKNOWN))
                return
            choice: Choice = choices[current_choice_index]
            voice = choice.lang_info.translated_voice
            lang_id: str = choice.lang_info.locale
            #  MY_LOGGER.debug(f'language: {language} # choices {len(choices)}')
            self.engine_language_value.setLabel(voice)
            self.engine_language_group.setVisible(True)
            if len(choices) < 2:
                self.engine_language_value.setEnabled(False)
            else:
                self.engine_language_value.setEnabled(True)
            Settings.set_language(lang_id)
        except Exception as e:
            MY_LOGGER.exception('')

    def select_language(self):
        """
        Presents the user with a list of the language variants for the given
        language and TTS engine. As an entry gets focus it is voiced in that
        language variant (via voice_language).

        Once a user selects an entry and confirms the selection,
        the change is committed to settings. Otherwise, any changes are
        discarded once the Selection Dialog exits.

        Once the user has configured the TTS engine, the next logical thing
        to do is to choose which language variant to use. When the TTS engine
        is configured, the only choice you have is the closest match to Kodi's
        locale. Here you get to fine tune it.

        First, all variants of Kodi's language (ex: en, or de) are discovered
        and ordered in rank of match and then by sorted name.
        :return:
        """
        try:
            MY_LOGGER.debug('FOOO select_language')
            choices: List[Choice]
            engine_id: str = Settings.get_engine_id()
            # Gets every language variant for the current engine and language
            # Sorted first by closeness of match to native language variant
            # and second by variant name.
            choices, current_choice_index = SettingsHelper.get_language_choices(
                    engine_id=engine_id,
                    get_best_match=False,
                    format_type=FormatType.LONG)
            self.save_current_choices(choices, current_choice_index)
            #  MY_LOGGER.debug(f'In select_language # choices: {len(choices)} '
            #                     f'current_choice_idx {current_choice_index} '
            #                     f'current_choice: {choices[current_choice_index]}')
            if len(choices) == 0:
                Settings.set_language(SettingsProperties.UNKNOWN_VALUE)
                self.engine_language_group.setVisible(False)
                self.engine_language_value.setEnabled(False)
                self.engine_language_value.setLabel(
                        Messages.get_msg(Messages.UNKNOWN))
                return
            # else:
            #     self.engine_language_group.setVisible(True)
            current_locale: str
            kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
                LanguageInfo.get_kodi_locale_info()
            kodi_lang: str
            kodi_locale: str
            locale_name: str
            kodi_language: langcodes.Language
            lang_name: str = kodi_language.language_name()
            engine_name: str = LanguageInfo.get_translated_engine_name(engine_id)
            title: str
            title = MessageId.AVAIL_VOICES_FOR_LANG.get_formatted_msg(
                    lang_name, engine_name)
            sub_title: str
            sub_title = (MessageId.DIALOG_LANG_SUB_HEADING.get_msg())
            previous_engine_id: str = self.engine_id
            self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_CONFIG)
            self.save_settings()
            MY_LOGGER.debug(f'sub_title: {sub_title}')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           sub_title=sub_title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=self.voice_language,
                                           disable_tts=True)
            dialog.doModal()
            self.restore_settings()  # resets settings prior to SelectionDialog

            # Now, apply any desired changes
            idx = dialog.close_selected_idx
            if idx < 0:  # No selection made or CANCELED
                return

            choice: Choice = choices[idx]
            if choice is not None:
                lang_info: LanguageInfo = choice.lang_info
                if lang_info is not None:
                    voice: str = choice.lang_info.engine_voice_id
                    from service_worker import TTSService
                    Settings.set_language(choice.lang_info.engine_lang_id,
                                          engine_id=engine_id)
                    Settings.set_voice(voice, engine_id=engine_id)
                    speed: float = Settings.get_speed()
                    MY_LOGGER.debug(f'engine: {engine_id} '
                                    f'language: {choice.lang_info.engine_lang_id}'
                                    f' voice: {voice}'
                                    f' speed: {speed}')
            self.engine_language_value.setLabel(choice.lang_info.translated_voice)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Set engine_language_value to '
                                f'{self.engine_language_value.getLabel()}')
        except Exception as e:
            MY_LOGGER.exception('')

    def voice_language(self, choice: Choice,
                       selection_idx: int) -> None:
        """
        Used during language selection to voice which language is in focus.

        :param choice: Choice for instance of language to be voiced
        :param selection_idx: index of Choice from Choices list. Redundant
        :return:
        """
        MY_LOGGER.debug('FOOO voice_language')
        MY_LOGGER.debug(f'idx: {selection_idx}')
        engine_id: str = Settings.get_engine_id()
        # gets the language_id, a unique id for the focused language
        # and the matching engine.
        if choice is not None:
            lang_info: LanguageInfo = choice.lang_info
            MY_LOGGER.debug(f'CHOICE idx: {choice.value} lang: '
                            f'{lang_info.ietf.to_tag()}')
            # gender: Genders = Settings.get_gender(self.service_id)
            if lang_info is not None:
                current_lang: LanguageInfo
                #   TODO: this is pretty crude.
                choices, current_selection_idx = self.retrieve_current_choices()
                choices: List[Choice]
                current_selection_idx: int
                current_choice: Choice = choices[selection_idx]
                current_lang = current_choice.lang_info
                voice: str = current_lang.engine_voice_id
                from service_worker import TTSService
                # MY_LOGGER.debug(f'{phrases}')
                Settings.set_language(current_lang.engine_lang_id,
                                      engine_id=engine_id)
                #  MY_LOGGER.debug(f'engine: {service_id} voice: {voice}')
                Settings.set_voice(voice, engine_id=engine_id)
                # cacheing
                # Settings.set_use_cache(False, service_id)
                # PlayerMode

                # Settings.set_player_mode(PlayerMode.FILE, service_id)
                # Player
                # Settings.set_player(Players.MPLAYER, service_id)
                # Speed
                Settings.set_speed(speed=1.0)  # Speed of 1x
                # MY_LOGGER.debug(f'OLD engine: {self.service_id} '
                #                 f'NEW engine: {service_id}')
                # if self.service_id != service_id:
                #     Settings.set_engine_id(service_id)
                #     # Expensive
                #     TTSService.get_instance().initTTS(self.service_id)  # .sayText(phrases)

    def refresh_engine_language_value(self):
        """
        Updates the GUI language value.
        :return:
        """
        voice = self.get_current_voice()
        self.engine_language_value.setLabel(voice)

    def set_voice_field(self):
        """
        Updates the voice field with the value that the current engine is
        using. The voice can be changed by the user selecting the asociated
        button.
        :return:
        """
        clz = type(self)
        try:
            MY_LOGGER.debug('FOOO set_voice_field')
            avail: bool
            engine_id: str = self.engine_id
            avail = SettingsMap.is_setting_available(engine_id,
                                                     SettingsProperties.VOICE)
            # MY_LOGGER.debug(f'is voice available: {avail}')
            valid: bool = SettingsMap.is_valid_property(engine_id,
                                                        SettingsProperties.VOICE)
            # MY_LOGGER.debug(f'is voice valid: {valid}')
            if not SettingsMap.is_setting_available(engine_id,
                                                    SettingsProperties.VOICE):
                #  MY_LOGGER.debug(f'setting voice_group invisible')
                self.engine_voice_group.setVisible(False)
                return
            choices: List[Choice]
            choices, current_choice_index = self.get_voice_choices()
            if current_choice_index < 0:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'choice out of range: {current_choice_index} '
                                    f'# choices: {len(choices)}')
                current_choice_index = 0

            if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'setting voice disabled: {self.engine_voice_value}')
                self.engine_voice_value.setEnabled(False)
                self.engine_voice_value.setLabel(
                        Messages.get_msg(Messages.UNKNOWN))
                return

            choice: Choice = choices[current_choice_index]
            MY_LOGGER.debug(f'voice label: {choice.label}')
            self.engine_voice_value.setLabel(choice.label)
            if len(choices) < 2:
                self.engine_voice_value.setEnabled(False)
            else:
                self.engine_voice_value.setEnabled(True)

            Settings.set_voice(choice.lang_info.engine_voice_id, engine_id)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting voice to: {choice.lang_info.engine_voice_id}')
            self.engine_voice_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_voice_choices(self) -> Tuple[List[Choice], int]:
        """
            Creates a list of voices for the current language and engine
            in a format suitable for the SelectionDialog
        :return:
        """
        choices: List[Choice] = []
        current_choice_index: int = -1
        MY_LOGGER.debug('FOOO get_voice_choices')

        try:
            # current_value: str = self.getSetting(SettingsProperties.VOICE)
            # MY_LOGGER.debug(f'engine: {self.service_id} voice: {current_value}')
            voices: List[Choice]
            # Request match closet to current lang settings, not kodi_locale
            voices, current_choice_index = SettingsHelper.get_language_choices(
                    self.engine_id,
                    get_best_match=False,
                    format_type=FormatType.LONG)
            # voices = BackendInfo.getSettingsList(
            #         self.service_id, SettingsProperties.VOICE)
            #  MY_LOGGER.debug(f'voices: {voices}')
            if voices is None:
                voices = []

            # voices = sorted(voices, key=lambda entry: entry.label)
            voices: List[Choice]
            for choice in voices:
                choice: Choice
                choices.append(choice)
        except Exception as e:
            MY_LOGGER.exception('')

        return choices, current_choice_index

    def select_voice(self):
        """

        :return:
        """
        try:
            MY_LOGGER.debug('FOOO select_voice')

            choices: List[Choice]
            choices, current_choice_index = self.get_voice_choices()
            title: str = MessageId.SELECT_VOICE_BUTTON.get_msg()
            sub_title = 'Is this a sub_title for select_voice?'

            self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_CONFIG)
            self.save_settings()
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           sub_title=sub_title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings()  # resets settings prior to SelectionDialog
            idx = dialog.close_selected_idx
            #  MY_LOGGER.debug_v(
            #         'SelectionDialog voice idx: {}'.format(str(idx)))
            if idx < 0:
                return

            choice: Choice = choices[idx]
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'select_voice value: {choice.label} '
                                  f'setting: {choice.value} idx: {idx:d}')

            self.engine_voice_value.setLabel(choice.label)
            Settings.set_voice(choice.choice_index)
            # self.update_engine_values()
        except Exception as e:
            MY_LOGGER.exception('')

    def get_pitch_range(self) -> UIValues:
        return
        """

        :return:
        """
        result: UIValues | None = None
        try:
            pitch_val: INumericValidator
            pitch_val = SettingsMap.get_validator(self.engine_id,
                                                  SettingsProperties.PITCH)
            if pitch_val is None:
                raise NotImplementedError
            result = pitch_val.get_tts_values()
        except NotImplementedError:
            result = UIValues()
        return result

    def select_pitch(self) -> None:
        """

        """
        return
        try:
            pitch_val: INumericValidator
            pitch_val = SettingsMap.get_validator(self.engine_id,
                                                  SettingsProperties.PITCH)
            if pitch_val is None:
                raise NotImplementedError

            pitch = self.engine_pitch_slider.getInt()
            pitch_val.set_value(pitch)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_pitch_range(self):
        """

        """
        return
        try:
            if not SettingsMap.is_valid_property(self.engine_id,
                                                 SettingsProperties.PITCH):
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

    def set_gender_field(self):
        """

        :return:
        """
        try:
            MY_LOGGER.debug('FOOO get_gender_field')

            choices: List[Choice]
            valid: bool = SettingsMap.is_valid_property(self.engine_id,
                                                        SettingsProperties.GENDER)
            MY_LOGGER.debug(f'service_id: {self.engine_id} GENDER valid: {valid}')
            if not valid:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Gender is not a valid property for '
                                    f'{self.engine_id}')
                self.engine_gender_group.setVisible(False)
            else:
                choices, current_choice_index = self.get_gender_choices()

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
                self.engine_gender_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_gender_choices(self) -> Tuple[List[Choice], int]:
        """

        :return:
        """
        MY_LOGGER.debug('FOOO get_gender_choices')

        current_value: Genders = Settings.get_gender(self.engine_id)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'gender: {current_value}')
        current_choice_index = -1
        choices: List[Choice] = []
        try:
            # Fetch settings on every access because it can change
            engine_id = self.engine_id
            if not SettingsMap.is_valid_property(engine_id, SettingsProperties.GENDER):
                return choices, current_choice_index

            #  MY_LOGGER.debug(f'Calling getSettingsList engine: {service_id}')
            engine: ITTSBackendBase = self.getEngineInstance(engine_id)
            gender_choices, _ = engine.settingList(SettingsProperties.GENDER)
            gender_choices: List[Choice]
            # supported_genders = BackendInfo.getSettingsList(engine,
            #                                               SettingsProperties.GENDER)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'genders: {gender_choices}')
            genders: List[Choice] = []

            if gender_choices is None:
                supported_genders = []
            idx: int = 0
            for choice in gender_choices:
                choice: Choice
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'choice: {choice.value}')
                display_value = GenderSettingsMap.get_label(choice.value)
                choices.append(Choice(label=display_value, value=choice.value,
                                      choice_index=idx))
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Gender choice: {choices[-1]}')
                if choice.value == current_value:
                    current_choice_index = len(choices) - 1
                idx += 1
        except Exception as e:
            MY_LOGGER.exception('')

        return choices, current_choice_index

    def select_gender(self):
        """

        :return:
        """
        try:
            MY_LOGGER.debug('FOOO select_gender')

            choices: List[Choice]
            choices, current_choice_index = self.get_gender_choices()
            # xbmc.executebuiltin('Skin.ToggleDebug')
            title: str = Messages.get_msg(Messages.SELECT_VOICE_GENDER)
            self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_CONFIG)
            self.save_settings()
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings()  # resets settings prior to SelectionDialog
            idx = dialog.close_selected_idx
            if idx < 0:
                return

            choice: Choice = choices[idx]
            gender: Genders = Genders(choice.value)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'select_gender label: {choice.label} '
                                  f'setting: {choice.value} idx: {idx:d}')
            self.engine_gender_value.setLabel(choice.label)
            Settings.set_gender(gender)
            # self.update_engine_values()
        except Exception as e:
            MY_LOGGER.exception('')

    def get_player_choices(self) -> Tuple[List[Choice], int]:
        """
            Get players which are compatible with the engine as well as player_Mode.
            The 'ranking' of players may influence the suggested player.

            The player_mode should be checked to see if it requires changing

        :return: List of compatible players and an index referencing the current
                 or suggested player.
        """
        choices: List[Choice] = []
        current_choice_index = -1
        '''
            # We want the players which can handle what our TTS engine produces
        '''
        return self.get_compatible_players(self.engine_id)

    def get_compatible_players(self, current_engine_id: str | None = None
                               ) -> Tuple[List[Choice], int]:
        """
               Get players which are compatible with the engine as well as player_Mode.
               The 'ranking' of players may influence the suggested player.

               The player_mode should be checked to see if it requires changing

           :return: List of compatible players and an index referencing the current
                 or suggested player.
        """
        choices: List[Choice] = []
        current_choice_index: int = -1
        try:
            if not SettingsMap.is_valid_property(current_engine_id,
                                                 SettingsProperties.PLAYER):
                if MY_LOGGER.isEnabledFor(INFO):
                    MY_LOGGER.info(f'There is no PLAYER for {current_engine_id}')
                return choices, current_choice_index

            # Make sure that any player complies with the engine's player
            # validator

            val: IStringValidator
            val = SettingsMap.get_validator(current_engine_id,
                                            SettingsProperties.PLAYER)
            current_choice: str
            current_choice = Settings.get_player_id(current_engine_id)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'current player: {current_choice} '
                                f'engine: {current_engine_id} ')

            supported_players_with_enable: List[AllowedValue]
            supported_players_with_enable = val.get_allowed_values()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'supported_players_with_enable:'
                                f' {supported_players_with_enable}')
            default_choice_str: str = val.default_value
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'default_value: {val.default_value}')

            if supported_players_with_enable is None:
                supported_players_with_enable = []
            supported_players: List[Tuple[str, bool]] = []
            idx: int = 0
            default_choice_idx: int = -1
            current_enabled: bool = True
            default_enabled: bool = True
            for supported_player in supported_players_with_enable:
                supported_player: AllowedValue
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'player_str: {supported_player.value} '
                                    f'enabled: {supported_player.enabled}')
                player: str = supported_player.value
                supported_players.append((player, supported_player.enabled))
                if player == current_choice:
                    current_choice_index = idx
                    current_enabled = supported_player.enabled
                if player == default_choice_str:
                    default_choice_idx = idx
                    default_enabled = supported_player.enabled
                idx += 1

            if current_choice_index < 0:
                current_choice_index = default_choice_idx
                current_enabled = default_enabled
            if not current_enabled:  # Must pick something else
                current_choice_index = 0
            idx: int = 0
            for player_id, enabled in supported_players:
                player_id: str
                label: str = Players.get_msg(player_id)
                choices.append(Choice(label=label, value=player_id,
                                      choice_index=idx, enabled=enabled))
        except Exception as e:
            MY_LOGGER.exception('')
        return choices, current_choice_index

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
            choices: List[Choice]
            (choices, current_choice_index) = self.get_player_choices()
            title: str = MessageId.SELECT_PLAYER.get_msg()
            sub_title: str = MessageId.SELECT_PLAYER_SUBTITLE.get_msg()
            self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_CONFIG)
            self.save_settings()
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           sub_title=sub_title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()

            self.restore_settings()  # resets settings prior to SelectionDialog
            idx = dialog.close_selected_idx
            if idx < 0:
                return

            choice: Choice = choices[idx]
            player_id: str = choice.value
            enabled: bool = choice.enabled
            player_label: str = choice.label
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'select_player value: {player_label} '
                                  f'setting: {player_id} idx: {idx:d} '
                                  f'enabled: {enabled}')
            engine_id: str = self.engine_id
            player_mode: PlayerMode
            player_mode = Settings.get_player_mode(self.engine_id)
            player_mode, allowed_values = SettingsHelper.update_player_mode(engine_id,
                                                                            player_id,
                                                                            player_mode)
            MY_LOGGER.debug(f'Setting engine: {self.engine_id} '
                            f'player_mode: {player_mode} '
                            f'values: {allowed_values}')
            self.set_player_mode_field(player_mode, self.engine_id)
            self.engine_player_value.setLabel(player_label)
            Settings.set_player(player_id, engine_id)
            # self.update_engine_values()
        except Exception as e:
            MY_LOGGER.exception('')

    def set_player_field(self):
        """

        :return:
        """
        try:
            choices: List[Choice]
            choices, current_choice_index = self.get_player_choices()
            if current_choice_index < 0:
                current_choice_index = 0
            if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                self.engine_player_value.setEnabled(False)
                self.engine_player_value.setLabel(
                        Messages.get_msg(Messages.UNKNOWN))
                return

            choice: Choice = choices[current_choice_index]
            player_id: str = choice.value
            enabled: bool = choice.enabled
            player_label: str = choice.label
            self.engine_player_value.setLabel(choice.label)
            if len(choices) < 2:
                self.engine_player_value.setEnabled(False)
            else:
                self.engine_player_value.setEnabled(True)

            Settings.set_player(choice.value)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_module_field(self):
        """

        :return:
        """
        try:
            choices: List[Choice]
            choices, current_choice_index = self.get_module_choices()
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

            #  self.set_module(choice.value)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_module_choices(self) -> Tuple[List[Choice], int]:
        """

        :return:
        """
        choices: List[Choice] = []
        current_choice_index: int = -1
        try:
            current_value = self.get_module()
            if not SettingsMap.is_valid_property(self.engine_id,
                                                 SettingsProperties.MODULE):
                return [], -1

            supported_modules: List[Choice]
            default_module: str
            supported_modules, default_module = BackendInfo.getSettingsList(
                    self.engine_id, SettingsProperties.MODULE)
            if supported_modules is None:
                supported_modules = []

            default_choice_index = -1
            idx: int = 0
            for module_name, module_id in supported_modules:
                module_label = module_name  # TODO: Fix
                choices.append(Choice(label=module_label, value=module_id,
                                      choice_index=idx))
                if module_id == current_value:
                    current_choice_index = len(choices) - 1
                if module_id == default_module:
                    default_choice_index = len(choices) - 1
                idx += 1

            if current_choice_index < 0:
                current_choice_index = default_choice_index
        except Exception as e:
            MY_LOGGER.exception('')
        return choices, current_choice_index

    def select_module(self):
        """

        :return:
        """
        try:
            choices: List[Choice]
            (choices, current_choice_index) = self.get_module_choices()
            title: str = Messages.get_msg(Messages.SELECT_MODULE)
            self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_CONFIG)
            self.save_settings()
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings()  # resets settings prior to SelectionDialog
            idx = dialog.close_selected_idx
            if idx < 0:
                return

            choice: Choice = choices[idx]
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'value: {choice.label} '
                                  f'setting: {choice.value} idx: {idx:d}')
            self.engine_module_value.setLabel(choice.label)
            Settings.set_module(choice.value)
            # self.update_engine_values()
        except Exception as e:
            MY_LOGGER.exception('')

    def select_volume(self) -> None:
        """

        """
        try:
            volume_val: INumericValidator | NumericValidator
            volume_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                   SettingsProperties.VOLUME)
            if volume_val is None:
                raise NotImplementedError
            volume: float = self.engine_volume_slider.getFloat()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting volume to {volume}')
            volume_val.set_value(volume)
            self.engine_volume_label.setLabel(label=f'Volume: {volume}dB')
        except Exception as e:
            MY_LOGGER.exception('')

    def set_volume_range(self):
        """

        """
        try:
            if not SettingsMap.is_valid_property(SettingsProperties.TTS_SERVICE,
                                                 SettingsProperties.VOLUME):
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Volume is NOT valid property')
                self.engine_volume_group.setVisible(False)
            else:
                volume_val: NumericValidator
                result: UIValues = self.get_volume_range()
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
                                        f'min: {result.minimum} inc: {result.increment} '
                                        f'max: {result.maximum}')
                    volume: float = Settings.get_volume(self.engine_id)
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Setting volume to {volume}')
                    self.engine_volume_label.setLabel(
                            label=MessageId.VOLUME_DB.get_formatted_msg(volume))

                    self.engine_volume_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_volume_range(self) -> UIValues:
        """

        :return:
        """
        result: UIValues | None = None
        try:
            volume_val: INumericValidator
            volume_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                   SettingsProperties.VOLUME)
            if volume_val is None:
                raise NotImplementedError
            result = volume_val.get_tts_values()
        except NotImplementedError:
            result = UIValues()
            MY_LOGGER.exception(f'service_id: {self.engine_id} volume: {result}')
        return result

    def select_speed(self):

        """

        """
        try:
            speed_val: INumericValidator
            speed_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                  SettingsProperties.SPEED)
            if speed_val is None:
                raise NotImplementedError

            speed: float = self.engine_speed_slider.getFloat()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'speed: {speed}')
            Settings.set_speed(speed)
            self.engine_speed_label.setLabel(
                    Messages.get_formatted_msg(Messages.SELECT_SPEED,
                                               f'{speed:.1f}'))
            self.engine_speed_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_speed_range(self):
        """

        """
        try:
            if not SettingsMap.is_valid_property(SettingsProperties.TTS_SERVICE,
                                                 SettingsProperties.SPEED):
                self.engine_speed_group.setVisible(False)
            else:
                speed_val: NumericValidator
                result: UIValues = self.get_speed_range()
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'min: {result.minimum} max: {result.maximum} '
                                    f'inc: {result.increment} current: {result.current}')
                if result.minimum == result.maximum:
                    self.engine_speed_group.setVisible(False)
                else:
                    self.engine_speed_slider.setFloat(
                            result.current, result.minimum, result.increment,
                            result.maximum)
                    speed: float = Settings.get_speed()
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Setting speed to {speed}')
                    self.engine_speed_label.setLabel(
                            Messages.get_formatted_msg(Messages.SELECT_SPEED,
                                                       f'{speed:.2f}'))
                    self.engine_speed_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_speed_range(self) -> UIValues:
        """

        :return:
        """
        try:
            speed_val: INumericValidator
            speed_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                  SettingsProperties.SPEED)
            speed_val: TTSNumericValidator
            if speed_val is None:
                raise NotImplementedError
            result = speed_val.get_values()
        except NotImplementedError:
            result = UIValues()
        return result

    def select_cache_speech(self):
        """

        """
        try:
            cache_speech: bool = self.engine_cache_speech_radio_button.isSelected()
            Settings.set_use_cache(cache_speech)
            self.engine_cache_speech_group.setVisible(True)
            # self.update_engine_values()
        except NotImplementedError:
            self.engine_cache_speech_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_cache_speech_field(self):
        """

        """
        try:
            use_cache: bool = Settings.is_use_cache(self.engine_id)
            self.engine_cache_speech_radio_button.setSelected(use_cache)
            self.engine_cache_speech_group.setVisible(True)
            self.engine_cache_speech_radio_button.setVisible(True)
        except NotImplementedError:
            self.engine_cache_speech_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def select_player_mode(self):
        """

        :return:
        """
        try:
            choices: List[Choice]
            choices, current_choice_index = self.get_player_mode_choices()
            if current_choice_index < 0:
                current_choice_index = 0
            title: str = Messages.get_msg(Messages.SELECT_PLAYER_MODE)
            self.reset_settings(SettingsDialog.POP_SETTING_STACK_FOR_CONFIG)
            self.save_settings()
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings()  # resets settings prior to SelectionDialog
            idx = dialog.close_selected_idx
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'SelectionDialog value: '
                                  f'{PlayerMode.translated_name} '
                                  f'idx: {str(idx)}')
            if idx < 0:
                return None

            choice: Choice = choices[idx]
            prev_choice: Choice = choices[current_choice_index]
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'engine: {self.engine_id} new player mode: {choice.label}'
                                f' previous: {prev_choice.label} ')
            new_player_mode: PlayerMode = PlayerMode(choice.value)
            previous_player_mode: PlayerMode
            previous_player_mode = PlayerMode(prev_choice.value)

            MY_LOGGER.debug(f'new_player_mode: {new_player_mode} type: '
                            f'{type(new_player_mode)}')
            if new_player_mode != previous_player_mode:
                MY_LOGGER.debug(f'setting player mode to: {new_player_mode}')
                self.set_player_mode_field(new_player_mode, self.engine_id)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_player_mode_field(self, player_mode: PlayerMode | None = None,
                              engine_id: str | None = None):
        """
            Initializes and displays the Player Mode control
        """
        try:
            if engine_id is None:
                engine_id = self.engine_id
            if player_mode is None:
                player_mode = Settings.get_player_mode(engine_id)
            player_mode_str: str = player_mode.translated_name
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting player mode to {player_mode_str}')

            Settings.set_player_mode(player_mode=player_mode, engine_id=engine_id)

            self.engine_player_mode_label.setLabel(player_mode_str)
            self.engine_player_mode_button.setVisible(True)
            self.engine_player_mode_label.setVisible(True)
            self.engine_player_mode_group.setVisible(True)
        except NotImplementedError:
            self.engine_player_mode_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_player_mode_choices(self) -> Tuple[List[Choice], int]:
        """

        :return:
        """
        choices: List[Choice] = []
        current_choice_index: int = -1
        try:
            if not SettingsMap.is_valid_property(self.engine_id,
                                                 SettingsProperties.PLAYER_MODE):
                MY_LOGGER.info(f'There are no PLAYER_MODEs for {self.engine_id}')
                return choices, current_choice_index
            current_choice: PlayerMode
            current_choice = Settings.get_player_mode(self.engine_id)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'current player_mode: {current_choice} '
                                f'engine: {self.engine_id} ')

            engine_id: str = self.engine_id
            player_id: str = Settings.get_player_id(engine_id)
            allowed_values: List[PlayerMode]
            default_choice: PlayerMode
            default_choice, allowed_values = SettingsHelper.update_player_mode(engine_id,
                                                                            player_id,
                                                                            current_choice)
            MY_LOGGER.debug(f'engine: {self.engine_id} '
                            f'default_choice: {default_choice} '
                            f'values: {allowed_values}')
            idx: int = 0
            default_choice_idx: int = -1
            for supported_mode in allowed_values:
                supported_mode: PlayerMode
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'supported_mode: {supported_mode.value} '
                                    f'enabled: True')
                choices.append(Choice(label=supported_mode.translated_name,
                                      value=supported_mode.value,
                                      choice_index=idx, enabled=True))
                if supported_mode == current_choice:
                    current_choice_index = idx
                idx += 1

            if current_choice_index < 0:
                current_choice_index = default_choice_idx
                current_choice_index = 0
        except Exception as e:
            MY_LOGGER.exception('')
        return choices, current_choice_index

    def select_api_key(self):
        """

        """
        try:
            api_key = self.engine_api_key_edit.getText()
            Settings.set_api_key(api_key)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_api_field(self):
        """

        """
        try:
            if not SettingsMap.is_setting_available(self.engine_id,
                                                    SettingsProperties.API_KEY):
                self.engine_api_key_group.setVisible(False)
                return

            if (SettingsMap.get_validator(self.engine_id,
                                          property_id=SettingsProperties.API_KEY) is not
                    None):
                api_key: str = Settings.get_api_key(self.engine_id)
                #  self.engine_api_key_edit.setText(api_key)
                self.engine_api_key_edit.setLabel(
                        Messages.get_msg(Messages.ENTER_API_KEY))
                self.engine_api_key_group.setVisible(True)
            else:
                self.engine_api_key_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def selection_dialog(self, title: str,
                         choices: List[Choice], initial_choice: int,
                         sub_title: str | None = None,
                         call_on_focus: Callable[Choice, None] | None = None,
                         call_on_select: Callable[Choice, None] | None = None,
                         disable_tts: bool = False
                         ) -> SelectionDialog:
        """
        Wraps the SelectionDialog so that the single instance can be shared.

        :param title:  Heading for the dialog
        :param choices:  List of available choices to present
        :param initial_choice:  Index of the current choice in choices
        :param sub_title:  Optional Sub-Heading for the dialog
        :param call_on_focus:  Optional call-back function for on-focus events
                               useful for hearing the difference immediately
        :param call_on_select: Optional call-back function for on-click events
                               useful for voicing the selected item immediately
        :param disable_tts: When True TTS screen-scraping is disabled until this
                            dialog text_exists. See Notes
        :return: Returns the underlying SelectionDialog so that methods can be
                 called such as doModal

        Note: Any changes made in SettingsDialog are either committed or undone
        on exit. OK commits the changes in Settings to settings.xml.
        Cancel reverts all changes in Settings from a backup-copy.

        Note: disable_tts is used when the language and engine need to be switched
        while voicing the dialog.

        Reverting live changes without Cancelling SettingsDialog requires care.
        """
        if SettingsDialog._selection_dialog is None:
            script_path: Path = Constants.ADDON_PATH
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(
                        f'SelectionDialog ADDON_PATH: {Constants.ADDON_PATH}')
            SettingsDialog._selection_dialog = SelectionDialog('selection-dialog.xml',
                                                               str(script_path), 'Custom',
                                                               defaultRes='1080i',
                                                               title=title,
                                                               choices=choices,
                                                               initial_choice=initial_choice,
                                                               sub_title=sub_title,
                                                               call_on_focus=call_on_focus,
                                                               call_on_select=call_on_select)
        else:
            SettingsDialog._selection_dialog.update_choices(title=title,
                                                            choices=choices,
                                                            initial_choice=initial_choice,
                                                            sub_title=sub_title,
                                                            call_on_focus=call_on_focus,
                                                            call_on_select=call_on_select)
        return SettingsDialog._selection_dialog

    @property
    def engine_id(self) -> str:
        """
            Gets the service_id from Settings. If the value is invalid, substitutes
            with one designated as 'good'. If a substitution is performed, the
            substitute is stored in Settings

        :return:
        """
        engine_id: str = Settings.get_engine_id()
        MY_LOGGER.info(f'service_id: {engine_id}')

        valid_engine: bool
        valid_engine = SettingsMap.is_available(engine_id)
        if not valid_engine:
            bad_engine_id: str = engine_id
            engine_id = BackendInfo.getAvailableBackends()[0].engine_id
            MY_LOGGER.info(f'Invalid engine: {bad_engine_id} replaced with: {engine_id}')
            Settings.set_engine_id(engine_id)
        return engine_id

    def get_current_voice(self) -> str:
        lang_info: LanguageInfo = LanguageInfo.get_entry()
        voice: str = ''
        if lang_info is None:
            voice = 'unknown'
        else:
            voice = lang_info.translated_voice
        return voice

    def get_language(self, label=False):
        """

        :return:
        """
        clz = type(self)
        try:
            self.language = Settings.get_language(self.engine_id)
            if self.language is None:
                MY_LOGGER.debug(f'Getting language from old call')
                _, default_setting = self.getEngineInstance().settingList(
                        SettingsProperties.LANGUAGE)
                self.language = default_setting
        except Exception as e:
            MY_LOGGER.exception('')
            self.language = get_language_code()
        lang: str = self.language
        if label:
            lang = SettingsHelper.get_formatted_lang(lang)
        return lang

    def get_module(self) -> str:
        """

        :return:
        """
        module = 'bad'
        try:
            module: str | None = self.get_module_setting()
            if module is None:
                engine: ITTSBackendBase = BackendInfo.getBackend(self.engine_id)
                module = engine.get_setting_default(SettingsProperties.PLAYER)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return module

    def getEngineInstance(self, engine_id=None) -> ITTSBackendBase:
        """
        :param engine_id:
        :return:
        """
        if engine_id is None:
            engine_id = self.engine_id
        engine_instance: ITTSBackendBase = BaseServices.getService(engine_id)
        return engine_instance

    def get_module_setting(self, default: str | None = None):
        """
            TODO: Almost certainly broken. Used by AudiDispatcher.
            Fix at that time. Don't share with Player setting anymore.
        :param default:
        :return:
        """
        engine: ITTSBackendBase = self.getEngineInstance(self.engine_id)
        if default is None:
            default = engine.get_setting_default(SettingsProperties.MODULE)
        value = engine.getSetting(SettingsProperties.MODULE, default)
        return value

    def commit_settings(self) -> None:
        """

        """
        SettingsLowLevel.commit_settings()
        MY_LOGGER.info(f'Settings saved/committed')
        #  TTSService.get_instance().checkBackend()

    def save_settings(self) -> None:
        """
        Pushes a copy of the current settings 'frame' onto the stack of settings.
        restore_settings pops the stack frame, discarding all changes and reverting
        to the settings prior to save_settings

        :return:
        """
        try:
            SettingsLowLevel.save_settings()
            self.settings_pushes += 1
        except Exception as e:
            MY_LOGGER.exception('')

    def restore_settings(self) -> None:
        """
        Pops the current stack frame of settings so that all settings are restored
        prior to save_settings.
        """
        if self.settings_pushes == 0:
            MY_LOGGER.debug('Settings Stack is being poped more than pushed')
            raise ValueError('Settings stack is being poped more than pushed')

        try:
            SettingsLowLevel.restore_settings()
            # settings_pushes is used to make sure that we exit this Dialog
            # with the Settings Stack restored to the same condition as when
            # we entered, even if user exits before some operation has a
            # chance to restore the stack.
            self.settings_pushes -= 1
        except Exception as e:
            MY_LOGGER.exception('')

    def reset_settings(self, depth_delta: int) -> None:
        """
        Restores settings so that the Settings Stack depth is the same as
        when the Dialog was entered, or when a setting is configured.

        When SettingsDialog starts, it pushes a new copy of the settingsMap onto
        the Settings Stack. This services as a scratch copy to test the
        effects of changing the settings, but leaving the ability to easily
        undo the changes.

        When a setting is configured, another settimgsMap is pushed so that the
        changes for that particular setting can be undone, but leaving other
        changes in effect.

        Due to the asynchronous nature of abandoning a dialog (BACK button)
        we can't just rely on simply poping the stack on return from configuriong
        a setting. Instead, at certain points, like starting to configure
        a setting, or no sttings are being configured, then the stack can be
        reset by knowing how many pushes should be on the stack at the time.

        When SettingsDialog enters, one frame is pushed.
        When any setting is configured, another frame is pushed.
        Therefore, before starting to configure a setting, make sure the frames
        pushed is one (from entering SettingsDialog). The same is true if no
        setting is being configured.
        When exiting SettingsDialog, zero frames should remain pushed.

        :param depth_delta: The target value of settings_pushes to reset to
        :return:
        """
        while self.settings_pushes > depth_delta:
            self.restore_settings()
