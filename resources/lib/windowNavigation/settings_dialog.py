# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from collections import namedtuple

import langcodes
import xbmc
import xbmcaddon
import xbmcgui
from xbmcgui import (ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider)

from backends.settings.language_info import LanguageInfo
from backends.settings.service_types import GENERATE_BACKUP_SPEECH, PlayerType
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
from common.exceptions import ConfigurationError
from common.lang_phrases import SampleLangPhrases
from common.logger import *
from common.message_ids import MessageId, MessageUtils
from common.messages import Message, Messages
from common.setting_constants import (AudioType, Backends, Genders, GenderSettingsMap,
                                      Players)
from common.settings import Settings
from common.settings_low_level import SettingsLowLevel, SettingsManager
from utils import util
from utils.util import get_language_code
from windowNavigation.action_map import Action
from windowNavigation.choice import Choice
from windowNavigation.selection_dialog import SelectionDialog

EngineConfig = namedtuple('EngineConfig',
                          ['engine_id', 'use_cache', 'player_id',
                           'engine_audio', 'player_mode', 'transcoder',
                           'trans_audio_in', 'trans_audio_out'],
                          rename=False, defaults=None, module=None)

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
        self.original_stack_depth: int = -1
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
        self.engine_language_value: ControlLabel | None = None
        self.engine_voice_group: ControlGroup | None = None
        self.engine_voice_button: ControlButton | None = None
        self.engine_voice_value: ControlLabel | None = None
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
        self.saved_choices: List[Choice] | None = None
        self.saved_selection_index: int | None = None
        # properties
        self._speed_val: INumericValidator | NumericValidator | None = None
        self._volume_val: INumericValidator | NumericValidator | None = None

        # Ensure some structures are built before we need them.
        SettingsHelper.build_allowed_player_modes()

    def re_init(self) -> None:
        MY_LOGGER.debug(f'In re-init')
        self.engine_instance = None
        self.saved_choices = None
        self.saved_selection_index = None
        self.closing = False
        self.exit_dialog = False
        # self.api_key = None

    @property
    def engine_id(self) -> str:
        """
            Gets the service_id from Settings. If the value is invalid, substitutes
            with one designated as 'good'. If a substitution is performed, the
            substitute is stored in Settings
        TODO: Review. There should be only one method to get engine_id in consistent
              way.
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

    @property
    def speed_val(self) -> INumericValidator:
        """

        :return:
        """
        if self._speed_val is None:
            self._speed_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                        SettingsProperties.SPEED)
            if self._speed_val is None:
                raise NotImplementedError
        return self._speed_val

    @property
    def volume_val(self) -> INumericValidator:
        """

        :return:
        """
        if self._volume_val is None:
            self._volume_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                         SettingsProperties.VOLUME)
            if self._volume_val is None:
                raise NotImplementedError
        return self._volume_val

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

                self.engine_engine_button = self.get_control_button(
                        clz.SELECT_ENGINE_BUTTON)

                self.engine_engine_value = self.get_control_label(
                        clz.SELECT_ENGINE_VALUE_LABEL)
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
                If there are many voices, then use multi-stage selection. Pick the 
                language/country (en-us) then use another 'voice' button to
                choose the specific voice. For now, it is ignored.
                """
                self.engine_language_group = self.get_control_group(
                        clz.SELECT_LANGUAGE_GROUP)
                self.engine_language_button: ControlButton = self.get_control_button(
                        clz.SELECT_LANGUAGE_BUTTON)

                self.engine_language_value = self.get_control_label(
                        clz.SELECT_LANGUAGE_VALUE_LABEL)

                self.engine_voice_group = self.get_control_group(
                        clz.SELECT_VOICE_GROUP)
                self.engine_voice_button: ControlButton = self.get_control_button(
                        clz.SELECT_VOICE_BUTTON)
                self.engine_voice_value = self.get_control_label(
                        clz.SELECT_VOICE_VALUE_LABEL)

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
            If there are many voices, then use multi-stage selection. Pick the 
            language/country (en-us) then use another 'voice' button to
            choose the specific voice. For now, it is ignored.
            """
            self.engine_language_button.setLabel(
                    MessageId.LANG_VARIANT_BUTTON.get_msg())
            self.refresh_engine_language_value()

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
                self.engine_voice_button.setLabel(
                        MessageId.SELECT_VOICE_BUTTON.get_msg())
                self.engine_voice_group.setVisible(True)
                self.engine_voice_value.setLabel(self.get_language(label=True))
                MY_LOGGER.debug(f'engine_voice_value: '
                                f'{self.engine_voice_value.getLabel()}')

            if not SettingsMap.is_valid_property(self.engine_id,
                                                 SettingsProperties.GENDER):
                self.engine_gender_group.setVisible(False)
            else:
                self.engine_gender_button.setLabel(
                        Messages.get_msg(Messages.SELECT_VOICE_GENDER))
                try:
                    gender: Genders = Settings.get_gender(self.engine_id)
                    self.engine_gender_value.setLabel(gender.name)
                    self.engine_gender_group.setVisible(True)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    MY_LOGGER.exception('')

            # TODO: Get pitch working again
            #  self.set_pitch_field(update_ui=True, engine_id=self.engine_id,
            #                      pitch=Settings.get_pitch(engine_id=self.engine_id))

            # NOTE: player and module share control. Only one active at a
            #       time. Probably should create two distinct buttons and
            #       control visibility

            #   TODO:   !!!!!
            # Move to where player or module are about to be displayed

            if SettingsMap.is_valid_property(self.engine_id,
                                             SettingsProperties.PLAYER):
                self.engine_player_button.setLabel(
                        MessageId.SELECT_PLAYER.get_msg())
                self.set_player_field(update_ui=True,
                                      engine_id=self.engine_id,
                                      player_id=Settings.get_player_id())
            else:
                self.engine_player_button.setLabel(
                        Messages.get_msg(Messages.SELECT_MODULE))
                self.engine_module_value.setLabel(self.get_module())
                self.engine_module_value.setVisible(True)

            self.engine_player_group.setVisible(True)
            self.engine_player_button.setVisible(True)

            self.engine_cache_speech_radio_button.setLabel(
                    Messages.get_msg(Messages.CACHE_SPEECH))

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

            # self.engine_api_key_label = self.get_control_label(
            #         clz.SELECT_API_KEY_LABEL)
            # self.engine_api_key_label.setLabel(util.T(32233))
            # self.engine_api_key_edit.setLabel(
            #         Messages.get_msg(Messages.API_KEY))

            speed: float = Settings.get_speed()
            self.set_speed_field(update_ui=True, speed=speed)
            result: UIValues = self.get_volume_range()
            self.set_volume_field(update_ui=True, volume=result.current)

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
            self.validate_and_set_lang_field()
            self.set_voice_field(update_ui=True)
            # self.set_gender_field() # Not that useful at this time.
            # Player and player_mode are inter-dependent
            # Speed, volume and pitch are also closely related to player, but not as
            # much as player/player-mode
            self.set_player_mode_field(update_ui=True)
            if SettingsMap.is_valid_property(self.engine_id, SettingsProperties.PLAYER):
                self.set_player_field(update_ui=True)
            elif SettingsMap.is_valid_property(self.engine_id, SettingsProperties.MODULE):
                self.set_module_field()
            self.set_pitch_range()
            self.set_speed_range()
            self.set_volume_range()
            self.set_api_field()
            # self.set_pipe_audio_field()
            self.set_cache_speech_field(update_ui=True)
            # TTSService.onSettingsChanged()
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
        self.save_settings(msg='on entry BEFORE doModal', initial_frame=True)
        # settings saved in individual methods just before changes made
        self.is_modal = True
        super().doModal()
        self.is_modal = False
        # Discard all uncommitted changes
        self.restore_settings(msg='doModal exit', initial_frame=True)
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
        self.save_settings(msg='on entry BEFORE doModal', initial_frame=True)
        super().show()
        # Discard all uncommitted changes
        self.restore_settings(msg='show exit', initial_frame=True)

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
                self.close()

            elif controlId == self.DEFAULTS_BUTTON:
                MY_LOGGER.debug(f'defaults button')
                self.select_defaults()

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
            # Make sure that Settings stack depth is the same as when this module
            # was entered (should be 2).
            self.restore_settings('enter select_engine BEFORE do_modal')
            MY_LOGGER.debug(f'After reset: {Settings.get_engine_id()}')
            self.save_settings('select_engine enter BEFORE do_modal')
            choices, current_choice_index = self.get_engine_choices()
            choices: List[Choice]
            if current_choice_index < 0:
                current_choice_index = 0
            MY_LOGGER.debug(f'# choices: {len(choices)} current_choice_idx: '
                            f'{current_choice_index}')
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
            # Revert all changes made during SelectionDialog
            self.restore_settings(msg='select_engine after doModal')  # Pops one
            # Get selected index
            idx = dialog.close_selected_idx
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

            choice: Choice = choices[idx]
            if choice is not None:
                self.configure_engine(choice)
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
        if choice is None:
            return
        try:
            self.configure_engine(choice)
        except Exception as e:
            MY_LOGGER.exception('')

    def configure_engine(self, choice: Choice) -> None:
        """
        Configures an engine with basic settings (player, etc.). Common code
        for select_engine and voice_engine.

        :param choice: Selected engine
        :return:
        """
        try:
            engine_id: str = choice.engine_id

            # See if we can configure engine
            engine_config: EngineConfig | None = None

            # This HACK provides a means to provide a limited set of
            # audio messages that is shipped with the addon. These
            # messages are used when either no engine or no player can
            # be configured. These messages are voiced using Kodi SFX
            # internal player. The messages should help the user install/
            # configure an engine or player. See:
            # GENERATE_BACKUP_SPEECH, sfx_audio_player, no_engine and voicecache

            player_mode: PlayerMode | None = None
            player_id: str | None = None
            engine_audio: AudioType | None = None
            use_cache: bool | None = None
            if GENERATE_BACKUP_SPEECH:
                player_mode = PlayerMode.FILE
                player_id = PlayerType.SFX.value
                engine_audio = AudioType.WAV
                use_cache = True

            engine_config: EngineConfig | None = None
            try:
                engine_config = self.configure_player(engine_id=engine_id,
                                                      use_cache=use_cache,
                                                      player_id=player_id,
                                                      engine_audio=engine_audio,
                                                      player_mode=player_mode)
            except ConfigurationError:
                MY_LOGGER.exception('Config Error')
                return

            MY_LOGGER.debug(f'engine_config: engine_id: {engine_config.engine_id} '
                            f'use_cache: {engine_config.use_cache} '
                            f'player_id: {engine_config.player_id} '
                            f'engine_audio: {engine_config.engine_audio} '
                            f'player_mode: {engine_config.player_mode} '
                            f'transcoder: {engine_config.transcoder} '
                            f'trans_audio_in: {engine_config.trans_audio_in} '
                            f'trans_audio_out: {engine_config.trans_audio_out}')
            lang_info: LanguageInfo = choice.lang_info
            self.set_lang_fields(update_ui=True,
                                 lang_info=lang_info,
                                 engine_id=engine_id)
            self.set_gender_field(update_ui=True, engine_id=engine_id)
            self.set_cache_speech_field(update_ui=True,
                                        engine_id=engine_id,
                                        use_cache=engine_config.use_cache)
            self.set_player_mode_field(update_ui=True,
                                       engine_id=engine_id,
                                       player_mode=engine_config.player_mode)
            self.set_player_field(update_ui=True,
                                  engine_id=engine_id,
                                  player_id=engine_config.player_id)
            Settings.set_converter(engine_config.transcoder, engine_id)
            self.set_speed_field(update_ui=True,
                                 speed=1.0)

            self.set_volume_field(update_ui=True,
                                  volume=0.0)
            self.set_engine_field(update_ui=True,
                                  engine_id=engine_id)
        except Exception:
            MY_LOGGER.exception('')

    def validate_and_set_lang_field(self, lang_id: str | None = None,
                                    engine_id: str | None = None) -> None:
        """
        Configures the Language Variant UI field, processing the related settings
        and resolving any incompatibility issues with other settings.

        :param lang_id:
        :param engine_id:
        :return:
        """
        try:
            if engine_id is None:
                engine_id = self.engine_id
            if lang_id is None:
                lang_id = Settings.get_language(engine_id)
            lang_voice_id: str = Settings.get_voice(engine_id)
            choices: List[Choice]
            # The language setting will always have the same language ('en')
            # as Kodi since Kodi is the source of all messages to be voiced.
            # The territory and voice can be different, as long as the variants
            # are not too far different.
            ietf_lang: langcodes.Language
            _, _, _, ietf_lang = LanguageInfo.get_kodi_locale_info()

            # lang_id = None causes the language code ('en') to come from
            # LanguageInfo.get_kodi_locale_info()
            lang_variant: LanguageInfo
            lang_variant = LanguageInfo.get_entry(engine_id=engine_id,
                                                  engine_voice_id=lang_voice_id,
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
                                f'service_id: {engine_id}  lang_id: '
                                f'{lang_id} lang_voice_id: '
                                f'{lang_voice_id}\n'
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

        All settings changes are applied to the current frame of the Settings
        stack. Only when the SettingsDialog is exited via the OK button are
        they committed to settings.xml and available to the rest of kodi TTS.

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
            engine_id: str = self.engine_id
            # Gets every language variant for the current engine and language
            # Sorted first by closeness of match to native language variant
            # and second by variant name.
            choices, current_choice_index = SettingsHelper.get_language_choices(
                    engine_id=engine_id,
                    get_best_match=False,
                    format_type=FormatType.LONG)
            if len(choices) == 0:
                # Do NOT change UI. These values will not be committed
                MY_LOGGER.debug(f'No language choices found. No changes made')
                return
            self.save_current_choices(choices, current_choice_index)
            #  MY_LOGGER.debug(f'In select_language # choices: {len(choices)} '
            #                     f'current_choice_idx {current_choice_index} '
            #                     f'current_choice: {choices[current_choice_index]}')
            current_locale: str
            kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
                LanguageInfo.get_kodi_locale_info()
            kodi_lang: str
            kodi_locale: str
            locale_name: str
            kodi_language: langcodes.Language
            lang_name: str = LanguageInfo.get_translated_language_name(kodi_language)
            engine_name: str = LanguageInfo.get_translated_engine_name(engine_id)
            title: str
            title = MessageId.AVAIL_VOICES_FOR_LANG.get_formatted_msg(
                    lang_name, engine_name)
            sub_title: str
            sub_title = (MessageId.DIALOG_LANG_SUB_HEADING.get_msg())
            self.restore_settings(msg='select_language BEFORE do_modal')
            self.save_settings('select_language BEFORE do_modal')
            MY_LOGGER.debug(f'sub_title: {sub_title}')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           sub_title=sub_title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=self.voice_language,
                                           disable_tts=True)
            dialog.doModal()
            # Restore to state prior to SelectionDialog
            self.restore_settings(msg='select_language AFTER doModal')

            # Now, apply any desired changes
            idx = dialog.close_selected_idx
            if idx < 0:  # No selection made or CANCELED
                return

            choice: Choice = choices[idx]
            if choice is not None:
                lang_info: LanguageInfo = choice.lang_info
                if lang_info is not None:
                    self.set_lang_fields(update_ui=True,
                                         lang_info=choice.lang_info,
                                         engine_id=engine_id)
                    MY_LOGGER.debug(f'engine: {engine_id} '
                                    f'language: {choice.lang_info.engine_lang_id}'
                                    f' voice: {choice.lang_info.engine_voice_id}')
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
        engine_id: str = self.engine_id
        # gets the language_id, a unique id for the focused language
        # and the matching engine.
        if choice is not None:
            lang_info: LanguageInfo = choice.lang_info
            MY_LOGGER.debug(f'CHOICE idx: {choice.value} lang: '
                            f'{lang_info.ietf.to_tag()}')
            if lang_info is not None:
                current_lang: LanguageInfo
                #   TODO: this is pretty crude.
                choices, current_selection_idx = self.retrieve_current_choices()
                choices: List[Choice]
                current_selection_idx: int
                current_choice: Choice = choices[selection_idx]
                self.set_lang_fields(update_ui=False,
                                     lang_info=current_choice.lang_info,
                                     engine_id=engine_id)
                voice: str = lang_info.engine_voice_id
                voice_label: str = lang_info.translated_voice
                self.set_voice_field(update_ui=False, engine_id=engine_id,
                                     voice_id=voice, voice_label=voice_label)
                self.set_speed_field(update_ui=False,
                                     speed=1.0)  # Speed of 1x

    def get_voice_choices(self, engine_id: str) -> Tuple[List[Choice], int]:
        """
            Creates a list of voices for the current language and engine
            in a format suitable for the SelectionDialog
        :param engine_id: engine_id to get voice choices for
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
                    engine_id,
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
            engine_id: str = self.engine_id
            choices: List[Choice]
            choices, current_choice_index = self.get_voice_choices(engine_id=engine_id)
            title: str = MessageId.SELECT_VOICE_BUTTON.get_msg()
            sub_title = 'Is this a sub_title for select_voice?'

            self.restore_settings(msg='select_voice enter BEFORE doModal')
            self.save_settings('select_voice BEFORE doModal')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           sub_title=sub_title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings(msg='select_voice AFTER doModal')

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
            Settings.set_voice(choice.value, engine_id=engine_id)
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
    '''
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
    '''

    def set_pitch_range(self):
        """

        """
        return
    '''
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
    '''

    def get_gender_choices(self, engine_id) -> Tuple[List[Choice], int]:
        """
        Gets gender choices for the given engine_id, if any

        :param engine_id: Identifies which engine's settings to work with
        :return:
        """
        MY_LOGGER.debug('FOOO get_gender_choices')

        current_value: Genders = Settings.get_gender(engine_id)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'gender: {current_value}')
        current_choice_index = -1
        choices: List[Choice] = []
        try:
            if not SettingsMap.is_valid_property(engine_id, SettingsProperties.GENDER):
                return choices, current_choice_index

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
            self.restore_settings(msg='select_gender BEFORE doModal')
            self.save_settings('select_gender BEFORE doModal')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings(msg='select_gender AFTER doModal')
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
            self.restore_settings(msg='select_player BEFORE doModal')
            self.save_settings('select_player BEFORE doModal')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           sub_title=sub_title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings(msg='select_player AFTER doModal')
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
            player_mode = Settings.get_player_mode(engine_id)
            engine_config: EngineConfig | None = None
            try:
                engine_config = self.configure_player(engine_id=engine_id,
                                                      use_cache=None,
                                                      player_id=player_id,
                                                      engine_audio=None,
                                                      player_mode=None)
            except ConfigurationError:
                MY_LOGGER.exception('Config Error')
                return None

            MY_LOGGER.debug(f'engine_config: engine_id: {engine_config.engine_id} '
                            f'use_cache: {engine_config.use_cache} '
                            f'player_id: {engine_config.player_id} '
                            f'engine_audio: {engine_config.engine_audio} '
                            f'player_mode: {engine_config.player_mode} '
                            f'transcoder: {engine_config.transcoder} '
                            f'trans_audio_in: {engine_config.trans_audio_in} '
                            f'trans_audio_out: {engine_config.trans_audio_out}')
            # MY_LOGGER.debug(f'Setting engine: {engine_id} '
            #                 f'player_mode: {player_mode} '
            #                 f'values: {allowed_values}')
            self.set_player_mode_field(update_ui=True,
                                       engine_id=engine_id,
                                       player_mode=engine_config.player_mode)
            #  self.engine_player_value.setLabel(player_label)
            self.set_player_field(update_ui=True,
                                  engine_id=engine_id,
                                  player_id=engine_config.player_id)
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
            self.restore_settings(msg='select_module BEFORE doModal')
            self.save_settings('select_module BEFORE doModal')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings(msg='select_module AFTER doModal')
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
        Configures the global volume of all engines
        """
        try:
            volume: float = self.engine_volume_slider.getFloat()
            self.set_volume_field(update_ui=True, volume=volume)
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
                    self.set_volume_field(update_ui=True, volume=volume)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_volume_range(self) -> UIValues:
        """

        :return:
        """
        result: UIValues | None = None
        try:
            result = self.volume_val.get_tts_values()
        except NotImplementedError:
            result = UIValues()
            MY_LOGGER.exception(f'service_id: {self.engine_id} volume: {result}')
        return result

    def select_volume(self) -> None:
        """
        Configures the global volume of all engines
        """
        try:
            volume: float = self.engine_volume_slider.getFloat()
            self.set_volume_field(update_ui=True, volume=volume)
        except Exception as e:
            MY_LOGGER.exception('')

    def select_speed(self):
        """

        """
        try:
            speed: float = self.engine_speed_slider.getFloat()
            self.set_speed_field(update_ui=True, speed=speed)
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
                    self.set_speed_field(update_ui=True, speed=speed)
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

    def select_player_mode(self):
        """
        Presents user with UI to change Player Mode and updates Settings and
        UI accordingly.
        :return:
        """
        try:
            choices: List[Choice]
            choices, current_choice_index = self.get_player_mode_choices()
            if current_choice_index < 0:
                current_choice_index = 0
            title: str = Messages.get_msg(Messages.SELECT_PLAYER_MODE)
            self.restore_settings(msg='select_player_mode BEFORE doModal')
            self.save_settings('select_player_mode BEFORE doModal')
            dialog: SelectionDialog
            dialog = self.selection_dialog(title=title,
                                           choices=choices,
                                           initial_choice=current_choice_index,
                                           call_on_focus=None)
            dialog.doModal()
            self.restore_settings(msg='select_player AFTER doModal')

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
                self.set_player_mode_field(update_ui=True,
                                           engine_id=self.engine_id,
                                           player_mode=new_player_mode)
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

    def configure_player(self, engine_id: str | None = None,
                         use_cache: bool | None = None,
                         player_id: str | None = None,
                         engine_audio: AudioType | None = None,
                         player_mode: PlayerMode | None = None) -> EngineConfig:
        """
        Configure a player and related settings for the given engine.
        The proposed configuration is returned.

        :param engine_id: REQUIRED. Specifies the engine being configured
        :param use_cache: If non-None, forces use or disuse of cache
        :param player_id: If non-None, forces to use a specific player
        :param engine_audio: If non-None, will cause audio to be produced in
                             the specified format (mp3 or wave) using a transcoder,
                             if needed.
        :param player_mode: If non-None, forces player mode to match
        :return:
        :raises ConfigurationError: if no valid configuration can be made
        """

        """
        Configuring a player can get messy because the engine, player,
        any cache, player_mode (depends on engine and player capabilities),
        transcoder, and audio type (wave/mp3/other). If use_cache is the default
        value None, then there is a strong bias to use caching. There is also 
        a strong bias to only cache mp3 files (due to the size of wave files). 
        If player_mode is None, then there is a bias to return PlayerMode.SLAVE_FILE
        and a player that can use it.

        Rough outline:
          If using internal engine player, then your decisions are
          complete. The default is to use internal player if available.

          If GENERATE_BACKUP_SPEECH (not done by users) is set, then use_cache
          will be True, audio_type will be .wav and player_id will be SFX.
          This will force wave files to be generated and placed in the cache. 
          
          Otherwise, with use_cache and audio_type = None, then a configuration
          will be returned that specifies use_cache=True and the first player found
          that can accept mp3 and any specified player_mode will be returned. 
          If a transcoder is needed to convert to mp3 then one will be chosen and
          returned.

          If no match can be made, then raise ConfigurationError
        """
        val: IStringValidator
        val = SettingsMap.get_validator(engine_id,
                                        SettingsProperties.PLAYER)
        engine_config: EngineConfig | None = None
        engine_audio_types: List[AudioType]
        engine_audio_types = SoundCapabilities.get_output_formats(engine_id)

        pm_val: IStringValidator
        pm_val = SettingsMap.get_validator(engine_id,
                                           SettingsProperties.PLAYER_MODE)
        pm_default: PlayerMode
        pm_default = PlayerMode(pm_val.default_value)
        if player_mode is None:
            player_mode = pm_default
        elif not pm_val.validate(player_mode)[0]:  # Returns (state, player_mode)
            MY_LOGGER.debug(f'PlayerMode: {player_mode} incompatible with '
                            f'engine {engine_id}. Using default: {pm_default}')
            player_mode = pm_default

        # First, handle the case where the engine also voices

        if player_mode == PlayerMode.ENGINE_SPEAK:
            if player_id is None:
                player_id = PlayerType.INTERNAL.value
            if player_id != PlayerType.INTERNAL.value:
                MY_LOGGER.debug(f'Engine configured for ENGINE_SPEAK but player '
                                f'configured for {player_id}. Ignoring player.')
                player_id = PlayerType.INTERNAL.value
            if use_cache is None:
                use_cache = False
            if use_cache:
                MY_LOGGER.debug('Engine configured for ENGINE_SPEAK and '
                                'set to use_cache. Ignoring use_cache')
                use_cache = False

            engine_config = EngineConfig(engine_id=engine_id,
                                         use_cache=False,
                                         player_id=player_id,
                                         engine_audio=None,
                                         player_mode=player_mode,
                                         transcoder=None,
                                         trans_audio_in=None,
                                         trans_audio_out=None)
            MY_LOGGER.debug(f'player_mode: {player_mode} '
                            f'engine_config.player_mode: '
                            f'{engine_config.player_mode}')
            return engine_config

        # Second, Handle the case where the player is specified. Check validity
        # and possibly a need for a transcoder

        MY_LOGGER.debug(f'player_id: {player_id}')
        if player_id is not None:
            ep_val: IStringValidator
            ep_val = SettingsMap.get_validator(engine_id,
                                               SettingsProperties.PLAYER)
            if not ep_val.validate(player_id)[0]:
                MY_LOGGER.debug(f'player {player_id} not valid for engine: {engine_id} '
                                f'Ignoring player.')
            else:
                # engine_audio is NOT a saved setting. Preference is to use mp3,
                # especially with caching.
                # Use mp3 if engine produces it.
                if engine_audio is None:
                    if AudioType.MP3 in engine_audio_types:
                        engine_audio = AudioType.MP3
                    else:
                        engine_audio = AudioType.WAV
                    MY_LOGGER.debug(f'engine_audio not specified. trying {engine_audio}')
                engine_config = self.verify_player(engine_id, engine_audio, player_id,
                                                   player_mode,
                                                   allow_player_mode_change=True,
                                                   use_cache=use_cache)
                if engine_config is None:
                    # See if a transcoder helps
                    trans_id: str | None = None
                    trans_audio_out: AudioType | None = None

                    if AudioType.MP3 not in engine_audio_types:
                        trans_audio_out = AudioType.MP3
                    elif AudioType.WAV not in engine_audio_types:
                        trans_audio_out = AudioType.WAV
                    if trans_audio_out is not None:
                        trans_id = self.find_transcoder(engine_id, trans_audio_out)
                        t_ecfg: EngineConfig | None
                        t_ecfg = self.verify_player(engine_id=engine_id,
                                                    engine_audio=engine_audio,
                                                    player_id=player_id,
                                                    player_mode=player_mode,
                                                    allow_player_mode_change=True,
                                                    use_cache=use_cache)
                        if t_ecfg is not None:
                            # Add info about transcoder
                            engine_config = EngineConfig(engine_id=t_ecfg.engine_id,
                                                         use_cache=t_ecfg.use_cache,
                                                         player_id=t_ecfg.player_id,
                                                         engine_audio=engine_audio,
                                                         player_mode=t_ecfg.player_mode,
                                                         transcoder=trans_id,
                                                         trans_audio_in=engine_audio,
                                                         trans_audio_out=trans_audio_out)

        if engine_config is None:
            # Did not work out, forget about the player_id that doesn't work,
            # then try every audio type that the engine produces, without
            # specifying player_id

            player_id = None
            MY_LOGGER.debug(f'engine_audio_types: {engine_audio_types}')
            for engine_audio_type in engine_audio_types:
                # Avoid putting .wav files in cache, unless explicitly
                # requested. Wave files require transcoder to .mp3 (except
                # GENERATE_BACKUP_SPEECH is set)
                t_use_cache: bool = use_cache
                if use_cache is None and engine_audio_type == AudioType.WAV:
                    t_use_cache = False
                MY_LOGGER.debug(f't_use_cache: {t_use_cache} audio_type: '
                                f'{engine_audio_type} engine: {engine_id}')
                engine_config = self.find_player(engine_id, engine_audio_type,
                                                 player_mode, t_use_cache)
                if engine_config is not None:
                    break

            if engine_config is None:
                # Perhaps a transcoder would help?
                trans_id: str | None = None
                trans_audio_out: AudioType | None = None
                if AudioType.MP3 not in engine_audio_types:
                    trans_audio_out = AudioType.MP3
                elif AudioType.WAV not in engine_audio_types:
                    trans_audio_out = AudioType.WAV
                MY_LOGGER.debug(f'trans_audio_out: {trans_audio_out}'
                                f' engine_id: {engine_id}')
                if trans_audio_out is not None:
                    trans_id = self.find_transcoder(engine_id, trans_audio_out)
                    if trans_id is None:
                        raise ConfigurationError('Can not find transcoder for'
                                                 f' engine: {engine_id}')
                    t_ecfg = self.find_player(engine_id, trans_audio_out,
                                              player_mode, use_cache)
                    if t_ecfg is not None:
                        # Add info about transcoder
                        engine_config = EngineConfig(engine_id=t_ecfg.engine_id,
                                                     use_cache=t_ecfg.use_cache,
                                                     player_id=t_ecfg.player_id,
                                                     engine_audio=engine_audio,
                                                     player_mode=t_ecfg.player_mode,
                                                     transcoder=trans_id,
                                                     trans_audio_in=engine_audio,
                                                     trans_audio_out=trans_audio_out)
            if engine_config is None:
                MY_LOGGER.debug(f'Can\'t find player for engine: {engine_id}')
                raise ConfigurationError(f'Can not find player for engine: {engine_id}')
        return engine_config

    def find_player(self, engine_id: str, engine_audio: AudioType,
                    player_mode: PlayerMode | None,
                    use_cache: bool | None) -> EngineConfig | None:
        """
        Searchs all players supported by the given engine for one that supports
        the given input_audio. The default player is searched first, otherwise
        they are searched in the order specified by the validator.

        This method is called under two circumstances: 1) When the user changes
        engines, 2) When the user changes some option for an engine.
        In the first case, the primary focus is to get a player that meets the
        requirements of the engine, but also supports caching. If no player is
        found, then the search can be retried with use_cache=False.

        In the second case, the engine has already been picked but the user
        wants to modify caching, player mode, etc. In this case player_mode
        and use_cache are specified to require matches on those values, narrowing
        the criteria.

        :param engine_id:
        :param engine_audio:
        :param player_mode: If not None,then the player_mode of player must match
        :param use_cache:
        :return:
        """

        """
        Look for the first player that:
          - player input audio type == engine output audio type
          - if engine's player_mode is specified and supports the players player_mode
          - supports caching
          - does not support caching and use_cache is False
        """
        MY_LOGGER.debug(f'engine_id: {engine_id} engine_audio: {engine_audio} '
                        f'player_mode: {player_mode} use_cache: {use_cache}')
        if engine_audio is None:
            MY_LOGGER.debug(f'engine_audio can not be None')
            return None
        engine_config: EngineConfig | None = None
        val: IStringValidator
        val = SettingsMap.get_validator(engine_id,
                                        SettingsProperties.PLAYER)
        default_player: str | None = val.default_value
        players: List[str] = [default_player]
        MY_LOGGER.debug(f'enabled allowed_values: {val.get_allowed_values(enabled=True)}')
        for player in val.get_allowed_values(enabled=True):
            player: AllowedValue
            if player.value != default_player:
                players.append(player.value)
        MY_LOGGER.debug(f'players: {players}')
        for player_id in players:
            engine_config = self.verify_player(engine_id=engine_id,
                                               engine_audio=engine_audio,
                                               player_id=player_id,
                                               player_mode=player_mode,
                                               allow_player_mode_change=False,
                                               use_cache=use_cache)
            if engine_config is not None:
                break
        return engine_config

    def verify_player(self, engine_id: str, engine_audio: AudioType,
                      player_id: str,
                      player_mode: PlayerMode | None = None,
                      allow_player_mode_change: bool = False,
                      use_cache: bool | None = None) -> EngineConfig | None:
        """
        Checks to see if the given configuration is a valid player for the given
        engine.

        :param engine_id: Can not be None
        :param engine_audio: Can not be None
        :param player_id: Can not be None
        :param player_mode: If None, then any player_mode is acceptable, otherwise,
                            the player_mode MUST match exactly, unless
                             allow_player_mode_change is True
        :param allow_player_mode_change: If True then the closest match to player_mode
                  will be returned
        :param use_cache:
        :return:
        """
        MY_LOGGER.debug(f'engine_id: {engine_id} engine_audio: {engine_audio} '
                        f'player_id: {player_id} player_mode: {player_mode} '
                        f'allow_player_mode_change: {allow_player_mode_change} '
                        f'use_cache: {use_cache}')
        if player_id is None:
            MY_LOGGER.debug(f'player_id can not be None')
            return None
        if engine_audio is None:
            MY_LOGGER.debug(f'engine_audio can not be None')
            return None

        best_match: PlayerMode | None = None
        engine_config: EngineConfig | None = None
        best_config: EngineConfig | None = None
        player_audio_types: List[AudioType]
        player_audio_types = SoundCapabilities.get_input_formats(player_id)
        if engine_audio in player_audio_types:
            MY_LOGGER.debug(f'player_id: {player_id} player_audio_types: '
                            f'{player_audio_types} engine_audio: {engine_audio.value}')
            em_val: StringValidator | IStringValidator
            em_val = SettingsMap.get_validator(engine_id, SettingsProperties.PLAYER_MODE)
            em_values: List[AllowedValue] = em_val.get_allowed_values(enabled=True)
            pm_val: StringValidator | IStringValidator
            pm_val = SettingsMap.get_validator(player_id,
                                               SettingsProperties.PLAYER_MODE)
            for pm_av in pm_val.get_allowed_values(enabled=True):
                pm_av: AllowedValue
                # Assumes that player modes are in preference order
                pm: PlayerMode
                pm = PlayerMode(pm_av.value)
                MY_LOGGER.debug(f'pm_av: {pm_av} em_values: {em_values}')
                engine_supports: bool = False
                for t in em_values:
                    t: AllowedValue
                    MY_LOGGER.debug(f't: {t} pm_av: {pm_av} equals: '
                                    f'{t == pm_av}')
                    if t == pm_av:
                        engine_supports = True
                        best_match = PlayerMode(t.value)
                        break
                if not engine_supports:
                    MY_LOGGER.debug(f'Engine does not support')
                    continue
                pc_val: BoolValidator | IBoolValidator
                pc_val = SettingsMap.get_validator(player_id,
                                                   SettingsProperties.CACHE_SPEECH)
                player_supports_cache: bool = False
                if player_mode == PlayerMode.ENGINE_SPEAK:
                    player_supports_cache = False
                    MY_LOGGER.debug(f'player_mode: {player_mode} supports_cache: '
                                    f'{player_supports_cache}')
                else:
                    player_supports_cache = pc_val.default_value
                    MY_LOGGER.debug(f'player_mode: {player_mode} player_supports_cache: '
                                    f'{player_supports_cache}')
                MY_LOGGER.debug(f'player_mode: {player_mode} '
                                f'player_supports_cache: '
                                f'{player_supports_cache}')
                if player_supports_cache and use_cache is None or use_cache:
                    engine_config = EngineConfig(engine_id=engine_id,
                                                 use_cache=True,
                                                 player_id=player_id,
                                                 engine_audio=engine_audio,
                                                 player_mode=pm,
                                                 transcoder=None,
                                                 trans_audio_in=None,
                                                 trans_audio_out=None)
                elif use_cache is None or not use_cache:
                    engine_config = EngineConfig(engine_id=engine_id,
                                                 use_cache=False,
                                                 player_id=player_id,
                                                 engine_audio=engine_audio,
                                                 player_mode=pm,
                                                 transcoder=None,
                                                 trans_audio_in=None,
                                                 trans_audio_out=None)
                if engine_config is not None:
                    if pm == player_mode:
                        best_config = engine_config
                        break
                    if best_match is None:
                        best_match = pm
                        best_config = engine_config
                    elif PlayerMode.get_rank(pm) < PlayerMode.get_rank(best_match):
                        best_match = pm
                        best_config = engine_config
        if (not allow_player_mode_change and player_mode is not None and
                best_match is not None and best_match != player_mode):
            MY_LOGGER.debug(f'player_mode invalid: {player_mode} best_match:'
                            f' {best_match}')
            return None
        return best_config

    def find_transcoder(self, engine_id: str, trans_audio_out: AudioType) -> str | None:
        """

        :param engine_id:
        :param trans_audio_out:
        :return: transcoder id Or None
        """
        MY_LOGGER.debug(f'trans_audio_out: {trans_audio_out}'
                        f' engine_id: {engine_id}')
        tran_id: str | None = None
        if trans_audio_out is not None:
            try:
                tran_id = SoundCapabilities.get_transcoder(
                        target_audio=trans_audio_out,
                        service_id=engine_id)
            except ValueError:
                MY_LOGGER.debug(f'Can\'t find transcoder for engine:'
                                f' {engine_id}')
                tran_id = None
        return tran_id

    def set_engine_field(self,
                         update_ui: bool,
                         engine_id: str = None) -> None:
        """
        Saves the given engine_id in Settings. Optionally updates the UI
        engine and language names.

        :param update_ui: If True, then the UI is updated to reflect the
        engine_id
        :param engine_id: If None, then engine_id is populated with the current
        engine_id from Settings.get_engine_id. Updates Settings with the value
        of engine_id (yeah, it can just update Settings with the same engine_id
        that it just read).
        :return:
        """
        if engine_id is None:
            engine_id = Settings.get_engine_id()
        if update_ui:
            kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
                LanguageInfo.get_kodi_locale_info()
            kodi_lang: str
            kodi_locale: str
            locale_name: str
            kodi_language: langcodes.Language
            engine_name: str = LanguageInfo.get_translated_engine_name(engine_id)
            lang_name: str = LanguageInfo.get_translated_language_name(kodi_language)
            self.engine_engine_value.setLabel(engine_name)
            self.engine_language_value.setLabel(lang_name)

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'engine_language_value: '
                            f'{self.engine_language_value.getLabel()}')

        from service_worker import TTSService

        # Do NOT try to skip initTTS by using:
        # current_engine_id: str = TTSService.get_instance().tts.engine_id
        # if engine_id != current_engine_id:
        # The reason is that TTSService's engine instance may NOT be
        # the same as Settings engine_id. In particular, this occurs when:
        #   voice_engine is giving a pre-view of how an engine sounds
        #   The user likes the engine and selects it (presses enter or OK)
        #   voice_engine returns to select_engine, which pops the temporary
        #   settings stack causing all settings to revert to their previous
        #   values. However, TTS engine instance is still running with the
        #   same engine that the user selected.
        # In short: don't depend on the TTSService engine instance to be the
        # same as what is in Settings

        PhraseList.set_current_expired()  # Changing engines
        # Sets the engine id and switch to use it. Expensive
        from service_worker import TTSService
        TTSService.get_instance().initTTS(engine_id)

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
        try:
            # Make sure that Settings stack depth is the same as when this module
            # was entered (should be 2).
            self.restore_settings('enter select_defaults')
            choices, current_choice_index = self.get_engine_choices()
            choices: List[Choice]
            if current_choice_index < 0:
                current_choice_index = 0
            MY_LOGGER.debug(f'# choices: {len(choices)} current_choice_idx: '
                            f'{current_choice_index}')
            # The first engine listed should be the best available and universal
            # (GoogleTTS)
            idx = 0
            MY_LOGGER.debug_v(f'SelectionDialog value: '
                              f'{MessageId.TTS_ENGINE.get_msg()} '
                              f'idx: {str(idx)}')
            if idx < 0:  # No selection made or CANCELED
                return

            choice: Choice = choices[idx]
            if choice is not None:
                self.configure_engine(choice)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_player_field(self, update_ui: bool,
                         engine_id: str | None = None,
                         player_id: str | None = None) -> None:
        """
        Updates player_id.engine_id Settings and optionally the UI.

        :param update_ui: if True, then the UI is updated as well as Settings.
                          otherwise, Settings player_id will be updated.
        :param engine_id: identifies which engine the settings belong to. If
                          None, then the current engine is used
        :param player_id: identifies the player_id to set. If None, then
                          the current player_id for engine_id will be 'updated'

        :return:
        """
        try:
            if update_ui is None:
                raise ValueError('update_ui must have a value')
            if engine_id is None:
                engine_id = Settings.get_engine_id()
            if player_id is None:
                player_id = Settings.get_player_id()

            player: PlayerType = PlayerType(player_id)
            player_str: str = player.label
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting player to {player_id}')
            Settings.set_player(value=player_id, engine_id=engine_id)
            if update_ui:
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

    def set_player_mode_field(self, update_ui: bool,
                              engine_id: str | None = None,
                              player_mode: PlayerMode | None = None) -> None:
        """
        Updates player_mode.engine_id Settings and optionally the UI.

        :param update_ui: if True, then the UI is updated as well as Settings.
                          otherwise, Settings player_id will be updated.
        :param engine_id: identifies which engine the settings belong to. If
                          None, then the current engine is used
        :param player_mode: identifies the player_mode to set. If None, then
                          the current player_mode for engine_id will be 'updated'
        :return:
        """
        try:
            if engine_id is None:
                engine_id = Settings.get_engine_id()
            if player_mode is None:
                player_mode = Settings.get_player_mode(engine_id)
            player_mode_str: str = player_mode.translated_name
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting player mode to {player_mode_str}')

            Settings.set_player_mode(player_mode=player_mode, engine_id=engine_id)
            if update_ui:
                self.engine_player_mode_label.setLabel(player_mode_str)
                self.engine_player_mode_button.setVisible(True)
                self.engine_player_mode_label.setVisible(True)
                self.engine_player_mode_group.setVisible(True)
        except NotImplementedError:
            self.engine_player_mode_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def refresh_engine_language_value(self):
        """
        TODO: Merge with set_lang_field
        Updates the GUI language value.
        :return:
        """
        lang_info: LanguageInfo = LanguageInfo.get_entry()
        voice: str = ''
        if lang_info is None:
            voice = 'unknown'
        else:
            voice = lang_info.translated_voice
        self.engine_language_value.setLabel(voice)

    def set_lang_fields(self, update_ui: bool = False,
                        lang_info: LanguageInfo | None = None,
                        engine_id: str | None = None) -> None:
        """
        Configures the Language Variant UI field and update settings. No
        validation is performed

        :param update_ui: When True, update UI and Settings, otherwise just
                          update Settings
        :param lang_info:
        :param engine_id:
        :return:
        """
        try:
            MY_LOGGER.debug('FOOO set_lang_field')
            lang_id: str | None = None
            voice_id: str | None = None
            if engine_id is None:
                raise ValueError('engine_id value required')
            if lang_info is None:
                raise ValueError('lang_info value required')
            lang_id = lang_info.engine_lang_id
            voice_id = lang_info.engine_voice_id
            voice_name: str = lang_info.translated_voice

            Settings.set_language(lang_id, engine_id)
            Settings.set_voice(voice_id, engine_id)

            if update_ui:
                visible: bool = lang_id != SettingsProperties.UNKNOWN_VALUE
                self.engine_language_group.setVisible(visible)
                self.engine_language_value.setEnabled(visible)
                self.engine_language_value.setLabel(voice_name)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_voice_field(self, update_ui: bool,
                        engine_id: str | None = None,
                        voice_id: str | None = None,
                        voice_label: str | None = None) -> None:
        """
        Updates the voice field with the value that the current engine is
        using. The voice can be changed by the user selecting the asociated
        button.
        :param update_ui: If True, the UI is updated to reflect the changes
        :param engine_id: Identifies the engine that will have its voice modified
        :param voice_id: New value to assign to the engine's voice
        :param voice_label: translated label for voice_id
        :return:
        """
        clz = type(self)
        try:
            MY_LOGGER.debug('FOOO set_voice_field')
            if engine_id is None:
                engine_id: str = self.engine_id
            has_voice: bool
            has_voice = SettingsMap.is_valid_property(engine_id,
                                                      SettingsProperties.VOICE)
            if has_voice:
                has_voice = SettingsMap.is_setting_available(engine_id,
                                                             SettingsProperties.VOICE)
            if not has_voice:
                if update_ui:
                    self.engine_voice_group.setVisible(False)
                    return

            choices: List[Choice] = []
            if voice_id is None:
                choices, current_choice_index = self.get_voice_choices(engine_id)
                if current_choice_index < 0:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'choice out of range: {current_choice_index} '
                                        f'# choices: {len(choices)}')
                    current_choice_index = 0

                if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                    if update_ui:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'setting voice disabled:'
                                            f' {self.engine_voice_value}')
                        self.engine_voice_value.setEnabled(False)
                        self.engine_voice_value.setLabel(
                                Messages.get_msg(Messages.UNKNOWN))
                    return

                choice: Choice = choices[current_choice_index]
                voice_id = choice.lang_info.engine_voice_id
                voice_label = choice.label
            Settings.set_voice(voice_id, engine_id)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting voice to: {voice_id}')

            MY_LOGGER.debug(f'voice label: {voice_label}')
            if update_ui:
                self.engine_voice_value.setLabel(voice_label)
                if len(choices) < 2:
                    self.engine_voice_value.setEnabled(False)
                else:
                    self.engine_voice_value.setEnabled(True)

                self.engine_voice_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_cache_speech_field(self, update_ui: bool,
                               engine_id: str | None = None,
                               use_cache: bool | None = None) -> None:
        """
        Propagates cache_speech setting to Settings and the UI
        :param update_ui: If True, update the UI as well as Settings, otherwise,
                          only update Settings
        :param engine_id: Specifies the engine_id to update. If None, then the
                          current Settings.engine_id will be used
        :param use_cache: Specifies whether the engine is using a cache. If None,
                          then the current Settings.use_cache.engine_id value will
                          be used
        """
        try:
            if engine_id is None:
                engine_id = Settings.get_engine_id()
            if use_cache is None:
                use_cache = Settings.is_use_cache(engine_id)
            Settings.set_use_cache(use_cache, engine_id)
            if update_ui:
                self.engine_cache_speech_radio_button.setSelected(use_cache)
                self.engine_cache_speech_group.setVisible(True)
                self.engine_cache_speech_radio_button.setVisible(True)
        except NotImplementedError:
            self.engine_cache_speech_group.setVisible(False)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_speed_field(self, update_ui: bool,
                        speed: float) -> None:
        """
        Configures Settings.speed and optinally updates the UI. Note that
        the speed setting applies to ALL TTS engines, so engine_id is not
        required for this setting.

        :param update_ui: If True, then the UI is updated to reflect the new speed,
                          otherwise, the UI will not be updated
        :param speed: float value to set the speed to.
        """
        try:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting speed to: {speed}')
            self.speed_val.set_value(speed)
            if update_ui:
                # See set_speed_range for configuring the slider, which
                # should be configured once, except for visibility.
                # Speed is ignored by players that don't support it, such as
                # SFX.
                label: str = MessageId.SPEED.get_formatted_msg(f'{speed:.1f}')
                self.engine_speed_label.setLabel(label)
                self.engine_speed_group.setVisible(True)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_pitch_field(self, update_ui: bool,
                        engine_id: engine_id,
                        pitch: float) -> None:
        """
        Updates Settings.pitch and optionally the pitch UI.

        :param update_ui: If True, then update the pitch related UI elements
        :param engine_id: Identifies the engine which to update the pitch
        :param pitch: value to set
        :return:
        """
        if update_ui:
            # TODO: Temporarily disable all pitch adjustments. eSpeak supports pitch
            if True or not SettingsMap.is_valid_property(engine_id,
                                                         SettingsProperties.PITCH):
                self.engine_pitch_group.setVisible(False)
            else:
                label: str = MessageId.PITCH.get_formatted_msg(f'{pitch:.1f}')
                self.engine_pitch_label.setLabel(label)
                self.engine_pitch_group.setVisible(True)

    def set_volume_field(self, update_ui: bool,
                         volume: float) -> None:
        """
        Configures Settings.volume and optinally updates the UI. Note that
        the volume setting applies to ALL TTS engines, so engine_id is not
        required for this setting.

        :param update_ui: If True, then the UI is updated to reflect the new speed,
                          otherwise, the UI will not be updated
        :param volume: float value to set the volume to.
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Setting volume to {volume}')
        self.volume_val.set_value(volume)
        if update_ui:
            label = MessageId.VOLUME_DB.get_formatted_msg(f'{volume:.1f}')
            self.engine_volume_label.setLabel(label=label)
            self.engine_volume_group.setVisible(True)

    def set_gender_field(self, update_ui: bool, engine_id: str):
        """
        Sets the given engine's Gender field, if it has one. Also, updates
        the UI if requested.
        :param update_ui: If true, and this engine supports gender, then the UI
               will be updated to reflect the current gender
        :param engine_id: Identifies which engine's settings to work with

        Note that the current gender is calculated by choices made from selecting
        the voice (SUBJECT TO CHANGE).
        :return:
        """
        try:
            MY_LOGGER.debug('FOOO set_gender_field')
            choices: List[Choice]
            valid: bool = SettingsMap.is_valid_property(engine_id,
                                                        SettingsProperties.GENDER)
            MY_LOGGER.debug(f'service_id: {engine_id} GENDER valid: {valid}')
            if update_ui:
                if not valid:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Gender is not a valid property for '
                                        f'{engine_id}')
                    self.engine_gender_group.setVisible(False)
            else:
                choices, current_choice_index = self.get_gender_choices(engine_id)
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
                                                    choices=choices,
                                                    initial_choice=initial_choice,
                                                    sub_title=sub_title,
                                                    call_on_focus=call_on_focus,
                                                    call_on_select=call_on_select)
        else:
            clz._selection_dialog.update_choices(title=title,
                                                 choices=choices,
                                                 initial_choice=initial_choice,
                                                 sub_title=sub_title,
                                                 call_on_focus=call_on_focus,
                                                 call_on_select=call_on_select)
        return clz._selection_dialog

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
        Gets an engine instance regardless if it is the active engine or not.
        Does NOT cause the active engine to change to a different enngine.
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
        MY_LOGGER.debug(f'original_depth: {self.original_stack_depth} stack_depth: '
                        f'{SettingsManager.get_stack_depth()}')

    def save_settings(self, msg: str, initial_frame: bool = False) -> None:
        """
        Pushes a copy of the current settings 'frame' onto the stack of settings.
        restore_settings pops the stack frame, discarding all changes and reverting
        to the settings prior to save_settings

        :param msg: Text to add to debug msgs to give context
        :param initial_frame: When True, this creates the initial frame on each entry
                        to this class via doModal or show.
        :return:
        """
        try:
            if initial_frame:
                if self.original_stack_depth != -1:
                    MY_LOGGER.debug('INVALID initial state.')
                self.original_stack_depth = SettingsManager.get_stack_depth()
            MY_LOGGER.debug(f'{msg}\nBEFORE save_settings original_depth: '
                            f'{self.original_stack_depth} '
                            f'stack_depth: {SettingsManager.get_stack_depth()}')
            SettingsLowLevel.save_settings()
            MY_LOGGER.debug(f'{msg}\nAFTER save_settings original_depth: '
                            f'{self.original_stack_depth} '
                            f'stack_depth: {SettingsManager.get_stack_depth()}')
        except Exception as e:
            MY_LOGGER.exception('')

    def restore_settings(self, msg: str, initial_frame: bool = False,
                         settings_changes: Dict[str, Any] | None = None) -> None:
        """
        Wrapper around SettingsManager.restore_settings. The purpose is to
        get extra debug information reported in this module to make easier to spot
        in logs.

        Restore the Settings Stack by poping one or more frames.

        :param msg: Text to add to debug messages to give context
        :param initial_frame: True when this is the for the first frame created on entry
                              to this class via doModal or show. Otherwise,
                              a secondary frame is created/destroyed
        :param settings_changes: If not None, then apply these changes
                                 to stack_top
        """
        stack_depth: int = 0
        msg_1: str = ''
        msg_2: str = ''
        if initial_frame:
            # Remove all frames created by SettingsDialog
            msg_1 = f'{msg}\nExiting SettingsDialog BEFORE restore'
            msg_2 = f'{msg}\nExiting SettingsDialog AFTER restore'
            stack_depth = self.original_stack_depth
            if (SettingsManager.get_stack_depth() <
                    self.original_stack_depth):
                MY_LOGGER.warn(f'INVALID stack_depth:')
                return
            self.original_stack_depth = -1  # Ready for next call
        else:
            msg_1 = f'{msg}\nBEFORE restore'
            msg_2 = f'{msg}\nAFTER restore'
            stack_depth = self.original_stack_depth + 1
            # Don't let stack go below the original frame created when
            # entering SettingsDialog.
            if stack_depth == SettingsManager.get_stack_depth():
                # This occurs because a check is made before modifying
                # any setting to make sure that the stack is at the proper
                # depth.
                MY_LOGGER.debug(f'{msg}  already at the proper stack_depth: {stack_depth}')
                return
            if (stack_depth > SettingsManager.get_stack_depth() or
                    stack_depth < self.original_stack_depth):
                MY_LOGGER.warn(f'INVALID stack_depth: '
                               f'{SettingsManager.get_stack_depth()}')
                return
        MY_LOGGER.debug(f'{msg_1} to stack_depth: {stack_depth} current: '
                        f'{SettingsManager.get_stack_depth()}')
        SettingsManager.restore_settings(stack_depth=stack_depth)

        MY_LOGGER.debug(f'{msg_2} with stack_depth: '
                        f' {SettingsManager.get_stack_depth()}')
