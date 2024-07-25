# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from collections import namedtuple

import xbmc

from common import *
from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList

module_logger = BasicLogger.get_module_logger(module_path=__file__)

'''
Table data format:
integer: XBMC localized string ID
string integer: controll ID
$INFO[<infolabel>]: infolabel
string: normal string
'''
'''
Accurate as of Kodi v20
/*
 *  Copyright (C) 2005-2018 Team Kodi
 *  This file is part of Kodi - https://kodi.tv
 *
 *  SPDX-License-Identifier: GPL-2.0-or-later
 *  See LICENSES/README.md for more information.
 */
'''


"""
Derived from #defines in Kodi source WindowIDs.h

Removed IDs:
    programssettings - Removed in ?
    scripts - Removed in v10 Dharma
    networksettings - Removed in v12 Frodo
    musicscan - Removed in v12 Frodo
    videoscan - Removed in v12 Frodo
    videofiles - Removed in v13 Gotham
    pvr - Replaced in v14 Helix with more specific PVR windows
    karaoke - Removed in v16 Jarvis
    musicoverlay - Removed in v16 Jarvis
    videooverlay - Removed in v16 Jarvis
    musicfiles - Removed in v16 Jarvis
    infodialog - Removed in v17 Jarvis
    video - Removed in v17 Krypton
    videolibrary - Removed in v17 Krypton
    musiclibrary - Removed in v17 Krypton
    mutebug - Removed in v17 Krypton
    videossettings - Removed in v17 Krypton
    musicsettings - Removed in v17 Krypton
    appearancesettings - Removed in v17 Krypton
    picturessettings - Removed in v17 Krypton
    weathersettings - Removed in v17 Krypton
    osdaudiodspsettings - Removed in v18 Leia
    testpattern - Removed in v18 Leia [7]
    accesspoints - Removed in v19 Matrix [8]
"""

# Window ID defines to make the code a bit more readable

WINDOW_INVALID: Final[
    int] = 9999  # do not change. value is used to avoid include in headers.
WINDOW_HOME: Final[int] = 10000
WINDOW_PROGRAMS: Final[int] = 10001
WINDOW_PICTURES: Final[int] = 10002
WINDOW_FILES: Final[int] = 10003
WINDOW_SETTINGS_MENU: Final[int] = 10004
WINDOW_SYSTEM_INFORMATION: Final[int] = 10007
WINDOW_SCREEN_CALIBRATION: Final[int] = 10011

WINDOW_SETTINGS_START: Final[int] = 10016
WINDOW_SETTINGS_SYSTEM: Final[int] = 10016
WINDOW_SETTINGS_SERVICE: Final[int] = 10018

WINDOW_SETTINGS_MYPVR: Final[int] = 10021
WINDOW_SETTINGS_MYGAMES: Final[int] = 10022

WINDOW_VIDEO_NAV: Final[int] = 10025
WINDOW_VIDEO_PLAYLIST: Final[int] = 10028

WINDOW_LOGIN_SCREEN: Final[int] = 10029

WINDOW_SETTINGS_PLAYER: Final[int] = 10030
WINDOW_SETTINGS_MEDIA: Final[int] = 10031
WINDOW_SETTINGS_INTERFACE: Final[int] = 10032

WINDOW_SETTINGS_PROFILES: Final[int] = 10034
WINDOW_SKIN_SETTINGS: Final[int] = 10035

WINDOW_ADDON_BROWSER: Final[int] = 10040

WINDOW_EVENT_LOG: Final[int] = 10050

WINDOW_FAVOURITES: Final[int] = 10060

