# coding=utf-8
from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

import xbmc
import xbmcaddon

from common.logger import BasicLogger

module_logger = BasicLogger.get_logger(__name__)


class MessageId(Enum):
    # The following tree values MUST be the same as in VoiceHintToggle
    ENGINE_LABEL = 32001
    VOLUME_LABEL = 32014
    VOICE_HINT_OFF = 32050
    VOICE_HINT_ON = 32051
    VOICE_HINT_PAUSE = 32052
    DATABASE_SCAN_STARTED = 32100
    DATABASE_SCAN_FINISHED = 32101

    ITEM_WITH_NUMBER = 32106  # item {number}
    ITEMS_WITH_NUMBER = 32107  # {number} items

    GENDER_UNKNOWN = 32165
    TTS_ENGINE = 32181
    #  ENGINE_AUTO = 32184
    GENDER_MALE = 32212
    GENDER_FEMALE = 32213
    VOICE = 32216  # (As in Voice: <name of voice>)
    OK_BUTTON = 32220
    CANCEL_BUTTON = 32221
    DEFAULTS_BUTTON = 32222
    CHOOSE_TTS_ENGINE = 32224
    LANG_VARIANT_BUTTON = 32227
    VOICE_GENDER_BUTTON = 32228

    # Displays current voicing pitch, a simple float
    # Pitch: {0}
    PITCH = 32229
    SELECT_PLAYER = 32230

    # Displays current voicing speed, a simple float value
    # Speed: {0}
    SPEED = 32231
    VOLUME_DB = 32232
    ITEM = 32237  # item (use when you can't get the number)
    CONTAINER_ITEM_NUMBER_CONTROL_AND_VALUE = 32238
    BASIC_CONFIGURATION = 32239

    # Separates the reading of the heading and the value
    VALUE_PREFIX = 32240
    # Separates the reading of the heading and the value
    HEADING_VALUE_SEPARATOR = 32241  # {heading} value {value}
    SELECT_TTS_ENGINE = 32242
    SELECT_VOICE_FOR_ENGINE = 32243
    PLAYER_MODE_SLAVE_FILE = 32244
    PLAYER_MODE_SLAVE_PIPE = 32245
    PLAYER_MODE_FILE = 32246
    PLAYER_MODE_PIPE = 32247
    PLAYER_MODE_ENGINE_SPEAK = 32248
    SELECT_PLAYER_SUBTITLE = 32249

    ENGINE_ESPEAK = 32314
    ENGINE_FESTIVAL = 32315
    ENGINE_FLITE = 32316
    ENGINE_EXPERIMENTAL = 32323
    ENGINE_GOOGLE = 32324
    ENGINE_POWERSHELL = 32347
    ENGINE_RECITE = 32325
    ENGINE_RESPONSIVE_VOICE = 32317
    ENGINE_SAPI = 32329
    ENGINE_SPEECH_DISPATCHER = 32318
    ENGINE_INTERNAL = 32326
    ENGINE_LOG_ONLY = 32327
    CONVERT_PICO_TO_WAV = 32328
    # Voice a boolean control value as 'True' or 'False'
    TRUE = 32820
    FALSE = 32821
    ENGINE_PIPER = 32331
    ENGINE_NO_ENGINE = 32250

    PLAYER_NONE = 32304
    PLAYER_SFX = 32297
    PLAYER_WINDOWS = 32298
    PLAYER_APLAY = 32299
    PLAYER_PAPLAY = 32300
    PLAYER_AFPLAY = 32301
    PLAYER_SOX = 32302
    PLAYER_MPLAYER = 32303
    PLAYER_MPG321 = 32305
    PLAYER_MPG123 = 32306
    PLAYER_MPG321_OE_PI = 32307
    SELECT_VOICE_BUTTON = 32308
    PLAYER_BUILT_IN = 32313

    PLAYER_MPV = 32330

    MSG_NOT_FOUND_ERROR = 32335

    LIBRARY_CLEAN_START = 32340
    LIBRARY_CLEAN_COMPLETE = 32341
    SCREEN_SAVER_START = 32342
    SCREEN_SAVER_INTERRUPTED = 32343
    HEADING_WITH_ITEMS = 32344
    HEADING_WITH_ORIENTATION = 32345
    HEADING_WITH_ORIENTATION_AND_ITEMS = 32346

    # PLAYER_WAVE_HANDLER = -1
    # PLAYER_MP3_AUDIO_PLAYER_HANDLER = -1
    # PLAYER_BUILTINAUDIOPLAYERHANDLER = -1

    DIALOG_N_OF_M_ITEMS = 32714

    # "Choose the desired voice using Select/Enter"

    DIALOG_LANG_SUB_HEADING = 32715

    # Used as a Menu Heading to select a TTS engine and voice
    # Ex. Available Voices for English
    AVAIL_VOICES_FOR_LANG = 32716
    TTS_SETTINGS = 32720

    # Enabled on new install
    READ_HINT_TEXT_ON_STARTUP = 32812
    EXTENDED_HELP_ON_STARTUP = 32813
    TTS_HELP_LABEL = 32859
    TTS_HELP_CHOOSE_SUBJECT = 32856

    def get_msg(self) -> str:
        return MessageUtils.get_msg_by_id(self.value)

    def get_formatted_msg(self, *args: Optional[str | int | float]) -> str:
        return MessageUtils.get_formatted_msg_by_id(self.value,
                                                    *args)


