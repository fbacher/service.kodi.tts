# coding=utf-8
from enum import Enum
from typing import Dict, Optional

import xbmc
import xbmcaddon

from common.logger import BasicLogger
from common.setting_constants import Players

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class MessageId(Enum):

    ENGINE_AUTO_ID = 32184
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
    ENGINE_PIPER = 32331

    PLAYER_NONE = 32304
    PLAYER_SFX = 32297
    PLAYER_WINDOWS = 32298
    PLAYER_APLAY = 32299
    PLAYER_PAPLAY = 32300
    PLAYER_AFPLAY = 32301
    PLAYER_SOX = 32302
    PLAYER_MPLAYER = 32303
    PLAYER_MPV = 32330
    PLAYER_MPG321 = 32305
    PLAYER_MPG123 = 32306
    PLAYER_MPG321_OE_PI = 32307
    PLAYER_INTERNAL = 32313
    # PLAYER_WAVE_HANDLER = -1
    # PLAYER_MP3_AUDIO_PLAYER_HANDLER = -1
    # PLAYER_BUILTINAUDIOPLAYERHANDLER = -1

    MSG_NOT_FOUND_ERROR = 32335
    DIALOG_N_OF_M_ITEMS = 32714

    # "Begins with the closest match to current language."

    DIALOG_LANG_SUB_HEADING = 32715

    # Used as a Menu Heading to select a TTS engine and voice
    # Ex. Available Voices for English
    AVAIL_VOICES_FOR_LANG = 32716

class MessageUtils:

    msg_id_lookup: Dict[str, int] = {
        # TTS :
        Players.NONE        : MessageId.PLAYER_NONE,
        Players.SFX         : MessageId.PLAYER_SFX,
        Players.WINDOWS     : MessageId.PLAYER_WINDOWS,
        Players.APLAY       : MessageId.PLAYER_APLAY,
        Players.PAPLAY      : MessageId.PLAYER_PAPLAY,
        Players.AFPLAY      : MessageId.PLAYER_AFPLAY,
        Players.SOX         : MessageId.PLAYER_SOX,
        Players.MPLAYER     : MessageId.PLAYER_MPLAYER,
        Players.MPV         : MessageId.PLAYER_MPV,
        Players.MPG321      : MessageId.PLAYER_MPG321,
        Players.MPG123      : MessageId.PLAYER_MPG123,
        Players.MPG321_OE_PI: MessageId.PLAYER_MPG321_OE_PI,
        Players.INTERNAL:   MessageId.PLAYER_INTERNAL
        # Players.WavAudioPlayerHandler : MessageId.PLAYER_WAVE_HANDLER,
        # Players.MP3AudioPlayerHandler : MessageId.PLAYER_MP3_AUDIO_PLAYER_HANDLER,
        # Players.BuiltInAudioPlayerHandler : MessageId.PLAYER_INTERNAL
    }

    @classmethod
    def get_msg(cls, msg_id: str | int | MessageId) -> str:
        msg: str = ''
        if isinstance(msg_id, str):
            try:
                msg_id_str: str = msg_id
                new_msg_id: int = cls.msg_id_lookup[msg_id_str]
                msg: str = cls.get_msg_by_id(new_msg_id)
            except Exception as e:
                module_logger.exception('')
        elif isinstance(msg_id, int):
            try:
                msg_num: int = msg_id
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
            else:
                message_id: MessageId = msg_id
                msg_num = message_id.value
            msg = xbmcaddon.Addon().getLocalizedString(msg_num)
            # module_logger.debug(f'ADDON msg: {msg} msg_id: {msg_id}')
        except:
            module_logger.exception(f'ADDON msg: {msg} msg_id: {msg_num}')
            msg = ''
        try:
            if msg == '':
                msg = xbmc.getLocalizedString(msg_num)
                # module_logger.debug(f'msg: {msg} msg_id: {msg_id}')
        except:
            module_logger.exception(f'msg: {msg} msg_id: {msg_num}')
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