WINDOW_SCREENSAVER_DIM: Final[int] = 97
WINDOW_DEBUG_INFO: Final[int] = 98
WINDOW_DIALOG_POINTER: Final[int] = 10099
WINDOW_DIALOG_YES_NO: Final[int] = 10100
WINDOW_DIALOG_PROGRESS: Final[int] = 10101
WINDOW_DIALOG_KEYBOARD: Final[int] = 10103
WINDOW_DIALOG_VOLUME_BAR: Final[int] = 10104
WINDOW_DIALOG_SUB_MENU: Final[int] = 10105
WINDOW_DIALOG_CONTEXT_MENU: Final[int] = 10106
WINDOW_DIALOG_KAI_TOAST: Final[int] = 10107
WINDOW_DIALOG_NUMERIC: Final[int] = 10109
WINDOW_DIALOG_GAMEPAD: Final[int] = 10110
WINDOW_DIALOG_BUTTON_MENU: Final[int] = 10111
WINDOW_DIALOG_PLAYER_CONTROLS: Final[int] = 10114
WINDOW_DIALOG_SEEK_BAR: Final[int] = 10115
WINDOW_DIALOG_PLAYER_PROCESS_INFO: Final[int] = 10116
WINDOW_DIALOG_MUSIC_OSD: Final[int] = 10120
WINDOW_DIALOG_VIS_SETTINGS: Final[int] = 10121
WINDOW_DIALOG_VIS_PRESET_LIST: Final[int] = 10122
WINDOW_DIALOG_VIDEO_OSD_SETTINGS: Final[int] = 10123
WINDOW_DIALOG_AUDIO_OSD_SETTINGS: Final[int] = 10124
WINDOW_DIALOG_VIDEO_BOOKMARKS: Final[int] = 10125
WINDOW_DIALOG_FILE_BROWSER: Final[int] = 10126
WINDOW_DIALOG_NETWORK_SETUP: Final[int] = 10128
WINDOW_DIALOG_MEDIA_SOURCE: Final[int] = 10129
WINDOW_DIALOG_PROFILE_SETTINGS: Final[int] = 10130
WINDOW_DIALOG_LOCK_SETTINGS: Final[int] = 10131
WINDOW_DIALOG_CONTENT_SETTINGS: Final[int] = 10132
WINDOW_DIALOG_LIBEXPORT_SETTINGS: Final[int] = 10133
WINDOW_DIALOG_FAVOURITES: Final[int] = 10134  # Deleted in V21
WINDOW_DIALOG_SONG_INFO: Final[int] = 10135
WINDOW_DIALOG_SMART_PLAYLIST_EDITOR: Final[int] = 10136
WINDOW_DIALOG_SMART_PLAYLIST_RULE: Final[int] = 10137
WINDOW_DIALOG_BUSY: Final[int] = 10138
WINDOW_DIALOG_PICTURE_INFO: Final[int] = 10139
WINDOW_DIALOG_ADDON_SETTINGS: Final[int] = 10140
WINDOW_DIALOG_FULLSCREEN_INFO: Final[int] = 10142
WINDOW_DIALOG_SLIDER: Final[int] = 10145
WINDOW_DIALOG_ADDON_INFO: Final[int] = 10146
WINDOW_DIALOG_TEXT_VIEWER: Final[int] = 10147
WINDOW_DIALOG_PLAY_EJECT: Final[int] = 10148
WINDOW_DIALOG_PERIPHERALS: Final[int] = 10149
WINDOW_DIALOG_PERIPHERAL_SETTINGS: Final[int] = 10150
WINDOW_DIALOG_EXT_PROGRESS: Final[int] = 10151
WINDOW_DIALOG_MEDIA_FILTER: Final[int] = 10152
WINDOW_DIALOG_SUBTITLES: Final[int] = 10153
WINDOW_DIALOG_KEYBOARD_TOUCH: Final[int] = 10156
WINDOW_DIALOG_CMS_OSD_SETTINGS: Final[int] = 10157
WINDOW_DIALOG_INFOPROVIDER_SETTINGS: Final[int] = 10158
WINDOW_DIALOG_SUBTITLE_OSD_SETTINGS: Final[int] = 10159
WINDOW_DIALOG_BUSY_NOCANCEL: Final[int] = 10160

WINDOW_MUSIC_PLAYLIST: Final[int] = 10500
WINDOW_MUSIC_NAV: Final[int] = 10502
WINDOW_MUSIC_PLAYLIST_EDITOR: Final[int] = 10503

WINDOW_DIALOG_OSD_TELETEXT: Final[int] = 10550

# PVR related Window and Dialog ID's

WINDOW_DIALOG_PVR_ID_START: Final[int] = 10600
WINDOW_DIALOG_PVR_GUIDE_INFO: Final[int] = WINDOW_DIALOG_PVR_ID_START
WINDOW_DIALOG_PVR_RECORDING_INFO: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 1)
WINDOW_DIALOG_PVR_TIMER_SETTING: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 2)
WINDOW_DIALOG_PVR_GROUP_MANAGER: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 3)
WINDOW_DIALOG_PVR_CHANNEL_MANAGER: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 4)
WINDOW_DIALOG_PVR_GUIDE_SEARCH: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 5)
WINDOW_DIALOG_PVR_CHANNEL_SCAN: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 6)
WINDOW_DIALOG_PVR_UPDATE_PROGRESS: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 7)
WINDOW_DIALOG_PVR_OSD_CHANNELS: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 8)
WINDOW_DIALOG_PVR_CHANNEL_GUIDE: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 9)
WINDOW_DIALOG_PVR_RADIO_RDS_INFO: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 10)
WINDOW_DIALOG_PVR_RECORDING_SETTING: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 11)
WINDOW_DIALOG_PVR_CLIENT_PRIORITIES: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 12)
WINDOW_DIALOG_PVR_GUIDE_CONTROLS: Final[int] = (WINDOW_DIALOG_PVR_ID_START + 13)
WINDOW_DIALOG_PVR_ID_END: Final[int] = WINDOW_DIALOG_PVR_GUIDE_CONTROLS

