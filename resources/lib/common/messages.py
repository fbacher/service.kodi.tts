# -*- coding: utf-8 -*-
"""
Created on Feb 28, 2019

@author: fbacher
"""
from enum import Enum

from common.critical_settings import CriticalSettings
from common.logger import *
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Message:

    msg_index: Dict[int, 'Message'] = {}

    def __init__(self, default_msg: str, msg_id:int) -> None:
        clz = type(self)
        self.default_msg: str = default_msg
        self.msg_id: int = msg_id
        clz.msg_index[msg_id] = self

    def get_default_msg(self) -> str:
        return self.default_msg

    def get_msg_id(self) -> int:
        return self.msg_id

    @classmethod
    def get_ref_by_id(cls, msg_id: int) -> 'Message':
        if not isinstance(msg_id, int):
            return None

        return cls.msg_index.get(msg_id)


class Messages:
    """
    Provides methods, message tags and default messages for accessing translated messages.
    """
    # Msg key       Default msg, Strings.po #

    UNKNOWN = Message('Unknown', 32165)

    GENDER_MALE = Message('Male', 32212)
    GENDER_FEMALE = Message('Female', 32213)
    VIDEO_MENU = Message('video menu', 32163)
    PVR_CLIENT_SPECIFIC_SETTINGS = Message('PVR Client Specific Settings', 32164)
    GENDER_UNKNOWN = Message('Unknown', 32165)
    SUBTITLES_DIALOG = Message('Subtitles dialog', 32201)
    OK = Message('OK', 32220)
    CANCEL = Message('OK', 32221)
    DEFAULTS = Message('Defaults', 32222)
    ENGINE = Message('Engine', 32001)
    DEFAULT_TTS_ENGINE = Message('Default TTS Engine', 32002)
    SELECT_LANGUAGE = Message('Select Language', 32227)
    SELECT_VOICE = Message('Select Voice', 32308)
    SETTINGS = Message('Settings', 32219)
    OPTIONS = Message('Options', 32029)
    KEYMAP = Message('Keymap', 32030)
    ADVANCED = Message('Advanced', 32031)
    SELECT_VOICE_GENDER = Message('Select Voice Gender', 32228)
    SELECT_PITCH = Message('Select Pitch', 32229)
    SELECT_PLAYER = Message('Select Player', 32230)
    PIPE_AUDIO = Message('Pipe Audio', 32234)
    SELECT_SPEED = Message('Select Speed', 32231)
    SELECT_VOLUME_DB = Message('Select Volume (dB)', 32232)
    API_KEY = Message('API Key', 32233)
    SELECT_SPEECH_ENGINE = Message('Select Speech Engine', 32224)
    ENTER_API_KEY = Message('Enter API Key:  ', 32235)
    CACHE_SPEECH = Message('Cache Audio From Engine', 32312)
    DATABASE_SCAN_STARTED = Message('Database scan started.', 32100)
    DATABASE_SCAN_FINISHED = Message('Database scan finished.', 32101)
    SPEECH_ENGINE_FALLING_BACK_TO = Message('Notice... Speech engine falling back to {0}',
                                            32102)
    SELECT_MODULE = Message('Select Module', 32322)

    Reason = Message('Reason', 32103)
    NEW_TTS_VERSION = Message('New T T S Version', 32104)
    WINDOW = Message('Window', 32105)
    SEASON = Message('Season', 32108)
    EPISODE = Message('Episode', 32109)
    PARENT_DIRECTORY = Message('Parent Directory', 32110)
    INSTALLED = Message('Installed', 32111)
    UPDATED = Message('Updated', 32112)
    DEFAULT_KEYMAP_INSTALLED = Message('Default keymap installed successfully!', 32113)
    CUSTOM_KEYMAP_INSTALLED = Message('Custom keymap installed or updated successfully!', 32114)
    CUSTOM_KEYMAP_RESET = Message('Custom keymap reset to defaults.', 32115)
    REMOVED = Message('Removed', 32116)
    KEYMAP_REMOVED = Message('Keymap removed.', 32117)
    PRESS_KEY_TO_ASSIGN = Message('Press the key you want to assign now.', 32118)
    TIMEOUT_IN_X_SECONDS = Message('Timeout in {0} seconds', 32119)
    ITEM = Message('item', 32106)
    ITEMS = Message('items', 32107)
    PRESS_THE_KEY_TO_ASSIGN = Message('Press the key you want to assign now.', 32124)

    IMPORTING_PVR_EPG = Message('Importing P.V.R. E.P.G.', 32120)
    LOADING_PVR_EPG = Message('Loading P.V.R. E.P.G.', 32121)
    BACKGROUND_PROGRESS_STARTED = Message('Background Progress Started', 32122)
    BACKGROUND_PROGRESS_DONE = Message('Background Progress Done', 322123)
    LIVE_TV_SETTINGS = Message('Live TV Settings', 32125)
    VIRTUAL_KEYBOARD = Message('virtual keyboard', 32126)
    VOLUME_BAR = Message('volume bar', 32127)
    CONTEXT_MENU = Message('context menu', 32128)
    INFO_DIALOG = Message('info dialog', 32129)
    NUMERIC_INPUT = Message('numeric input', 32130)
    SHUTDOWN_MENU = Message('shutdown menu', 32131)
    PLAYER_CONTROLS = Message('player controls', 32132)
    SEEK_BAR = Message('seek bar', 32133)
    MUSIC_OSD = Message('music OSD', 32134)
    VISUALISATION_PRESET_LIST = Message('visualisation preset list', 32135)
    OSD_VIDEO_SETTINGS = Message('OSD video settings', 32136)
    OSD_AUDIO_SETTINGS = Message('OSD audio settings', 32137)
    VIDEO_BOOKMARKS = Message('video bookmarks', 32138)
    FILE_BROWSER = Message('file browser', 32139)
    NETWORK_SETUP = Message('network setup', 32140)
    MEDIA_SOURCE = Message('media source', 32141)
    SMART_PLAYLIST_EDITOR = Message('smart playlist editor', 32142)
    BUSY_DIALOG = Message('busy dialog', 32143)
    ADDON_SETTINGS = Message('addon settings', 32144)
    FULLSCREEN_INFO = Message('fullscreen info', 32145)
    KARAOKE_SELECTOR = Message('karaoke selector', 32146)
    KARAOKE_LARGE_SELECTOR = Message('karaoke large selector', 32147)
    SLIDER_DIALOG = Message('slider dialog', 32148)
    ADDON_INFORMATION = Message('addon information', 32149)
    TEXT_VIEWER = Message('text viewer', 32150)
    PERIPHERAL_SETTINGS = Message('peripheral settings', 32151)
    MEDIA_FILTER = Message('media filter', 32152)
    PVR = Message('pvr', 32153)
    PVR_GUIDE_INFO = Message('pvr guide info', 32154)
    PVR_RECORDING_INFO = Message('pvr recording info', 32155)
    PVR_TIMER_SETTING = Message('pvr timer setting', 32156)
    PVR_GROUP_MANAGER = Message('pvr group_manager', 32157)
    PVR_CHANNEL_MANAGER = Message('pvr channel manager', 32158)
    PVR_GUIDE_SEARCH = Message('pvr guide search', 32159)
    PVR_OSD_CHANNELS = Message('pvr OSD channels', 32160)
    PVR_OSD_GUIDE = Message('pvr OSD guide', 32161)
    ADDONS_UPDATED = Message('Addons updated', 32166)
    VERSION = Message('version', 32167)
    NOTICE = Message('Notice', 32168)
    REWIND = Message('Rewind', 32169)
    FAST_FORWARD = Message('Fast Forward', 32170)
    CHANNEL = Message('Channel', 32171)
    SUB_SETTING = Message('Sub-setting', 32172)
    YES = Message('yes', 32173)
    NO = Message('no', 32174)
    SECTION = Message('section', 32175)
    AREA = Message('area', 32176)
    SPACE = Message('space', 32177)
    NO_TEXT = Message('No text', 32178)
    DELETED = Message('deleted', 32179)
    CANNOT_ADJUST_VOLUME = Message('Cannot adjust volume', 32180)
    CHOOSE_BACKEND = Message('Choose Backend', 32181)
    NOT_AVAILABLE = Message('Not Available', 32182)
    NO_PLAYERS_TO_SELECT = Message('No players to select.', 32183)
    AUTO = Message('Auto', 32184)
    CHOOSE_PLAYER = Message('Choose Player', 32185)
    NO_OPTIONS_TO_SELECT = Message('No options to select.', 32186)
    CHOOSE_OPTION = Message('Choose Option', 32187)
    PVR_TV_CHANNELS = Message('PVR TV Channels', 32188)
    PVR_TV_RECORDINGS = Message('PVR TV Recordings', 32189)
    PVR_TV_GUIDE = Message('PVR TV Guide', 32190)
    PVR_TV_TIMERS = Message('PVR TV Timers', 32191)
    PVR_TV_SEARCH = Message('PVR TV Search', 32192)
    PVR_RADIO_CHANNELS = Message('PVR Radio Channels', 32193)
    PVR_RADIO_RECORDINGS = Message('PVR Radio Recordings', 32194)
    PVR_RADIO_GUIDE = Message('PVR Radio Guide', 32195)
    PVR_RADIO_TIMERS = Message('PVR Radio Timers', 32196)
    PVR_RADIO_SEARCH = Message('PVR Radio Search', 32197)
    WATCHED = Message('watched', 32198)
    RESUMABLE = Message('resumable', 32199)
    SELECTED = Message('selected', 32200)

    LOCALE_AF = Message('Afrikans', 32237)
    LOCALE_AF_ZA = Message('Afrikans (South Africa)', 32238)
    LOCALE_AR_SA = Message('Arabic (Saudi Arabia)', 32239)
    LOCALE_BS = Message('Bosnian', 32240)
    LOCALE_CA = Message('Catalan', 32241)
    LOCALE_CA_ES = Message('Catalan (Spain)', 32242)
    LOCALE_CS = Message('Czech', 32243)
    LOCALE_CY = Message('Welsh', 32244)
    LOCALE_DA_DK = Message('Danish (Denmark)', 32245)
    LOCALE_DE_DE = Message('German (Germany)', 32246)
    LOCALE_EL_GR = Message('Greek (Greece)', 32247)
    LOCALE_EN_AU = Message('English (Australia)', 32248)
    LOCALE_EN_GB = Message('English (United Kingdom)', 32249)
    LOCALE_EN_IE = Message('English (Ireland)', 32250)
    LOCALE_EN_IN = Message('English (India)', 32251)
    LOCALE_EN_US = Message('English (United States)', 32252)
    LOCALE_EN_ZA = Message('English (South Africa)', 32253)
    LOCALE_EO = Message('Esperanto', 32254)
    LOCALE_ES = Message('Spanish', 32255)
    LOCALE_ES_ES = Message('Spanish (Castilian, Spain)', 32256)
    LOCALE_ES_MX = Message('Spanish (Mexico)', 32257)
    LOCALE_ES_US = Message('Spanish (United States)', 32258)
    LOCALE_FI_FI = Message('Finnish (Finland)', 32259)
    LOCALE_FR = Message('French', 32260)
    LOCALE_FR_BE = Message('French (Belgium)', 32261)
    LOCALE_FR_FR = Message('French (France)', 32262)
    LOCALE_FR_CA = Message('French (Canada)', 32263)
    LOCALE_HI = Message('Hindi', 32264)
    LOCALE_HI_IN = Message('Hindi (India)', 32265)
    LOCALE_HR_HR = Message('Croatian (Croatia)', 32266)
    LOCALE_HU_HU = Message('Hungarian (Hungary)', 32267)
    LOCALE_HY_AM = Message('Armenian (Armenia)', 32268)
    LOCALE_ID_ID = Message('Indonesian (Indonesia)', 32269)
    LOCALE_IS_IS = Message('Icelandic (Iceland)', 32270)
    LOCALE_IT_IT = Message('Italian (Italy)', 32271)
    LOCALE_JA_JP = Message('Japanese (Japan)', 32272)
    LOCALE_KO_KR = Message('Korean (Korea)', 32273)
    LOCALE_LA = Message('Latin', 32274)
    LOCALE_LV_LV = Message('Latvian (Latvia)', 32275)
    #LOCALE_MK_MK = Message('FYRO Macedonian (Former Yugoslav Republic of Macedonia)')
    #LOCALE_MO = Message('Moldovan (Deprecated)')
    LOCALE_NB_NO = Message('Norwegian (Norway)', 32276)
    LOCALE_NL_BE = Message('Dutch (Belgium)', 32277)
    LOCALE_NL_NL = Message('Dutch (Netherlands)', 32278)
    LOCALE_NO_NO = Message('Norwegian (Norway)', 32279)
    LOCALE_PL_PL = Message('Polish (Poland)', 32280)
    LOCALE_PT_BR = Message('Portuguese (Brazil)', 32281)
    LOCALE_PT_PT = Message('Portuguese (Portugal)', 32282)
    LOCALE_RO_RO = Message('Romanian (Romania)', 32283)
    LOCALE_RU_RU = Message('Russian (Russia)', 32284)
    #LOCALE_SH = Message('Serbo-Croation (Deprecated)')
    LOCALE_SK_SK = Message('Slovak (Slovakia)', 32285)
    LOCALE_SQ_AL = Message('Albanian (Albania)', 32286)
    LOCAL_SR_ME = Message('Serbian (Montenegro)', 32287)
    LOCALE_SR_RS = Message('Serbian (Serbia)', 32288)
    LOCALE_SW_KE = Message('Swahili (Kenya)', 32289)
    LOCALE_TA = Message('Tamil', 32290)
    LOCALE_TH_TH = Message('Thai (Thailand)', 32291)
    LOCALE_TR_TR = Message('Turkish (Turkey)', 32292)
    LOCALE_VI_VN = Message('Vietnamese (Viet Nam)', 32293)
    LOCALE_ZH_CN = Message('Chinese (S)', 32294)
    LOCALE_ZH_HK = Message('Chinese (Hong Kong)', 32295)
    LOCALE_ZH_TW = Message('Chinese (T)', 32296)

    # Audio Players

    PLAYER_NONE = Message('No Player', 32304)
    PLAYER_SFX = Message('PlaySFX', 32297)
    PLAYER_WINDOWS = Message('Windows Internal', 32298)
    PLAYER_APLAY = Message('aplay', 32299)
    PLAYER_PAPLAY = Message('paplay', 32300)
    PLAYER_AFPLAY = Message('afplay', 32301)
    PLAYER_SOX = Message('SOX', 32302)
    PLAYER_MPLAYER = Message('Mplayer', 32303)
    PLAYER_MPG321 = Message('mpg321', 32305)
    PLAYER_MPG123 = Message('mpg123', 32306)
    PLAYER_MPG321_OE_PI = Message('mpg321 OE Pi', 32307)

    # built-in players

    PLAYER_INTERNAL = Message('internal', 32313)

    BACKEND_ESPEAK = Message('eSpeak', 32314)
    BACKEND_FESTIVAL = Message('Festival', 32315)
    BACKEND_FLITE = Message('Flite', 32316)
    BACKEND_RESPONSIVE_VOICE = Message('ResponsiveVoice', 32317)
    BACKEND_SPEECH_DISPATCHER = Message('Speech Dispatcher', 32318)
    BACKEND_EXPERIMENTAL = Message('Experimental Engine', 32323)

    # Generic VOICE Names

    VOICE_1 = Message('Voice 1', 32309)
    VOICE_2 = Message('Voice 2', 32310)
    VOICE_3 = Message('Voice 3', 32311)

    # Miscellaneous Settings

    MISC_PITCH = Message('Pitch', 32005)
    MISC_SPELLING = Message('Spelling', 32319)
    MISC_PUNCTUATION = Message('Punctuation', 32320)
    MISC_CAPITAL_RECOGNITION = Message('Capital Recognition', 32321)

    # Last Msg 32322

    _instance = None
    _debug_dump = False

    def __init__(self):
        # type: () -> None
        """

        """
        self._logger = module_logger.getChild(self.__class__.__name__)

    @staticmethod
    def get_msg(msg_ref: Message| int) -> str:
        """

        :param msg_ref:
        :return:
        """
        if Messages._instance is None:
            Messages._instance = Messages()
        if isinstance(msg_ref, int):
            msg_ref = Message.get_ref_by_id(msg_ref)

        if isinstance(msg_ref, Enum):
            msg_ref = msg_ref.name

        return Messages._instance.get_formatted_msg(msg_ref)

    @staticmethod
    def get_formatted_msg(msg_ref: Message | int, *args: Optional[List[str]]) -> str:
        """

        :param msg_ref:
        :param args
        :return:
        """
        if Messages._instance is None:
            Messages._instance = Messages()

        msg_id: int
        unformatted_msg = ''
        if isinstance(msg_ref, int):
            msg_ref = Message.get_ref_by_id(msg_ref)

        if isinstance(msg_ref, Enum):
            msg_ref = msg_ref.name

        msg_id: int = 0
        try:
            if isinstance(msg_ref, Message):
                msg_id = msg_ref.get_msg_id()
                unformatted_msg = CriticalSettings.ADDON.getLocalizedString(msg_id)
            if unformatted_msg == '':
                if msg_id != 0:
                    unformatted_msg = f'Message not defined: {str(msg_id)}'
                else:
                    unformatted_msg = f'Message not defined: {msg_ref}'
                if Messages._instance._logger.isEnabledFor(ERROR):
                    Messages._instance._logger.error(
                        f'Can not find message from strings for message id: {str(msg_id)}')
        except:
            unformatted_msg = f"Invalid msg id: {str(msg_id)}"
            module_logger.exception(unformatted_msg)

        return unformatted_msg.format(*args)
