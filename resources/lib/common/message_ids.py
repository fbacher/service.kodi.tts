# coding=utf-8
from enum import Enum
from typing import Dict, Optional

import xbmc
import xbmcaddon

from backends.settings.service_types import Services
from common.logger import BasicLogger
from common.setting_constants import Players

module_logger = BasicLogger.get_logger(__name__)


class MessageId(Enum):
    # The following tree values MUST be the same as in VoiceHintToggle
    ENGINE_LABEL = 32001

    VOICE_HINT_OFF = 32050
    VOICE_HINT_ON = 32051
    VOICE_HINT_PAUSE = 32052
    DATABASE_SCAN_STARTED = 32100
    DATABASE_SCAN_FINISHED = 32101

    ITEM_WITH_NUMBER = 32106  # item {number}
    ITEMS_WITH_NUMBER = 32107  # {number} items

    ENGINE_AUTO_ID = 32184
    ITEM = 32237  # item (use when you can't get the number)
    CONTAINER_ITEM_NUMBER_CONTROL_AND_VALUE = 32238
    BASIC_CONFIGURATION = 32239

    # Separates the reading of the heading and the value
    VALUE_PREFIX = 32240
    # Separates the reading of the heading and the value
    HEADING_VALUE_SEPARATOR = 32241  # {heading} value {value}


    ENGINE_ESPEAK_ID = 32314
    ENGINE_FESTIVAL = 32315
    ENGINE_FLITE = 32316
    ENGINE_EXPERIMENTAL = 32323
    ENGINE_GOOGLE = 32324
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

    PLAYER_INTERNAL = 32313

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

    # "Begins with the closest match to current language."

    DIALOG_LANG_SUB_HEADING = 32715

    # Used as a Menu Heading to select a TTS engine and voice
    # Ex. Available Voices for English
    AVAIL_VOICES_FOR_LANG = 32716

    # Enabled on new install
    READ_HINT_TEXT_ON_STARTUP = 32812
    EXTENDED_HELP_ON_STARTUP = 32813
    TTS_HELP_LABEL = 32859

    def get_msg(self) -> str:
        return MessageUtils.get_msg_by_id(self.value)

    def get_formatted_msg(self, *args: Optional[str]) -> str:
        return MessageUtils.get_formatted_msg_by_id(self.value,
                                                    *args)

class MessageUtils:

    msg_id_lookup: Dict[str, int] = {
        # TTS :
        Services.AUTO_ENGINE_ID        : MessageId.ENGINE_AUTO_ID,
        Services.ESPEAK_ID             : MessageId.ENGINE_ESPEAK_ID,
        Services.FESTIVAL_ID           : MessageId.ENGINE_FESTIVAL,
        Services.FLITE_ID              : MessageId.ENGINE_FLITE,
        Services.EXPERIMENTAL_ENGINE_ID: MessageId.ENGINE_EXPERIMENTAL,
        Services.GOOGLE_ID             : MessageId.ENGINE_GOOGLE,
        Services.RECITE_ID             : MessageId.ENGINE_RECITE,
        Services.RESPONSIVE_VOICE_ID   : MessageId.ENGINE_RESPONSIVE_VOICE,
        Services.SAPI_ID               : MessageId.ENGINE_SAPI,
        Services.SPEECH_DISPATCHER_ID  : MessageId.ENGINE_SPEECH_DISPATCHER,
        Services.INTERNAL_PLAYER_ID    : MessageId.ENGINE_INTERNAL,
        Services.LOG_ONLY_ID           : MessageId.ENGINE_LOG_ONLY,
        Services.PICO_TO_WAVE_ID       : MessageId.CONVERT_PICO_TO_WAV,
        Services.PIPER_ID              : MessageId.ENGINE_PIPER,
        Players.NONE                   : MessageId.PLAYER_NONE,
        Players.SFX                    : MessageId.PLAYER_SFX,
        Players.WINDOWS                : MessageId.PLAYER_WINDOWS,
        Players.APLAY                  : MessageId.PLAYER_APLAY,
        Players.PAPLAY                 : MessageId.PLAYER_PAPLAY,
        Players.AFPLAY                 : MessageId.PLAYER_AFPLAY,
        Players.SOX                    : MessageId.PLAYER_SOX,
        Players.MPLAYER                : MessageId.PLAYER_MPLAYER,
        Players.MPV                    : MessageId.PLAYER_MPV,
        Players.MPG321                 : MessageId.PLAYER_MPG321,
        Players.MPG123                 : MessageId.PLAYER_MPG123,
        Players.MPG321_OE_PI           : MessageId.PLAYER_MPG321_OE_PI,
        Players.INTERNAL               : MessageId.PLAYER_INTERNAL
        # Players.WavAudioPlayerHandler : MessageId.PLAYER_WAVE_HANDLER,
        # Players.MP3AudioPlayerHandler : MessageId.PLAYER_MP3_AUDIO_PLAYER_HANDLER,
        # Players.BuiltInAudioPlayerHandler : MessageId.PLAYER_INTERNAL
    }

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
        elif isinstance(msg_id, str):
            try:
                msg_id_str: str = msg_id
                new_msg_id: int = cls.msg_id_lookup[msg_id_str]
                msg: str = cls.get_msg_by_id(new_msg_id)
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
        if isinstance(msg_id, str):
            msg_id_str: str = msg_id
            msg_num = cls.msg_id_lookup[msg_id_str]
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
        if isinstance(msg_id, str):
            msg_id_str: str = msg_id
            msg_num = cls.msg_id_lookup[msg_id_str]
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