WINDOW_PVR_ID_START: Final[int] = 10700
WINDOW_TV_CHANNELS: Final[int] = WINDOW_PVR_ID_START
WINDOW_TV_RECORDINGS: Final[int] = (WINDOW_PVR_ID_START + 1)
WINDOW_TV_GUIDE: Final[int] = (WINDOW_PVR_ID_START + 2)
WINDOW_TV_TIMERS: Final[int] = (WINDOW_PVR_ID_START + 3)
WINDOW_TV_SEARCH: Final[int] = (WINDOW_PVR_ID_START + 4)
WINDOW_RADIO_CHANNELS: Final[int] = (WINDOW_PVR_ID_START + 5)
WINDOW_RADIO_RECORDINGS: Final[int] = (WINDOW_PVR_ID_START + 6)
WINDOW_RADIO_GUIDE: Final[int] = (WINDOW_PVR_ID_START + 7)
WINDOW_RADIO_TIMERS: Final[int] = (WINDOW_PVR_ID_START + 8)
WINDOW_RADIO_SEARCH: Final[int] = (WINDOW_PVR_ID_START + 9)
WINDOW_TV_TIMER_RULES: Final[int] = (WINDOW_PVR_ID_START + 10)
WINDOW_RADIO_TIMER_RULES: Final[int] = (WINDOW_PVR_ID_START + 11)
WINDOW_PVR_ID_END: Final[int] = WINDOW_RADIO_TIMER_RULES

#  virtual windows for PVR specific keymap bindings in fullscreen playback
WINDOW_FULLSCREEN_LIVETV: Final[int] = 10800
WINDOW_FULLSCREEN_RADIO: Final[int] = 10801
WINDOW_FULLSCREEN_LIVETV_PREVIEW: Final[int] = 10802
WINDOW_FULLSCREEN_RADIO_PREVIEW: Final[int] = 10803
WINDOW_FULLSCREEN_LIVETV_INPUT: Final[int] = 10804
WINDOW_FULLSCREEN_RADIO_INPUT: Final[int] = 10805

WINDOW_DIALOG_GAME_CONTROLLERS: Final[int] = 10820
WINDOW_GAMES: Final[int] = 10821
WINDOW_DIALOG_GAME_OSD: Final[int] = 10822
WINDOW_DIALOG_GAME_VIDEO_FILTER: Final[int] = 10823
WINDOW_DIALOG_GAME_STRETCH_MODE: Final[int] = 10824
WINDOW_DIALOG_GAME_VOLUME: Final[int] = 10825
WINDOW_DIALOG_GAME_ADVANCED_SETTINGS: Final[int] = 10826
WINDOW_DIALOG_GAME_VIDEO_ROTATION: Final[int] = 10827
WINDOW_DIALOG_GAME_PORTS: Final[int] = 10828
WINDOW_DIALOG_IN_GAME_SAVES: Final[int] = 10829
WINDOW_DIALOG_GAME_SAVES: Final[int] = 10830
WINDOW_DIALOG_GAME_AGENTS: Final[int] = 10831

# WINDOW_VIRTUAL_KEYBOARD: Final[int]=           11000
# WINDOW_ID: Final[int]='s from 11100 to 11199 reserved for Skins

WINDOW_DIALOG_SELECT: Final[int] = 12000
WINDOW_DIALOG_MUSIC_INFO: Final[int] = 12001
WINDOW_DIALOG_OK: Final[int] = 12002
WINDOW_DIALOG_VIDEO_INFO: Final[int] = 12003
WINDOW_DIALOG_MANAGE_VIDEO_VERSIONS: Final[int] = 12004
WINDOW_FULLSCREEN_VIDEO: Final[int] = 12005
WINDOW_VISUALISATION: Final[int] = 12006
WINDOW_SLIDESHOW: Final[int] = 12007
WINDOW_DIALOG_COLOR_PICKER: Final[int] = 12008

#  @todo Numbers given here must match the ids given in strings.po for a translatable
#   string for
#  the window. 12009 to 12014 are already taken for something else in strings.po (
#  accidentally).
#  So, do not define windows with ids 12009 to 12014, unless strings.po got fixed.

WINDOW_DIALOG_SELECT_VIDEO_VERSION: Final[int] = 12015
WINDOW_DIALOG_SELECT_VIDEO_EXTRA: Final[int] = 12016
WINDOW_DIALOG_MANAGE_VIDEO_EXTRAS: Final[int] = 12017

WINDOW_WEATHER: Final[int] = 12600
WINDOW_SCREENSAVER: Final[int] = 12900
WINDOW_DIALOG_VIDEO_OSD: Final[int] = 12901

WINDOW_VIDEO_MENU: Final[int] = 12902
WINDOW_VIDEO_TIME_SEEK: Final[int] = 12905  # virtual window for time seeking during
# fullscreen video

WINDOW_FULLSCREEN_GAME: Final[int] = 12906

WINDOW_SPLASH: Final[int] = 12997  # splash window
WINDOW_START: Final[int] = 12998  # first window to load
WINDOW_STARTUP_ANIM: Final[int] = 12999  # for startup animations

#  WINDOW_ID: Final[int]='s from 13000 to 13099 reserved for Python

WINDOW_PYTHON_START: Final[int] = 13000
WINDOW_PYTHON_END: Final[int] = 13099

#  WINDOW_ID: Final[int]='s from 14000 to 14099 reserved for Addons

WINDOW_ADDON_START: Final[int] = 14000
WINDOW_ADDON_END: Final[int] = 14099

