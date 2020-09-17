# -*- coding: utf-8 -*-
'''
Created on Feb 6, 2019

@author: Frank Feuerbacher
'''

import xbmc


class Action:
    # Values came from xbmcgui

    def __init__(self):
        actionMap = {'ACTION_ANALOG_FORWARD': 113,
                     'ACTION_ANALOG_MOVE': 49,
                     'ACTION_ANALOG_MOVE_X_LEFT': 601,
                     'ACTION_ANALOG_MOVE_X_RIGHT': 602,
                     'ACTION_ANALOG_MOVE_Y_DOWN': 604,
                     'ACTION_ANALOG_MOVE_Y_UP': 603,
                     'ACTION_ANALOG_REWIND': 114,
                     'ACTION_ANALOG_SEEK_BACK': 125,
                     'ACTION_ANALOG_SEEK_FORWARD': 124,
                     'ACTION_ASPECT_RATIO': 19,
                     'ACTION_AUDIO_DELAY': 161,
                     'ACTION_AUDIO_DELAY_MIN': 54,
                     'ACTION_AUDIO_DELAY_PLUS': 55,
                     'ACTION_AUDIO_NEXT_LANGUAGE': 56,
                     'ACTION_BACKSPACE': 110,
                     'ACTION_BIG_STEP_BACK': 23,
                     'ACTION_BIG_STEP_FORWARD': 22,
                     'ACTION_BROWSE_SUBTITLE': 247,
                     'ACTION_BUILT_IN_FUNCTION': 122,
                     'ACTION_CALIBRATE_RESET': 48,
                     'ACTION_CALIBRATE_SWAP_ARROWS': 47,
                     'ACTION_CHANGE_RESOLUTION': 57,
                     'ACTION_CHANNEL_DOWN': 185,
                     'ACTION_CHANNEL_NUMBER_SEP': 192,
                     'ACTION_CHANNEL_SWITCH': 183,
                     'ACTION_CHANNEL_UP': 184,
                     'ACTION_CHAPTER_OR_BIG_STEP_BACK': 98,
                     'ACTION_CHAPTER_OR_BIG_STEP_FORWARD': 97,
                     'ACTION_CONTEXT_MEN': 117,
                     'ACTION_COPY_ITEM': 81,
                     'ACTION_CREATE_BOOKMARK': 96,
                     'ACTION_CREATE_EPISODE_BOOKMARK': 95,
                     'ACTION_CURSOR_LEFT': 120,
                     'ACTION_CURSOR_RIGHT': 121,
                     'ACTION_CYCLE_SUBTITLE': 99,
                     'ACTION_DECREASE_PAR': 220,
                     'ACTION_DECREASE_RATING': 137,
                     'ACTION_DELETE_ITEM': 80,
                     'ACTION_ENTER': 135,
                     'ACTION_ERROR': 998,
                     'ACTION_FILTER': 233,
                     'ACTION_FILTER_CLEAR': 150,
                     'ACTION_FILTER_SMS2': 151,
                     'ACTION_FILTER_SMS3': 152,
                     'ACTION_FILTER_SMS4': 153,
                     'ACTION_FILTER_SMS5': 154,
                     'ACTION_FILTER_SMS6': 155,
                     'ACTION_FILTER_SMS7': 156,
                     'ACTION_FILTER_SMS8': 157,
                     'ACTION_FILTER_SMS9': 158,
                     'ACTION_FIRST_PAGE': 159,
                     'ACTION_FORWARD': 16,
                     'ACTION_GESTURE_ABORT': 505,
                     'ACTION_GESTURE_BEGIN': 501,
                     'ACTION_GESTURE_END': 599,
                     'ACTION_GESTURE_NOTIFY': 500,
                     'ACTION_GESTURE_PAN': 504,
                     'ACTION_GESTURE_ROTATE': 503,
                     'ACTION_GESTURE_SWIPE_DOWN': 541,
                     'ACTION_GESTURE_SWIPE_DOWN_TEN': 550,
                     'ACTION_GESTURE_SWIPE_LEFT': 511,
                     'ACTION_GESTURE_SWIPE_LEFT_TEN': 520,
                     'ACTION_GESTURE_SWIPE_RIGHT': 521,
                     'ACTION_GESTURE_SWIPE_RIGHT_TEN': 530,
                     'ACTION_GESTURE_SWIPE_UP': 531,
                     'ACTION_GESTURE_SWIPE_UP_TEN': 540,
                     'ACTION_GESTURE_ZOOM': 502,
                     'ACTION_GUIPROFILE_BEGIN': 204,
                     'ACTION_HIGHLIGHT_ITEM': 8,
                     'ACTION_INCREASE_PAR': 219,
                     'ACTION_INCREASE_RATING': 136,
                     'ACTION_INPUT_TEXT': 244,
                     'ACTION_JUMP_SMS2': 142,
                     'ACTION_JUMP_SMS3': 143,
                     'ACTION_JUMP_SMS4': 144,
                     'ACTION_JUMP_SMS5': 145,
                     'ACTION_JUMP_SMS6': 146,
                     'ACTION_JUMP_SMS7': 147,
                     'ACTION_JUMP_SMS8': 148,
                     'ACTION_JUMP_SMS9': 149,
                     'ACTION_LAST_PAGE': 160,
                     'ACTION_MEN': 163,
                     'ACTION_MOUSE_DOUBLE_CLICK': 103,
                     'ACTION_MOUSE_DRAG': 106,
                     'ACTION_MOUSE_END': 109,
                     'ACTION_MOUSE_LEFT_CLICK': 100,
                     'ACTION_MOUSE_LONG_CLICK': 108,
                     'ACTION_MOUSE_MIDDLE_CLICK': 102,
                     'ACTION_MOUSE_MOVE': 107,
                     'ACTION_MOUSE_RIGHT_CLICK': 101,
                     'ACTION_MOUSE_START': 100,
                     'ACTION_MOUSE_WHEEL_DOWN': 105,
                     'ACTION_MOUSE_WHEEL_UP': 104,
                     'ACTION_MOVE_DOWN': 4,
                     'ACTION_MOVE_ITEM': 82,
                     'ACTION_MOVE_ITEM_DOWN': 116,
                     'ACTION_MOVE_ITEM_UP': 115,
                     'ACTION_MOVE_LEFT': 1,
                     'ACTION_MOVE_RIGHT': 2,
                     'ACTION_MOVE_UP': 3,
                     'ACTION_MUTE': 91,
                     'ACTION_NAV_BACK': 92,
                     'ACTION_NEXT_CHANNELGROUP': 186,
                     'ACTION_NEXT_CONTROL': 181,
                     'ACTION_NEXT_ITEM': 14,
                     'ACTION_NEXT_LETTER': 140,
                     'ACTION_NEXT_PICTURE': 28,
                     'ACTION_NEXT_SCENE': 138,
                     'ACTION_NEXT_SUBTITLE': 26,
                     'ACTION_NONE': 0,
                     'ACTION_NOOP': 999,
                     'ACTION_PAGE_DOWN': 6,
                     'ACTION_PAGE_UP': 5,
                     'ACTION_PARENT_DIR': 9,
                     'ACTION_PASTE': 180,
                     'ACTION_PAUSE': 12,
                     'ACTION_PLAYER_DEBUG': 27,
                     'ACTION_PLAYER_FORWARD': 77,
                     'ACTION_PLAYER_PLAY': 79,
                     'ACTION_PLAYER_PLAYPAUSE': 229,
                     'ACTION_PLAYER_PROCESS_INFO': 69,
                     'ACTION_PLAYER_PROGRAM_SELECT': 70,
                     'ACTION_PLAYER_RESET': 248,
                     'ACTION_PLAYER_RESOLUTION_SELECT': 71,
                     'ACTION_PLAYER_REWIND': 78,
                     'ACTION_PREVIOUS_CHANNELGROUP': 187,
                     'ACTION_PREVIOUS_MEN': 10,
                     'ACTION_PREV_CONTROL': 182,
                     'ACTION_PREV_ITEM': 15,
                     'ACTION_PREV_LETTER': 141,
                     'ACTION_PREV_PICTURE': 29,
                     'ACTION_PREV_SCENE': 139,
                     'ACTION_PVR_PLAY': 188,
                     'ACTION_PVR_PLAY_RADIO': 190,
                     'ACTION_PVR_PLAY_TV': 189,
                     'ACTION_PVR_SHOW_TIMER_RULE': 191,
                     'ACTION_QUEUE_ITEM': 34,
                     'ACTION_QUEUE_ITEM_NEXT': 251,
                     'ACTION_RECORD': 170,
                     'ACTION_RELOAD_KEYMAPS': 203,
                     'ACTION_REMOVE_ITEM': 35,
                     'ACTION_RENAME_ITEM': 87,
                     'ACTION_REWIND': 17,
                     'ACTION_ROTATE_PICTURE_CCW': 51,
                     'ACTION_ROTATE_PICTURE_CW': 50,
                     'ACTION_SCAN_ITEM': 201,
                     'ACTION_SCROLL_DOWN': 112,
                     'ACTION_SCROLL_UP': 111,
                     'ACTION_SELECT_ITEM': 7,
                     'ACTION_SETTINGS_LEVEL_CHANGE': 242,
                     'ACTION_SETTINGS_RESET': 241,
                     'ACTION_SET_RATING': 164,
                     'ACTION_SHIFT': 118,
                     'ACTION_SHOW_FULLSCREEN': 36,
                     'ACTION_SHOW_GUI': 18,
                     'ACTION_SHOW_INFO': 11,
                     'ACTION_SHOW_OSD': 24,
                     'ACTION_SHOW_OSD_TIME': 123,
                     'ACTION_SHOW_PLAYLIST': 33,
                     'ACTION_SHOW_SUBTITLES': 25,
                     'ACTION_SHOW_VIDEOMEN': 134,
                     'ACTION_SMALL_STEP_BACK': 76,
                     'ACTION_STEP_BACK': 21,
                     'ACTION_STEP_FORWARD': 20,
                     'ACTION_STEREOMODE_NEXT': 235,
                     'ACTION_STEREOMODE_PREVIOUS': 236,
                     'ACTION_STEREOMODE_SELECT': 238,
                     'ACTION_STEREOMODE_SET': 240,
                     'ACTION_STEREOMODE_TOGGLE': 237,
                     'ACTION_STEREOMODE_TOMONO': 239,
                     'ACTION_STOP': 13,
                     'ACTION_SUBTITLE_ALIGN': 232,
                     'ACTION_SUBTITLE_DELAY': 162,
                     'ACTION_SUBTITLE_DELAY_MIN': 52,
                     'ACTION_SUBTITLE_DELAY_PLUS': 53,
                     'ACTION_SUBTITLE_VSHIFT_DOWN': 231,
                     'ACTION_SUBTITLE_VSHIFT_UP': 230,
                     'ACTION_SWITCH_PLAYER': 234,
                     'ACTION_SYMBOLS': 119,
                     'ACTION_TAKE_SCREENSHOT': 85,
                     'ACTION_TELETEXT_BLUE': 218,
                     'ACTION_TELETEXT_GREEN': 216,
                     'ACTION_TELETEXT_RED': 215,
                     'ACTION_TELETEXT_YELLOW': 217,
                     'ACTION_TOGGLE_COMMSKIP': 246,
                     'ACTION_TOGGLE_DIGITAL_ANALOG': 202,
                     'ACTION_TOGGLE_FONT': 249,
                     'ACTION_TOGGLE_FULLSCREEN': 199,
                     'ACTION_TOGGLE_SOURCE_DEST': 32,
                     'ACTION_TOGGLE_WATCHED': 200,
                     'ACTION_TOUCH_LONGPRESS': 411,
                     'ACTION_TOUCH_LONGPRESS_TEN': 420,
                     'ACTION_TOUCH_TAP': 401,
                     'ACTION_TOUCH_TAP_TEN': 410,
                     'ACTION_TRIGGER_OSD': 243,
                     'ACTION_VIDEO_NEXT_STREAM': 250,
                     'ACTION_VIS_PRESET_LOCK': 130,
                     'ACTION_VIS_PRESET_NEXT': 128,
                     'ACTION_VIS_PRESET_PREV': 129,
                     'ACTION_VIS_PRESET_RANDOM': 131,
                     'ACTION_VIS_PRESET_SHOW': 126,
                     'ACTION_VIS_RATE_PRESET_MINUS': 133,
                     'ACTION_VIS_RATE_PRESET_PLUS': 132,
                     'ACTION_VOICE_RECOGNIZE': 300,
                     'ACTION_VOLAMP': 90,
                     'ACTION_VOLAMP_DOWN': 94,
                     'ACTION_VOLAMP_UP': 93,
                     'ACTION_VOLUME_DOWN': 89,
                     'ACTION_VOLUME_SET': 245,
                     'ACTION_VOLUME_UP': 88,
                     'ACTION_VSHIFT_DOWN': 228,
                     'ACTION_VSHIFT_UP': 227,
                     'ACTION_ZOOM_IN': 31,
                     'ACTION_ZOOM_LEVEL_1': 38,
                     'ACTION_ZOOM_LEVEL_2': 39,
                     'ACTION_ZOOM_LEVEL_3': 40,
                     'ACTION_ZOOM_LEVEL_4': 41,
                     'ACTION_ZOOM_LEVEL_5': 42,
                     'ACTION_ZOOM_LEVEL_6': 43,
                     'ACTION_ZOOM_LEVEL_7': 44,
                     'ACTION_ZOOM_LEVEL_8': 45,
                     'ACTION_ZOOM_LEVEL_9': 46,
                     'ACTION_ZOOM_LEVEL_NORMAL': 37,
                     'ACTION_ZOOM_OUT': 30}

        '''
            'ALPHANUM_HIDE_INPUT' : 2,
            'CONTROL_TEXT_OFFSET_X' : 10,
            'CONTROL_TEXT_OFFSET_Y' : 2,
            'HORIZONTAL' : 0,
            'ICON_OVERLAY_HD' : 6,
            'ICON_OVERLAY_LOCKED' : 3,
            'ICON_OVERLAY_NONE' : 0,
            'ICON_OVERLAY_RAR' : 1,
            'ICON_OVERLAY_UNWATCHED' : 4,
            'ICON_OVERLAY_WATCHED' : 5,
            'ICON_OVERLAY_ZIP' : 2,
            'ICON_TYPE_FILES' : 106,
            'ICON_TYPE_MUSIC' : 103,
            'ICON_TYPE_NONE' : 101,
            'ICON_TYPE_PICTURES' : 104,
            'ICON_TYPE_PROGRAMS' : 102,
            'ICON_TYPE_SETTINGS' : 109,
            'ICON_TYPE_VIDEOS' : 105,
            'ICON_TYPE_WEATHER' : 107
        '''

        '''
            'INPUT_ALPHANUM' : 0,
            'INPUT_DATE' : 2,
            'INPUT_IPADDRESS' : 4,
            'INPUT_NUMERIC' : 1,
            'INPUT_PASSWORD' : 5,
                'INPUT_TIME' : 3,
                'INPUT_TYPE_DATE' : 4,
                'INPUT_TYPE_IPADDRESS' : 5,
                'INPUT_TYPE_NUMBER' : 1,
                'INPUT_TYPE_PASSWORD' : 6,
                'INPUT_TYPE_PASSWORD_MD5' : 7,
                'INPUT_TYPE_SECONDS' : 2,
                'INPUT_TYPE_TEXT' : 0,
            'INPUT_TYPE_TIME' : 3
        '''

        '''
                'KEY_APPCOMMAND' : 53248,
                'KEY_ASCII' : 61696,
        '''

        keyButtonMap = {
            'KEY_BUTTON_A': 256,
            'KEY_BUTTON_B': 257,
            'KEY_BUTTON_BACK': 275,
            'KEY_BUTTON_BLACK': 260,
            'KEY_BUTTON_DPAD_DOWN': 271,
            'KEY_BUTTON_DPAD_LEFT': 272,
            'KEY_BUTTON_DPAD_RIGHT': 273,
            'KEY_BUTTON_DPAD_UP': 270,
            'KEY_BUTTON_LEFT_ANALOG_TRIGGER': 278,
            'KEY_BUTTON_LEFT_THUMB_BUTTON': 276,
            'KEY_BUTTON_LEFT_THUMB_STICK': 264,
            'KEY_BUTTON_LEFT_THUMB_STICK_DOWN': 281,
            'KEY_BUTTON_LEFT_THUMB_STICK_LEFT': 282,
            'KEY_BUTTON_LEFT_THUMB_STICK_RIGHT': 283,
            'KEY_BUTTON_LEFT_THUMB_STICK_UP': 280,
            'KEY_BUTTON_LEFT_TRIGGER': 262,
            'KEY_BUTTON_RIGHT_ANALOG_TRIGGER': 279,
            'KEY_BUTTON_RIGHT_THUMB_BUTTON': 277,
            'KEY_BUTTON_RIGHT_THUMB_STICK': 265,
            'KEY_BUTTON_RIGHT_THUMB_STICK_DOWN': 267,
            'KEY_BUTTON_RIGHT_THUMB_STICK_LEFT': 268,
            'KEY_BUTTON_RIGHT_THUMB_STICK_RIGHT': 269,
            'KEY_BUTTON_RIGHT_THUMB_STICK_UP': 266,
            'KEY_BUTTON_RIGHT_TRIGGER': 263,
            'KEY_BUTTON_START': 274,
            'KEY_BUTTON_WHITE': 261,
            'KEY_BUTTON_X': 258,
            'KEY_BUTTON_Y': 259,
            'KEY_INVALID': 65535,
            'KEY_MOUSE_CLICK': 57344,
            'KEY_MOUSE_DOUBLE_CLICK': 57360,
            'KEY_MOUSE_DRAG': 57604,
            'KEY_MOUSE_DRAG_END': 57606,
            'KEY_MOUSE_DRAG_START': 57605,
            'KEY_MOUSE_END': 61439,
            'KEY_MOUSE_LONG_CLICK': 57376,
            'KEY_MOUSE_MIDDLECLICK': 57346,
            'KEY_MOUSE_MOVE': 57603,
            'KEY_MOUSE_NOOP': 61439,
            'KEY_MOUSE_RDRAG': 57607,
            'KEY_MOUSE_RDRAG_END': 57609,
            'KEY_MOUSE_RDRAG_START': 57608,
            'KEY_MOUSE_RIGHTCLICK': 57345,
            'KEY_MOUSE_START': 57344,
            'KEY_MOUSE_WHEEL_DOWN': 57602,
            'KEY_MOUSE_WHEEL_UP': 57601,
            'KEY_UNICODE': 61952,
            'KEY_VKEY': 61440,
            'KEY_VMOUSE': 61439}

        '''
            'NOTIFICATION_ERROR' : ,'error'
            'NOTIFICATION_INFO' : ,'info'
            'NOTIFICATION_WARNING' : ,'warning'
            'PASSWORD_VERIFY' : 1
        '''

        remoteMap = {
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

        self.byNameMap = {'actionMap': actionMap,
                          'keyButtonMap': keyButtonMap,
                          'remoteMap': remoteMap
                          }
        self.reverseActionMap = dict()
        for key in actionMap:
            value = actionMap.get(key)
            if value in self.reverseActionMap:
                xbmc.log('duplicate value in actionMap: ' +
                         str(value), xbmc.LOGDEBUG)
            self.reverseActionMap[value] = key

        self.reverseKeyButtonMap = dict()
        for key in keyButtonMap:
            value = keyButtonMap.get(key)
            if value in self.reverseKeyButtonMap:
                xbmc.log('duplicate value in keyButtonMap: ' +
                         str(value), xbmc.LOGDEBUG)
            self.reverseKeyButtonMap[value] = key

        self.buttonNameForCode = dict()
        self.buttonNameForCode[61513] = 'key_I'

        self.reverseRemoteMap = dict()
        for key in remoteMap:
            value = remoteMap.get(key)
            if value in self.reverseRemoteMap:
                xbmc.log('duplicate value in remoteMap: ' +
                         str(value) + ' ' + self.reverseRemoteMap.get(value), xbmc.LOGDEBUG)
            self.reverseRemoteMap[value] = key

        self.reverseMapsByNameMap = {'actionMap': self.reverseActionMap,
                                     'keyButtonMap': self.reverseKeyButtonMap,
                                     'remoteMap':  self.reverseRemoteMap}
        self.mapNames = ['actionMap', 'keyButtonMap', 'remoteMap']

    _singletonInstance = None

    @staticmethod
    def get_instance():
        if Action._singletonInstance is None:
            Action._singletonInstance = Action()
        return Action._singletonInstance

    def getKeyIDInfo(self, action):
        actionId = action.getId()

        result = []
        for mapName in self.mapNames:
            reverseMap = self.reverseMapsByNameMap.get(mapName)
            keyName = reverseMap.get(actionId)
            if keyName is not None:
                result.append(str(actionId) + ' Map: ' +
                              mapName + ' : ' + keyName)

        if len(result) == 0:
            result.append('Keyname for ' + str(actionId) + ' not Found')

        return result

    def getRemoteKeyIDInfo(self, action):
        actionId = action.getId()
        return self.reverseRemoteMap.get(actionId, '')

    def getRemoteKeyButtonInfo(self, action):
        actionId = action.getId()
        return self.reverseKeyButtonMap.get(actionId, '')

    def getActionIDInfo(self, action):
        actionId = action.getId()
        return self.reverseActionMap.get(actionId, '')

    def getButtonCodeId(self, action):
        buttonCode = action.getButtonCode()
        buttonName = self.buttonNameForCode.get(
            buttonCode, 'key_' + str(buttonCode))
        return buttonName
