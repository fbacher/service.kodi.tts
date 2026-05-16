# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmcgui

'''
Created on Feb 6, 2019

@author: Frank Feuerbacher
'''

import xbmc

from common import *
from common.logger import *

MY_LOGGER = BasicLogger.get_logger(__name__)


class Action:

    # Values came from xbmcgui

    action_map: dict[str, int] = {
        "ACTION_ANALOG_FORWARD"             : 113,
        "ACTION_ANALOG_MOVE"                : 49,
        "ACTION_ANALOG_MOVE_X_LEFT"         : 601,
        "ACTION_ANALOG_MOVE_X_RIGHT"        : 602,
        "ACTION_ANALOG_MOVE_Y_DOWN"         : 604,
        "ACTION_ANALOG_MOVE_Y_UP"           : 603,
        "ACTION_ANALOG_REWIND"              : 114,
        "ACTION_ANALOG_SEEK_BACK"           : 125,
        "ACTION_ANALOG_SEEK_FORWARD"        : 124,
        "ACTION_ASPECT_RATIO"               : 19,
        "ACTION_AUDIO_DELAY"                : 161,
        "ACTION_AUDIO_DELAY_MIN"            : 54,
        "ACTION_AUDIO_DELAY_PLUS"           : 55,
        "ACTION_AUDIO_NEXT_LANGUAGE"        : 56,
        "ACTION_BACKSPACE"                  : 110,
        "ACTION_BIG_STEP_BACK"              : 23,
        "ACTION_BIG_STEP_FORWARD"           : 22,
        "ACTION_BROWSE_SUBTITLE"            : 247,
        "ACTION_BUILT_IN_FUNCTION"          : 122,
        "ACTION_CALIBRATE_RESET"            : 48,
        "ACTION_CALIBRATE_SWAP_ARROWS"      : 47,
        "ACTION_CHANGE_RESOLUTION"          : 57,
        "ACTION_CHANNEL_DOWN"               : 185,
        "ACTION_CHANNEL_NUMBER_SEP"         : 192,
        "ACTION_CHANNEL_SWITCHdd"             : 183,
        "ACTION_CHANNEL_UP"                 : 184,
        "ACTION_CHAPTER_OR_BIG_STEP_BACK"   : 98,
        "ACTION_CHAPTER_OR_BIG_STEP_FORWARD": 97,
        "ACTION_CONTEXT_MENU"               : 117,
        "ACTION_COPY_ITEM"                  : 81,
        "ACTION_CREATE_BOOKMARK"            : 96,
        "ACTION_CREATE_EPISODE_BOOKMARK"    : 95,
        "ACTION_CURSOR_LEFT"                : 120,
        "ACTION_CURSOR_RIGHT"               : 121,
        "ACTION_CYCLE_SUBTITLE"             : 99,
        "ACTION_CYCLE_TONEMAP_METHOD"       : 261,
        "ACTION_DECREASE_PAR"               : 220,
        "ACTION_DECREASE_RATING"            : 137,
        "ACTION_DELETE_ITEM"                : 80,
        "ACTION_ENTER"                      : 135,
        "ACTION_ERROR"                      : 998,
        "ACTION_FILTER"                     : 233,
        "ACTION_FILTER_CLEAR"               : 150,
        "ACTION_FILTER_SMS2"                : 151,
        "ACTION_FILTER_SMS3"                : 152,
        "ACTION_FILTER_SMS4"                : 153,
        "ACTION_FILTER_SMS5"                : 154,
        "ACTION_FILTER_SMS6"                : 155,
        "ACTION_FILTER_SMS7"                : 156,
        "ACTION_FILTER_SMS8"                : 157,
        "ACTION_FILTER_SMS9"                : 158,
        "ACTION_FIRST_PAGE"                 : 159,
        "ACTION_FORWARD"                    : 16,
        "ACTION_GESTURE_ABORT"              : 505,
        "ACTION_GESTURE_BEGIN"              : 501,
        "ACTION_GESTURE_END"                : 599,
        "ACTION_GESTURE_NOTIFY"             : 500,
        "ACTION_GESTURE_PAN"                : 504,
        "ACTION_GESTURE_ROTATE"             : 503,
        "ACTION_GESTURE_SWIPE_DOWN"         : 541,
        "ACTION_GESTURE_SWIPE_DOWN_TEN"     : 550,
        "ACTION_GESTURE_SWIPE_LEFT"         : 511,
        "ACTION_GESTURE_SWIPE_LEFT_TEN"     : 520,
        "ACTION_GESTURE_SWIPE_RIGHT"        : 521,
        "ACTION_GESTURE_SWIPE_RIGHT_TEN"    : 530,
        "ACTION_GESTURE_SWIPE_UP"           : 531,
        "ACTION_GESTURE_SWIPE_UP_TEN"       : 540,
        "ACTION_GESTURE_ZOOM"               : 502,
        "ACTION_GUIPROFILE_BEGIN"           : 204,
        "ACTION_HDR_TOGGLE"                 : 260,
        "ACTION_HIGHLIGHT_ITEM"             : 8,
        "ACTION_INCREASE_PAR"               : 219,
        "ACTION_INCREASE_RATING"            : 136,
        "ACTION_INPUT_TEXT"                 : 244,
        "ACTION_JUMP_SMS2"                  : 142,
        "ACTION_JUMP_SMS3"                  : 143,
        "ACTION_JUMP_SMS4"                  : 144,
        "ACTION_JUMP_SMS5"                  : 145,
        "ACTION_JUMP_SMS6"                  : 146,
        "ACTION_JUMP_SMS7"                  : 147,
        "ACTION_JUMP_SMS8"                  : 148,
        "ACTION_JUMP_SMS9"                  : 149,
        "ACTION_LAST_PAGE"                  : 160,
        "ACTION_MENU"                       : 163,
        "ACTION_MOUSE_DOUBLE_CLICK"         : 103,
        "ACTION_MOUSE_DRAG"                 : 106,
        "ACTION_MOUSE_DRAG_END"             : 109,
        "ACTION_MOUSE_END"                  : 109,
        "ACTION_MOUSE_LEFT_CLICK"           : 100,
        "ACTION_MOUSE_LONG_CLICK"           : 108,
        "ACTION_MOUSE_MIDDLE_CLICK"         : 102,
        "ACTION_MOUSE_MOVE"                 : 107,
        "ACTION_MOUSE_RIGHT_CLICK"          : 101,
        "ACTION_MOUSE_START"                : 100,
        "ACTION_MOUSE_WHEEL_DOWN"           : 105,
        "ACTION_MOUSE_WHEEL_UP"             : 104,
        "ACTION_MOVE_DOWN"                  : 4,
        "ACTION_MOVE_ITEM"                  : 82,
        "ACTION_MOVE_ITEM_DOWN"             : 116,
        "ACTION_MOVE_ITEM_UP"               : 115,
        "ACTION_MOVE_LEFT"                  : 1,
        "ACTION_MOVE_RIGHT"                 : 2,
        "ACTION_MOVE_UP"                    : 3,
        "ACTION_MUTE"                       : 91,
        "ACTION_NAV_BACK"                   : 92,
        "ACTION_NEXT_CHANNELGROUP"          : 186,
        "ACTION_NEXT_CONTROL"               : 181,
        "ACTION_NEXT_ITEM"                  : 14,
        "ACTION_NEXT_LETTER"                : 140,
        "ACTION_NEXT_PICTURE"               : 28,
        "ACTION_NEXT_SCENE"                 : 138,
        "ACTION_NEXT_SUBTITLE"              : 26,
        "ACTION_NONE"                       : 0,
        "ACTION_NOOP"                       : 999,
        "ACTION_PAGE_DOWN"                  : 6,
        "ACTION_PAGE_UP"                    : 5,
        "ACTION_PARENT_DIR"                 : 9,
        "ACTION_PASTE"                      : 180,
        "ACTION_PAUSE"                      : 12,
        "ACTION_PLAYER_DEBUG"               : 27,
        "ACTION_PLAYER_DEBUG_VIDEO"         : 262,
        "ACTION_PLAYER_FORWARD"             : 77,
        "ACTION_PLAYER_PLAY"                : 79,
        "ACTION_PLAYER_PLAYPAUSE"           : 229,
        "ACTION_PLAYER_PROCESS_INFO"        : 69,
        "ACTION_PLAYER_PROGRAM_SELECT"      : 70,
        "ACTION_PLAYER_RESET"               : 248,
        "ACTION_PLAYER_RESOLUTION_SELECT"   : 71,
        "ACTION_PLAYER_REWIND"              : 78,
        "ACTION_PREVIOUS_CHANNELGROUP"      : 187,
        "ACTION_PREVIOUS_MENU"              : 10,
        "ACTION_PREV_CONTROL"               : 182,
        "ACTION_PREV_ITEM"                  : 15,
        "ACTION_PREV_LETTER"                : 141,
        "ACTION_PREV_PICTURE"               : 29,
        "ACTION_PREV_SCENE"                 : 139,
        "ACTION_PVR_ANNOUNCE_REMINDERS"     : 193,
        "ACTION_PVR_PLAY"                   : 188,
        "ACTION_PVR_PLAY_RADIO"             : 190,
        "ACTION_PVR_PLAY_TV"                : 189,
        "ACTION_PVR_SHOW_TIMER_RULE"        : 191,
        "ACTION_QUEUE_ITEM"                 : 34,
        "ACTION_QUEUE_ITEM_NEXT"            : 251,
        "ACTION_RECORD"                     : 170,
        "ACTION_RELOAD_KEYMAPS"             : 203,
        "ACTION_REMOVE_ITEM"                : 35,
        "ACTION_RENAME_ITEM"                : 87,
        "ACTION_REWIND"                     : 17,
        "ACTION_ROTATE_PICTURE_CCW"         : 51,
        "ACTION_ROTATE_PICTURE_CW"          : 50,
        "ACTION_SCAN_ITEM"                  : 201,
        "ACTION_SCROLL_DOWN"                : 112,
        "ACTION_SCROLL_UP"                  : 111,
        "ACTION_SELECT_ITEM"                : 7,
        "ACTION_SETTINGS_LEVEL_CHANGE"      : 242,
        "ACTION_SETTINGS_RESET"             : 241,
        "ACTION_SET_RATING"                 : 164,
        "ACTION_SHIFT"                      : 118,
        "ACTION_SHOW_FULLSCREEN"            : 36,
        "ACTION_SHOW_GUI"                   : 18,
        "ACTION_SHOW_INFO"                  : 11,
        "ACTION_SHOW_OSD"                   : 24,
        "ACTION_SHOW_OSD_TIME"              : 123,
        "ACTION_SHOW_PLAYLIST"              : 33,
        "ACTION_SHOW_SUBTITLES"             : 25,
        "ACTION_SHOW_VIDEOMENU"             : 134,
        "ACTION_SMALL_STEP_BACK"            : 76,
        "ACTION_STEP_BACK"                  : 21,
        "ACTION_STEP_FORWARD"               : 20,
        "ACTION_STEREOMODE_NEXT"            : 235,
        "ACTION_STEREOMODE_PREVIOUS"        : 236,
        "ACTION_STEREOMODE_SELECT"          : 238,
        "ACTION_STEREOMODE_SET"             : 240,
        "ACTION_STEREOMODE_TOGGLE"          : 237,
        "ACTION_STEREOMODE_TOMONO"          : 239,
        "ACTION_STOP"                       : 13,
        "ACTION_SUBTITLE_ALIGN"             : 232,
        "ACTION_SUBTITLE_DELAY"             : 162,
        "ACTION_SUBTITLE_DELAY_MIN"         : 52,
        "ACTION_SUBTITLE_DELAY_PLUS"        : 53,
        "ACTION_SUBTITLE_VSHIFT_DOWN"       : 231,
        "ACTION_SUBTITLE_VSHIFT_UP"         : 230,
        "ACTION_SWITCH_PLAYER"              : 234,
        "ACTION_SYMBOLS"                    : 119,
        "ACTION_TAKE_SCREENSHOT"            : 85,
        "ACTION_TELETEXT_BLUE"              : 218,
        "ACTION_TELETEXT_GREEN"             : 216,
        "ACTION_TELETEXT_RED"               : 215,
        "ACTION_TELETEXT_YELLOW"            : 217,
        "ACTION_TOGGLE_COMMSKIP"            : 246,
        "ACTION_TOGGLE_DIGITAL_ANALOG"      : 202,
        "ACTION_TOGGLE_FONT"                : 249,
        "ACTION_TOGGLE_FULLSCREEN"          : 199,
        "ACTION_TOGGLE_SOURCE_DEST"         : 32,
        "ACTION_TOGGLE_WATCHED"             : 200,
        "ACTION_TOUCH_LONGPRESS"            : 411,
        "ACTION_TOUCH_LONGPRESS_TEN"        : 420,
        "ACTION_TOUCH_TAP"                  : 401,
        "ACTION_TOUCH_TAP_TEN"              : 410,
        "ACTION_TRIGGER_OSD"                : 243,
        "ACTION_VIDEO_NEXT_STREAM"          : 250,
        "ACTION_VIS_PRESET_LOCK"            : 130,
        "ACTION_VIS_PRESET_NEXT"            : 128,
        "ACTION_VIS_PRESET_PREV"            : 129,
        "ACTION_VIS_PRESET_RANDOM"          : 131,
        "ACTION_VIS_PRESET_SHOW"            : 126,
        "ACTION_VIS_RATE_PRESET_MINUS"      : 133,
        "ACTION_VIS_RATE_PRESET_PLUS"       : 132,
        "ACTION_VOICE_RECOGNIZE"            : 300,
        "ACTION_VOLAMP"                     : 90,
        "ACTION_VOLAMP_DOWN"                : 94,
        "ACTION_VOLAMP_UP"                  : 93,
        "ACTION_VOLUME_DOWN"                : 89,
        "ACTION_VOLUME_SET"                 : 245,
        "ACTION_VOLUME_UP"                  : 88,
        "ACTION_VSHIFT_DOWN"                : 228,
        "ACTION_VSHIFT_UP"                  : 227,
        "ACTION_ZOOM_IN"                    : 31,
        "ACTION_ZOOM_LEVEL_1"               : 38,
        "ACTION_ZOOM_LEVEL_2"               : 39,
        "ACTION_ZOOM_LEVEL_3"               : 40,
        "ACTION_ZOOM_LEVEL_4"               : 41,
        "ACTION_ZOOM_LEVEL_5"               : 42,
        "ACTION_ZOOM_LEVEL_6"               : 43,
        "ACTION_ZOOM_LEVEL_7"               : 44,
        "ACTION_ZOOM_LEVEL_8"               : 45,
        "ACTION_ZOOM_LEVEL_9"               : 46,
        "ACTION_ZOOM_LEVEL_NORMAL"          : 37,
        "ACTION_ZOOM_OUT"                   : 30}

    '''
    ALPHANUM_HIDE_INPUT = 2
    CONTROL_TEXT_OFFSET_X = 10
    CONTROL_TEXT_OFFSET_Y = 2
    DLG_YESNO_CUSTOM_BTN = 12
    DLG_YESNO_NO_BTN = 10
    DLG_YESNO_YES_BTN = 11
    HORIZONTAL = 0
    ICON_OVERLAY_HD = 6
    ICON_OVERLAY_LOCKED = 3
    ICON_OVERLAY_NONE = 0
    ICON_OVERLAY_RAR = 1
    ICON_OVERLAY_UNWATCHED = 4
    ICON_OVERLAY_WATCHED = 5
    ICON_OVERLAY_ZIP = 2
    ICON_TYPE_FILES = 106
    ICON_TYPE_MUSIC = 103
    ICON_TYPE_NONE = 101
    ICON_TYPE_PICTURES = 104
    ICON_TYPE_PROGRAMS = 102
    ICON_TYPE_SETTINGS = 109
    ICON_TYPE_VIDEOS = 105
    ICON_TYPE_WEATHER = 107
    '''
    '''
    INPUT_ALPHANUM = 0
    INPUT_DATE = 2
    INPUT_IPADDRESS = 4
    INPUT_NUMERIC = 1
    INPUT_PASSWORD = 5
    INPUT_TIME = 3
    INPUT_TYPE_DATE = 4
    INPUT_TYPE_IPADDRESS = 5
    INPUT_TYPE_NUMBER = 1
    INPUT_TYPE_PASSWORD = 6
    INPUT_TYPE_PASSWORD_MD5 = 7
    INPUT_TYPE_PASSWORD_NUMBER_VERIFY_NEW = 10
    INPUT_TYPE_SECONDS = 2
    INPUT_TYPE_TEXT = 0
    INPUT_TYPE_TIME = 3
    '''
    '''
    KEY_APPCOMMAND = 53248
    '''
    key_button_map: dict[str, int] = {

        'KEY_BUTTON_A'                      : 256,
        'KEY_BUTTON_B'                      : 257,
        'KEY_BUTTON_BACK'                   : 275,
        'KEY_BUTTON_BLACK'                  : 260,
        'KEY_BUTTON_DPAD_DOWN'              : 271,
        'KEY_BUTTON_DPAD_LEFT'              : 272,
        'KEY_BUTTON_DPAD_RIGHT'             : 273,
        'KEY_BUTTON_DPAD_UP'                : 270,
        'KEY_BUTTON_LEFT_ANALOG_TRIGGER'    : 278,
        'KEY_BUTTON_LEFT_THUMB_BUTTON'      : 276,
        'KEY_BUTTON_LEFT_THUMB_STICK'       : 264,
        'KEY_BUTTON_LEFT_THUMB_STICK_DOWN'  : 281,
        'KEY_BUTTON_LEFT_THUMB_STICK_LEFT'  : 282,
        'KEY_BUTTON_LEFT_THUMB_STICK_RIGHT' : 283,
        'KEY_BUTTON_LEFT_THUMB_STICK_UP'    : 280,
        'KEY_BUTTON_LEFT_TRIGGER'           : 262,
        'KEY_BUTTON_RIGHT_ANALOG_TRIGGER'   : 279,
        'KEY_BUTTON_RIGHT_THUMB_BUTTON'     : 277,
        'KEY_BUTTON_RIGHT_THUMB_STICK'      : 265,
        'KEY_BUTTON_RIGHT_THUMB_STICK_DOWN' : 267,
        'KEY_BUTTON_RIGHT_THUMB_STICK_LEFT' : 268,
        'KEY_BUTTON_RIGHT_THUMB_STICK_RIGHT': 269,
        'KEY_BUTTON_RIGHT_THUMB_STICK_UP'   : 266,
        'KEY_BUTTON_RIGHT_TRIGGER'          : 263,
        'KEY_BUTTON_START'                  : 274,
        'KEY_BUTTON_WHITE'                  : 261,
        'KEY_BUTTON_X'                      : 258,
        'KEY_BUTTON_Y'                      : 259,
        'KEY_INVALID'                       : 65535,
        'KEY_MOUSE_CLICK'                   : 57344,
        'KEY_MOUSE_DOUBLE_CLICK'            : 57360,
        'KEY_MOUSE_DRAG'                    : 57604,
        'KEY_MOUSE_DRAG_END'                : 57606,
        'KEY_MOUSE_DRAG_START'              : 57605,
        'KEY_MOUSE_END'                     : 61439,
        'KEY_MOUSE_LONG_CLICK'              : 57376,
        'KEY_MOUSE_MIDDLECLICK'             : 57346,
        'KEY_MOUSE_MOVE'                    : 57603,
        'KEY_MOUSE_NOOP'                    : 61439,
        'KEY_MOUSE_RDRAG'                   : 57607,
        'KEY_MOUSE_RDRAG_END'               : 57609,
        'KEY_MOUSE_RDRAG_START'             : 57608,
        'KEY_MOUSE_RIGHTCLICK'              : 57345,
        'KEY_MOUSE_START'                   : 57344,
        'KEY_MOUSE_WHEEL_DOWN'              : 57602,
        'KEY_MOUSE_WHEEL_UP'                : 57601,
        'KEY_UNICODE'                       : 61952,
        'KEY_VKEY'                          : 61440,
        'KEY_VMOUSE'                        : 61439}

    '''
    NOTIFICATION_ERROR = 'error'
    NOTIFICATION_INFO = 'info'
    NOTIFICATION_WARNING = 'warning'
    PASSWORD_VERIFY = 1
    '''

    remote_map: dict[str, int] = {
        'REMOTE_0': 58,
        'REMOTE_1': 59,
        'REMOTE_2': 60,
        'REMOTE_3': 61,
        'REMOTE_4': 62,
        'REMOTE_5': 63,
        'REMOTE_6': 64,
        'REMOTE_7': 65,
        'REMOTE_8': 66,
        'REMOTE_9': 67,
        'VERTICAL': 1}

    by_name_map: dict[str, dict[str, int]] = {
        'actionMap'   : action_map,
        'keyButtonMap': key_button_map,
        'remoteMap'   : remote_map
    }
    reverse_action_map: dict[int, str] = dict()
    for key in action_map:
        key: str
        value: int = action_map.get(key)
        if value in reverse_action_map:
            xbmc.log(f'duplicate value in actionMap: {value}', xbmc.LOGDEBUG)
        reverse_action_map[value] = key

    reverse_key_button_map: dict[int, str] = dict()
    for key in key_button_map:
        value = key_button_map.get(key)
        if value in reverse_key_button_map:
            xbmc.log(f'duplicate value in keyButtonMap: {value}', xbmc.LOGDEBUG)
        reverse_key_button_map[value] = key

    button_name_for_code: dict[int, str] = dict()
    button_name_for_code[61513] = 'key_I'

    reverse_remote_map: dict[int, str] = dict()
    for key in remote_map:
        value = remote_map.get(key)
        value: int
        if value in reverse_remote_map:
            xbmc.log(f'duplicate value in reverseRemoteMap: {value} '
                     f'{reverse_remote_map.get(value)}',
                     xbmc.LOGDEBUG)
        reverse_remote_map[value] = key

    reverse_maps_by_name_map: dict[str, dict[str, Any]]
    reverse_maps_by_name_map = {'actionMap'    : reverse_action_map,
                                 'keyButtonMap': reverse_key_button_map,
                                 'remoteMap'   : reverse_remote_map}
    mapNames = ['actionMap', 'keyButtonMap', 'remoteMap']

    @staticmethod
    def get_key_id_info(action: xbmcgui.Action):
        action_id: int = action.getId()

        result: list[str] = []
        for mapName in Action.mapNames:
            reverse_map = Action.reverse_maps_by_name_map.get(mapName)
            key_name: str = reverse_map.get(action_id)
            if key_name is not None:
                result.append(f'{action_id} Map: {mapName}: {key_name}')

        if len(result) == 0:
            result.append(f'Keyname for {action_id} not Found')

        return result

    @staticmethod
    def getRemoteKeyIDInfo(action: xbmcgui.Action):
        action_id = action.getId()
        return Action.reverse_remote_map.get(action_id, '')

    @staticmethod
    def getRemoteKeyButtonInfo(action: xbmcgui.Action):
        action_id = action.getId()
        return Action.reverse_key_button_map.get(action_id, '')


    @staticmethod
    def getActionIDInfo(action: xbmcgui.Action):
        action_id = action.getId()
        return Action.reverse_action_map.get(action_id, '')

    @staticmethod
    def getButtonCodeId(action: xbmcgui.Action):
        button_code = action.getButtonCode()
        button_name = Action.button_name_for_code.get(
                button_code, f'key_{button_code}')
        return button_name

    @staticmethod
    def dump_action(action: xbmcgui.Action, log_all: bool = False) -> str:
        # Don't log some mouse event noise
        if (log_all or
            (action.getId() not in (xbmcgui.ACTION_MOUSE_LEFT_CLICK,  # AKA MOUSE_START
                                    xbmcgui.ACTION_MOUSE_MOVE))):
            matches: List[str] = Action.get_key_id_info(action)
            for line in matches:
                MY_LOGGER.debug(line)

        # These return empty string if not found
        action_key: str = Action.getActionIDInfo(action)
        remote_button: str = Action.getRemoteKeyButtonInfo(action)
        remote_key_id: str = Action.getRemoteKeyIDInfo(action)
        # Returns found button_code, or 'key_' +  action_button
        action_button = Action.getButtonCodeId(action)
        MY_LOGGER.debug(f'action_key: {action_key} remote_button: {remote_button}'
                        f' remote_key_id: {remote_key_id}')
        key_parts: list[str] = []
        if action_key != '':
            key_parts.append(action_key)
        if remote_button != '':
            key_parts.append(remote_button)
        if remote_key_id != '':
            key_parts.append(remote_key_id)
        key: str = ''.join(key_parts)
        if key == '':
            key = action_button
        MY_LOGGER.debug(f'Key found: {key}')
        # xbmc.log(f'Debug enabled: {MY_LOGGER.isEnabledFor(DEBUG)}', xbmc.LOGDEBUG)
        # MY_LOGGER.info("info")
        return key