# window_map uses the window-ID as the key. Each Tuple entry contains:
# (message_id # almost always the same as window-id
#  window name,
#  Definition (constant with value of window-ID
#  xml source file defining the window
#
# keymap.xml uses the Window name.
# Kodi's C++ code uses the Window definitions and Window ID's.
# ActivateWindow() should use the Window name.
# sounds.xml should use the window name
WinField = namedtuple('WinField', ['msg_id', 'window_name', 'definition',
                      'source'])
window_map: Dict[int, WinField] = {
    10000: WinField(10000, 'home', 0, 'Home.xml'),
    10001: WinField(10001, 'programs', 'WINDOW_PROGRAMS', 'MyPrograms.xml'),
    10002: WinField(10002, 'pictures', 'WINDOW_PICTURES', 'MyPics.xml'),
    10003: WinField(10003, 'filemanager', 'WINDOW_FILES', 'FileManager.xml'),
    10004: WinField(10004, 'settings', 'WINDOW_SETTINGS_MENU', 'Settings.xml'),
    10007: WinField(10007, 'systeminfo', 'WINDOW_SYSTEM_INFORMATION',
                    'SettingsSystemInfo.xml'),
    10011: WinField(10011, 'screencalibration', 'WINDOW_SCREEN_CALIBRATION',
                    'SettingsScreenCalibration.xml'),
    10016: WinField(10016, 'systemsettings', 'WINDOW_SETTINGS_SYSTEM',
                    'SettingsCategory.xml'),
    10018: WinField(10018, 'servicesettings', 'WINDOW_SETTINGS_SERVICE',
                    'SettingsCategory.xml'),
    10021: WinField(10021, 'pvrsettings', 'WINDOW_SETTINGS_MYPVR',
                    'SettingsCategory.xml'),
    10022: WinField(10022, 'gamesettings', 'WINDOW_SETTINGS_MYGAMES',
                    'SettingsCategory.xml'),
    10025: WinField(10025, 'videos', 'WINDOW_VIDEO_NAV', 'MyVideoNav.xml'),
    10028: WinField(10028, 'videoplaylist', 'WINDOW_VIDEO_PLAYLIST', 'MyPlaylist.xml'),
    10029: WinField(10029, 'loginscreen', 'WINDOW_LOGIN_SCREEN', 'LoginScreen.xml'),
    10030: WinField(10030, 'playersettings', 'WINDOW_SETTINGS_PLAYER',
                    'SettingsCategory.xml'),
    10031: WinField(10031, 'mediasettings', 'WINDOW_SETTINGS_MEDIA',
                    'SettingsCategory.xml'),
    10032: WinField(10032, 'interfacesettings', 'WINDOW_SETTINGS_INTERFACE',
                    'SettingsCategory.xml'),
    10034: WinField(10034, 'profiles', 'WINDOW_SETTINGS_PROFILES', 'SettingsProfile.xml'),
    10035: WinField(10035, 'skinsettings', 'WINDOW_SKIN_SETTINGS', 'SkinSettings.xml'),
    10040: WinField(10040, 'addonbrowser', 'WINDOW_ADDON_BROWSER', 'AddonBrowser.xml'),
    10050: WinField(10050, 'eventlog', 'WINDOW_EVENT_LOG', 'EventLog.xml'),
    10060: WinField(10060, 'favouritesbrowser', 'WINDOW_FAVOURITES', 'MyFavourites.xml'),
    # Added in Kodi v20 Nexus
    10099: WinField(10099, 'pointer', 'WINDOW_DIALOG_POINTER', 'Pointer.xml'),
    10100: WinField(10100, 'yesnodialog', 'WINDOW_DIALOG_YES_NO', 'DialogConfirm.xml'),
    10101: WinField(10101, 'progressdialog', 'WINDOW_DIALOG_PROGRESS',
                    'DialogConfirm.xml'),
    10103: WinField(10103, 'virtualkeyboard', 'WINDOW_DIALOG_KEYBOARD',
                    'DialogKeyboard.xml'),
    10104: WinField(10104, 'volumebar', 'WINDOW_DIALOG_VOLUME_BAR',
                    'DialogVolumeBar.xml'),
    10105: WinField(10105, 'submenu', 'WINDOW_DIALOG_SUB_MENU', 'DialogSubMenu.xml'),
    10106: WinField(10106, 'contextmenu', 'WINDOW_DIALOG_CONTEXT_MENU',
                    'DialogContextMenu.xml'),
    10107: WinField(10107, 'notification', 'WINDOW_DIALOG_KAI_TOAST',
                    'DialogNotification.xml'),
    10109: WinField(10109, 'numericinput', 'WINDOW_DIALOG_NUMERIC', 'DialogNumeric.xml'),
    10110: WinField(10110, 'gamepadinput', 'WINDOW_DIALOG_GAMEPAD', 'DialogSelect.xml'),
    10111: WinField(10111, 'shutdownmenu', 'WINDOW_DIALOG_BUTTON_MENU',
                    'DialogButtonMenu.xml'),
    10114: WinField(10114, 'playercontrols', 'WINDOW_DIALOG_PLAYER_CONTROLS',
                    'PlayerControls.xml'),
    10115: WinField(10115, 'seekbar', 'WINDOW_DIALOG_SEEK_BAR', 'DialogSeekBar.xml'),
    10116: WinField(10116, 'playerprocessinfo', 'WINDOW_DIALOG_PLAYER_PROCESS_INFO',
                    'DialogPlayerProcessInfo.xml'),
    10120: WinField(10120, 'musicosd', 'WINDOW_DIALOG_MUSIC_OSD', 'MusicOSD.xml'),
    10121: WinField(10121, 'visualisationpresetlist', 'WINDOW_DIALOG_VIS_SETTINGS',
                    None),
    10122: WinField(10122, 'visualisationpresetlist', 'WINDOW_DIALOG_VIS_PRESET_LIST',
                    'DialogSelect.xml'),
    10123: WinField(10123, 'osdvideosettings', 'WINDOW_DIALOG_VIDEO_OSD_SETTINGS',
                    'DialogSettings.xml'),
    10124: WinField(10124, 'osdaudiosettings', 'WINDOW_DIALOG_AUDIO_OSD_SETTINGS',
                    'DialogSettings.xml'),
    10125: WinField(10125, 'videobookmarks', 'WINDOW_DIALOG_VIDEO_BOOKMARKS',
                    'VideoOSDBookmarks.xml'),
    10126: WinField(10126, 'filebrowser', 'WINDOW_DIALOG_FILE_BROWSER',
                    'FileBrowser.xml'),
    10128: WinField(10128, 'networksetup', 'WINDOW_DIALOG_NETWORK_SETUP',
                    'DialogSettings.xml'),
    10129: WinField(10129, 'mediasource', 'WINDOW_DIALOG_MEDIA_SOURCE',
                    'DialogMediaSource.xml'),
    10130: WinField(10130, 'profilesettings', 'WINDOW_DIALOG_PROFILE_SETTINGS',
                    'DialogSettings.xml'),
    10131: WinField(10131, 'locksettings', 'WINDOW_DIALOG_LOCK_SETTINGS',
                    'DialogSettings.xml'),
    10132: WinField(10132, 'contentsettings', 'WINDOW_DIALOG_CONTENT_SETTINGS',
                    'DialogSettings.xml'),
    10133: WinField(10133, 'libexportsettings', 'WINDOW_DIALOG_LIBEXPORT_SETTINGS',
                    'DialogSettings.xml'),
    10134: WinField(10134, 'favourites', 'WINDOW_DIALOG_FAVOURITES',
                    'DialogFavourites.xml'),
    # 10134 Deprecated. Will be removed in V21
    10135: WinField(10135, 'songinformation', 'WINDOW_DIALOG_SONG_INFO',
                    'DialogMusicInfo.xml'),
    10136: WinField(10136, 'smartplaylisteditor', 'WINDOW_DIALOG_SMART_PLAYLIST_EDITOR',
                    'SmartPlaylistEditor.xml'),
    10137: WinField(10137, 'smartplaylistrule', 'WINDOW_DIALOG_SMART_PLAYLIST_RULE',
                    'SmartPlaylistRule.xml'),
    10138: WinField(10138, 'busydialog', 'WINDOW_DIALOG_BUSY', 'DialogBusy.xml'),
    10139: WinField(10139, 'pictureinfo', 'WINDOW_DIALOG_PICTURE_INFO',
                    'DialogPictureInfo.xml'),
    10140: WinField(10140, 'addonsettings', 'WINDOW_DIALOG_ADDON_SETTINGS',
                    'DialogAddonSettings.xml'),
    10142: WinField(10142, 'fullscreeninfo', 'WINDOW_DIALOG_FULLSCREEN_INFO',
                    'DialogFullScreenInfo.xml'),
    10145: WinField(10145, 'sliderdialog', 'WINDOW_DIALOG_SLIDER', 'DialogSlider.xml'),
    10146: WinField(10146, 'addoninformation', 'WINDOW_DIALOG_ADDON_INFO',
                    'DialogAddonInfo.xml'),
    10147: WinField(10147, 'textviewer', 'WINDOW_DIALOG_TEXT_VIEWER',
                    'DialogTextViewer.xml'),
    10148: WinField(10148, '', 'WINDOW_DIALOG_PLAY_EJECT', 'DialogConfirm.xml'),
    10149: WinField(10149, '', 'WINDOW_DIALOG_PERIPHERALS', 'DialogSelect.xml'),
    10150: WinField(10150, 'peripheralsettings', 'WINDOW_DIALOG_PERIPHERAL_SETTINGS',
                    'DialogSettings.xml'),
    10151: WinField(10151, 'extendedprogressdialog', 'WINDOW_DIALOG_EXT_PROGRESS',
                    'DialogExtendedProgressBar.xml'),
    10152: WinField(10152, 'mediafilter', 'WINDOW_DIALOG_MEDIA_FILTER',
                    'DialogSettings.xml'),
    10153: WinField(10153, 'subtitlesearch', 'WINDOW_DIALOG_SUBTITLES',
                    'DialogSubtitles.xml'),
    10156: WinField(10156, '', 'WINDOW_DIALOG_KEYBOARD_TOUCH', None),
    10157: WinField(10157, 'osdcmssettings', 'WINDOW_DIALOG_CMS_OSD_SETTINGS',
                    'DialogSettings.xml'),
    10158: WinField(10158, 'infoprovidersettings', 'WINDOW_DIALOG_INFOPROVIDER_SETTINGS',
                    'DialogSettings.xml'),
    10159: WinField(10159, 'osdsubtitlesettings', 'WINDOW_DIALOG_SUBTITLE_OSD_SETTINGS',
                    'DialogSettings.xml'),
    10160: WinField(10160, 'busydialognocancel', 'WINDOW_DIALOG_BUSY_NOCANCEL',
                    'DialogBusy.xml'),
    10500: WinField(10500, 'musicplaylist', 'WINDOW_MUSIC_PLAYLIST', 'MyPlaylist.xml'),
    10502: WinField(10502, 'music', 'WINDOW_MUSIC_NAV', 'MyMusicNav.xml'),
    10503: WinField(10503, 'musicplaylisteditor', 'WINDOW_MUSIC_PLAYLIST_EDITOR',
                    'MyMusicPlaylistEditor.xml'),
    10550: WinField(10550, 'teletext', 'WINDOW_DIALOG_OSD_TELETEXT', None),
    10600: WinField(10600, 'pvrguideinfo', 'WINDOW_DIALOG_PVR_GUIDE_INFO',
                    'DialogPVRInfo.xml'),
    10601: WinField(10601, 'pvrrecordinginfo', 'WINDOW_DIALOG_PVR_RECORDING_INFO',
                    'DialogPVRInfo.xml'),
    10602: WinField(10602, 'pvrtimersetting', 'WINDOW_DIALOG_PVR_TIMER_SETTING',
                    'DialogSettings.xml'),
    10603: WinField(10603, 'pvrgroupmanager', 'WINDOW_DIALOG_PVR_GROUP_MANAGER',
                    'DialogPVRGroupManager.xml'),
    10604: WinField(10604, 'pvrchannelmanager', 'WINDOW_DIALOG_PVR_CHANNEL_MANAGER',
                    'DialogPVRChannelManager.xml'),
    10605: WinField(10605, 'pvrguidesearch', 'WINDOW_DIALOG_PVR_GUIDE_SEARCH',
                    'DialogPVRGuideSearch.xml'),
    10606: WinField(10606, 'pvrchannelscan', 'WINDOW_DIALOG_PVR_CHANNEL_SCAN', None),
    #  10606 unused,
    10607: WinField(10607, 'pvrupdateprogress', 'WINDOW_DIALOG_PVR_UPDATE_PROGRESS',
                    None),
    # 10607 unused,
    10608: WinField(10608, 'pvrosdchannels', 'WINDOW_DIALOG_PVR_OSD_CHANNELS',
                    'DialogPVRChannelsOSD.xml'),
    10609: WinField(10609, 'pvrchannelguide', 'WINDOW_DIALOG_PVR_CHANNEL_GUIDE',
                    'DialogPVRChannelGuide.xml'),
    10610: WinField(10610, 'pvrradiordsinfo', 'WINDOW_DIALOG_PVR_RADIO_RDS_INFO',
                    'DialogPVRRadioRDSInfo.xml'),
    10611: WinField(10611, 'pvrrecordingsettings', 'WINDOW_DIALOG_PVR_RECORDING_SETTING',
                    'DialogSettings.xml'),
    10612: WinField(10612, '', 'WINDOW_DIALOG_PVR_CLIENT_PRIORITIES',
                    'DialogSettings.xml'),
    10613: WinField(10613, 'pvrguidecontrols', 'WINDOW_DIALOG_PVR_GUIDE_CONTROLS', None),
    10700: WinField(10700, 'tvchannels', 'WINDOW_TV_CHANNELS', 'MyPVRChannels.xml'),
    10701: WinField(10701, 'tvrecordings', 'WINDOW_TV_RECORDINGS', 'MyPVRRecordings.xml'),
    10702: WinField(10702, 'tvguide', 'WINDOW_TV_GUIDE', 'MyPVRGuide.xml'),
    10703: WinField(10703, 'tvtimers', 'WINDOW_TV_TIMERS', 'MyPVRTimers.xml'),
    10704: WinField(10704, 'tvsearch', 'WINDOW_TV_SEARCH', 'MyPVRSearch.xml'),
    10705: WinField(10705, 'radiochannels', 'WINDOW_RADIO_CHANNELS',
                    'MyPVRChannels.xml'),
    10706: WinField(10706, 'radiorecordings', 'WINDOW_RADIO_RECORDINGS',
                    'MyPVRRecordings.xml'),
    10707: WinField(10707, 'radioguide', 'WINDOW_RADIO_GUIDE', 'MyPVRGuide.xml'),
    10708: WinField(10708, 'radiotimers', 'WINDOW_RADIO_TIMERS', 'MyPVRTimers.xml'),
    10709: WinField(10709, 'radiosearch', 'WINDOW_RADIO_SEARCH', 'MyPVRSearch.xml'),
    10710: WinField(10710, 'tvtimerrules', 'WINDOW_TV_TIMER_RULES', 'MyPVRTimers.xml'),
    10711: WinField(10711, 'radiotimerrules', 'WINDOW_RADIO_TIMER_RULES',
                    'MyPVRTimers.xml'),
    10800: WinField(10800, 'fullscreenlivetv', 'WINDOW_FULLSCREEN_LIVETV', None),
    # None # WinField(shortcut to fullscreenvideo),
    10801: WinField(10801, 'fullscreenradio', 'WINDOW_FULLSCREEN_RADIO', None),
    # None WinField(shortcut to visualisation),
    10802: WinField(10802, 'fullscreenlivetvpreview', 'WINDOW_FULLSCREEN_LIVETV_PREVIEW',
                    None),
    # None WinField(shortcut to fullscreenlivetv),
    10803: WinField(10803, 'fullscreenradiopreview', 'WINDOW_FULLSCREEN_RADIO_PREVIEW',
                    None),
    # None WinField(shortcut to fullscreenradio
    10804: WinField(10804, 'fullscreenlivetvinput', 'WINDOW_FULLSCREEN_LIVETV_INPUT',
                    None),
    # None WinField(shortcut to fullscreenlivetv),
    10805: WinField(10805, 'fullscreenradioinput', 'WINDOW_FULLSCREEN_RADIO_INPUT', None),
    # None WinField(shortcut to fullscreenradio),
    10820: WinField(10820, 'gamecontrollers', 'WINDOW_DIALOG_GAME_CONTROLLERS',
                    'DialogGameControllers.xml'),
    10821: WinField(10821, 'games', 'WINDOW_GAMES', 'MyGames.xml'),
    10822: WinField(10822, 'gameosd', 'WINDOW_DIALOG_GAME_OSD', 'GameOSD.xml'),
    10823: WinField(10823, 'gamevideofilter', 'WINDOW_DIALOG_GAME_VIDEO_FILTER',
                    'DialogSelect.xml'),
    10824: WinField(10824, 'gameviewmode', 'WINDOW_DIALOG_GAME_STRETCH_MODE',
                    'DialogSelect.xml'),
    10825: WinField(10825, 'gamevolume', 'WINDOW_DIALOG_GAME_VOLUME',
                    'DialogVolumeBar.xml'),
    10826: WinField(10826, 'gameadvancedsettings', 'WINDOW_DIALOG_GAME_ADVANCED_SETTINGS',
                    'DialogAddonSettings.xml'),
    10827: WinField(10827, 'gamevideorotation', 'WINDOW_DIALOG_GAME_VIDEO_ROTATION',
                    'DialogSelect.xml'),
    10828: WinField(10828, 'gameports', 'WINDOW_DIALOG_GAME_PORTS',
                    'DialogGameControllers.xml'),
    10829: WinField(10829, 'ingamesaves', 'WINDOW_DIALOG_IN_GAME_SAVES',
                    'DialogSelect.xml'),
    10830: WinField(10830, 'gamesaves', 'WINDOW_DIALOG_GAME_SAVES', 'DialogSelect.xml'),
    10831: WinField(10831, 'gameagents', 'WINDOW_DIALOG_GAME_AGENTS',
                    'DialogGameControllers.xml'),
    # 11100 to 11199 Reserved for  Windows Custom Skin - - custom*'.xml'),
    12000: WinField(12000, 'selectdialog', 'WINDOW_DIALOG_SELECT', 'DialogSelect.xml'),
    12001: WinField(12001, 'musicinformation', 'WINDOW_DIALOG_MUSIC_INFO',
                    'DialogMusicInfo.xml'),
    12002: WinField(12002, 'okdialog', 'WINDOW_DIALOG_OK', 'DialogConfirm.xml'),
    12003: WinField(12003, 'movieinformation', 'WINDOW_DIALOG_VIDEO_INFO',
                    'DialogVideoInfo.xml'),
    12005: WinField(12005, 'fullscreenvideo', 'WINDOW_FULLSCREEN_VIDEO',
                    'VideoFullScreen.xml'),
    12006: WinField(12006, 'visualisation', 'WINDOW_VISUALISATION',
                    'MusicVisualisation.xml'),
    12007: WinField(12007, 'slideshow', 'WINDOW_SLIDESHOW', 'SlideShow.xml'),
    12008: WinField(12008, 'dialogcolorpicker', 'WINDOW_DIALOG_COLOR_PICKER',
                    'DialogColorPicker.xml'),
    # Added in Kodi v20 Nexus
    12600: WinField(12600, 'weather', 'WINDOW_WEATHER', 'MyWeather.xml'),
    12900: WinField(12900, 'screensaver', 'WINDOW_SCREENSAVER', None),  # none
    12901: WinField(12901, 'videoosd', 'WINDOW_DIALOG_VIDEO_OSD',
                    'VideoOSD.xml'),
    12902: WinField(12902, 'videomenu', 'WINDOW_VIDEO_MENU', None),  # none
    12905: WinField(12905, 'videotimeseek', 'WINDOW_VIDEO_TIME_SEEK', None),  # none
    12906: WinField(12906, 'fullscreengame', 'WINDOW_FULLSCREEN_GAME', None),  # none
    12997: WinField(12997, 'splash', 'WINDOW_SPLASH', None),
    12998: WinField(12998, 'startwindow', 'WINDOW_START', None),
    # shortcut to the current startwindow
    12999: WinField(12999, 'startup', 'WINDOW_STARTUP_ANIM', 'Startup.xml')
}