class MessageUtils:

    @classmethod
    def get_msg(cls, msg_id: str | int | MessageId) -> str:
        msg: str = ''
        msg_num: int = -1

        if isinstance(msg_id, str) and msg_id.isdigit():
            msg_id = int(msg_id)
        if isinstance(msg_id, int):
            msg_num = msg_id
            try:
                msg: str = cls.get_msg_by_id(msg_num)
            except Exception as e:
                module_logger.exception('')
        else:
            try:
                msg_id: MessageId
                msg_num: int = msg_id.value
                msg: str = cls.get_msg_by_id(msg_num)
            except Exception as e:
                module_logger.exception('')
        return msg

    @classmethod
    def get_msg_by_id(cls, msg_id: int | MessageId, empty_on_error: bool = False) -> str:
        msg: str = ''
        msg_num: int = -1
        try:
            if isinstance(msg_id, int):
                msg_num = msg_id
            elif isinstance(msg_id, str) and msg_id.isdigit():
                msg_num = int(msg_id)
            else:
                message_id: MessageId = msg_id
                msg_num = message_id.value
            msg = xbmcaddon.Addon().getLocalizedString(msg_num)
            module_logger.debug(f'ADDON msg: {msg} msg_id: {msg_id} msg_num {msg_num}')
        except:
            module_logger.exception(f'ADDON msg: {msg} msg_id: {msg_id} msg_num: {msg_num}')
            msg = ''
        try:
            if msg == '':
                msg = xbmc.getLocalizedString(msg_num)
                module_logger.debug(f'msg: {msg} msg_id: {msg_id} msg_num: {msg_num}')
        except:
            module_logger.exception(f'msg: {msg} msg_id: {msg_id} msg_num: {msg_num}')
            msg = ''

        if msg == '' and empty_on_error:
            module_logger.debug(f'msg is empty and empty_on_error msg: {msg}')
            return msg

        if msg_num == 0:
            module_logger.debug(f'msg_id = 0')
        # else:
        #     module_logger.debug(f'Returning msg without error: {msg}')
        return msg

    @classmethod
    def get_error_msg(cls, msg_id: str | int | MessageId) -> str:
        msg_num: int = -1
        if isinstance(msg_id, int):
            msg_num = msg_id
        elif isinstance(msg_id, MessageId):
            msg_num = msg_id.value
        msg: str = f'Message {msg_num} not found in neither Kodi\'s nor ' \
                   'this addon\'s message catalog'
        return msg

    @classmethod
    def get_formatted_msg_by_id(cls, msg_id: str | int | MessageId,
                                *args: Optional[str]) -> str:
        """

        :param msg_id:
        :param args
        :return:
        """
        msg: str = ''
        msg_num: int = -1
        if isinstance(msg_id, int):
            msg_num = msg_id
        elif isinstance(msg_id, MessageId):
            msg_num = msg_id.value

        unformatted_msg = MessageUtils.get_msg_by_id(msg_num, empty_on_error=True)
        if unformatted_msg == '' or msg_num == 0:
            unformatted_msg = (f"Can not find message from Kodi's nor ADDON's "
                               "messages msg_id: {msg_num}")
            return unformatted_msg.format(*args)
        return unformatted_msg.format(*args)