# 13000 -13099 Reserved for Python Windows - WINDOW_ID's
# 14000 -14099 Reserved for addons

winTexts: Dict[int, Tuple[int, Any]] = {}

winExtraTexts = {10000: (
    555, '$INFO[System.Time]', 8, '$INFO[Weather.Temperature]',
    '$INFO[Weather.Conditions]'),
    # Home
    10146             : (21863,  # Addon Info Dialog
                         '$INFO[ListItem.Property(Addon.Creator)]',
                         19114,
                         '$INFO[ListItem.Property(Addon.Version)]',
                         21821, '$INFO[ListItem.Property(Addon.Description)]'
                         )
}

itemExtraTexts = {}

winListItemProperties = {10040: ('$INFO[ListItem.Property(Addon.Status)]',)

                         }


def getWindowAddonID(win_id: int) -> str:
    addon_id: str = None
    path: str = xbmc.getInfoLabel(f'Window({win_id}).Property(xmlfile)')
    addon_id: str = path.replace('\\', '/').split('/addons/', 1)[-1].split('/', 1)[0]
    return addon_id


def getWindowAddonName(winID: int) -> str:
    addonID: str = getWindowAddonID(winID)
    return xbmc.getInfoLabel(f'System.AddonTitle({addonID})') or addonID

# WinField = namedtuple('WinField', ['msg_id', 'window_name', 'definition',
#                                          'source'])


def getWindowName(winID: int) -> str:
    name = None
    if winID in window_map:
        name_id: str | int = window_map[winID].msg_id
        if isinstance(name_id, int):
            name = xbmc.getLocalizedString(name_id)
            window_name: str = window_map[winID].window_name
        module_logger.debug(f'winID: {winID} name_id: {name_id} window '
                            f"name: {name} currentWindow: "
                            f"{xbmc.getInfoLabel('System.CurrentWindow')}")
    elif winID > 12999:
        return getWindowAddonName(winID)
    return name or xbmc.getInfoLabel('System.CurrentWindow') \
        or Messages.get_msg(Messages.UNKNOWN)  # T(unknown)


def convertTexts(winID: int,
                 data_list: Tuple | List, phrases: PhraseList) -> bool:
    """

    :param winID:
    :param data_list:  # winExtraTexts | itemExtraTexts | winListItemProperties
    :param phrases:
    :return:
    """
    start_len: int = len(phrases)
    for sid in data_list:
        if isinstance(sid, int):
            sid = xbmc.getLocalizedString(sid)
        elif sid.isdigit():  # Single digit?
            sid = xbmc.getInfoLabel(f'Control.GetLabel({sid})')
        elif sid.startswith('$INFO['):
            info = sid[6:-1]
            sid = xbmc.getInfoLabel(info)
        if sid:
            phrases.create(texts=sid)
    if len(phrases) > start_len:
        return True
    return False


def getWindowTexts(winID: int, phrases: PhraseList, table=winTexts) -> bool:
    """

    :param winID:
    :param phrases:
    :param table:
    :return:
    """
    if winID not in table:
        return False
    return convertTexts(winID, table[winID], phrases)


def getExtraTexts(winID: int, phrases: PhraseList) -> bool:
    return getWindowTexts(winID, phrases, table=winExtraTexts)


def getItemExtraTexts(winID: int, phrases: PhraseList) -> bool:
    return getWindowTexts(winID, phrases, table=itemExtraTexts)


def getListItemProperty(winID: int, phrases: PhraseList) -> bool:
    tmp_phrases: PhraseList = PhraseList(check_expired=False)
    success: bool = getWindowTexts(winID, tmp_phrases,
                                   table=winListItemProperties)
    texts: List[str] = []
    for phrase in tmp_phrases:
        phrase: Phrase
        texts.append(phrase.get_text())
    if len(texts) == 0:
        return False
    phrases.add_text(texts=(','.join(texts)))
    return True

def getSongInfo() -> List[str] | None:
    if xbmc.getCondVisibility('ListItem.IsFolder'):
        return None
    title = xbmc.getInfoLabel('ListItem.Title')
    genre = xbmc.getInfoLabel('ListItem.Genre')
    duration = xbmc.getInfoLabel('ListItem.Duration')
    if not (title or genre or duration):
        return None
    ret = []
    if title:
        ret.append(xbmc.getLocalizedString(556))
        ret.append(title)
    if genre:
        ret.append(xbmc.getLocalizedString(515))
        ret.append(genre)
    if duration:
        ret.append(xbmc.getLocalizedString(180))
        ret.append(duration)
    return ret
