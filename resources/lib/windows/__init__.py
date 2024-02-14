# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *

from common.logger import BasicLogger
from .base import DefaultWindowReader, KeymapKeyInputReader, NullReader
from .busydialog import BusyDialogReader
from .contextmenu import ContextMenuReader
from .homedialog import HomeDialogReader
from .libraryviews import VideoLibraryWindowReader
from .playerstatus import PlayerStatusReader
from .progressdialog import ProgressDialogReader
from .pvr import (PVRChannelsWindowReader, PVRGuideWindowReader,
                  PVRRecordingsWindowReader,
                  PVRSearchWindowReader, PVRTimersWindowReader, PVRWindowReader)
from .pvrguideinfo import PVRGuideInfoReader
from .selectdialog import SelectDialogReader
from .settings import SettingsReader
from .subtitlesdialog import SubtitlesDialogReader
from .textviewer import TextViewerReader
from .videoinfodialog import VideoInfoDialogReader
from .virtualkeyboard import PVRSGuideSearchDialogReader, VirtualKeyboardReader
from .weather import WeatherReader
from .yesnodialog import YesNoDialogReader

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)

READERS = (
    HomeDialogReader,
    KeymapKeyInputReader,
    DefaultWindowReader,
    NullReader,
    ProgressDialogReader,
    VirtualKeyboardReader,
    PVRSGuideSearchDialogReader,
    PVRGuideInfoReader,
    TextViewerReader,
    BusyDialogReader,
    ContextMenuReader,
    PVRWindowReader,
    PVRGuideWindowReader,
    PVRChannelsWindowReader,
    PVRRecordingsWindowReader,
    PVRTimersWindowReader,
    PVRSearchWindowReader,
    VideoLibraryWindowReader,
    WeatherReader,
    PlayerStatusReader,
    SettingsReader,
    YesNoDialogReader,
    VideoInfoDialogReader,
    SelectDialogReader,
    SubtitlesDialogReader
)

READERS_WINID_MAP = {
    10000: HomeDialogReader,  # Home
    10004: SettingsReader,  # settings
    10012: SettingsReader,  # picturesettings
    10013: SettingsReader,  # programsettings
    10014: SettingsReader,  # weathersettings
    10015: SettingsReader,  # musicsettings
    10016: SettingsReader,  # systemsettings
    10017: SettingsReader,  # videosettings
    10018: SettingsReader,  # servicesettings
    10019: SettingsReader,  # appearancesettings
    10021: SettingsReader,  # livetvsettings
    10025: VideoLibraryWindowReader,  # videolibrary
    10030: SettingsReader,  # SettingsCategory.xml
    10031: SettingsReader,  # SettingsCategory.xml
    10032: SettingsReader,  # SettingsCategory.xml
    10034: SettingsReader,  # profilesettings
    10035: SettingsReader,  # SettingsCategory.xml
    14000: SettingsReader,  # pvrclientspecificsettings
    10100: YesNoDialogReader,  # yesnodialog
    10101: ProgressDialogReader,
    10103: VirtualKeyboardReader,
    10106: ContextMenuReader,
    10109: VirtualKeyboardReader,
    10120: PlayerStatusReader,  # musicosd
    10123: SettingsReader,  # osdvideosettings
    10124: SettingsReader,  # osdaudiosettings
    10131: SettingsReader,  # locksettings
    10132: SettingsReader,  # contentsettings
    10135: VideoInfoDialogReader,  # songinformation
    10138: BusyDialogReader,
    10140: SettingsReader,  # addonsettings
    10147: TextViewerReader,
    10150: SettingsReader,  # peripheralsettings
    10153: SubtitlesDialogReader,  # subtitlesdialog
    10501: VideoLibraryWindowReader,  # musicsongs
    10502: VideoLibraryWindowReader,  # musiclibrary
    10601: PVRWindowReader,  # pvr - Pre-Helix
    10602: PVRGuideInfoReader,
    10607: PVRSGuideSearchDialogReader,
    10615: PVRChannelsWindowReader,  # tvchannels
    10616: PVRRecordingsWindowReader,  # tvrecordings
    10617: PVRGuideWindowReader,  # tvguide
    10618: PVRTimersWindowReader,  # tvtimers
    10619: PVRSearchWindowReader,  # tvsearch
    10620: PVRChannelsWindowReader,  # radiochannels
    10621: PVRRecordingsWindowReader,  # radiorecordings
    10622: PVRGuideWindowReader,  # radioguide
    10623: PVRTimersWindowReader,  # radiotimers
    10624: PVRSearchWindowReader,  # radiosearch
    11102: TextViewerReader,
    12000: SelectDialogReader,
    12002: YesNoDialogReader,
    12003: VideoInfoDialogReader,  # videoinfodialog
    12005: PlayerStatusReader,  # fullscreenvideo
    12006: PlayerStatusReader,  # visualization
    12600: WeatherReader,
    12901: SettingsReader,  # videoosd
}

READERS_MAP = {}
for r in READERS:
    READERS_MAP[r.ID] = r


def getWindowReader(winID):
    xbmc.log(f'Window: {winID}', xbmc.LOGDEBUG)
    reader_id = xbmc.getInfoLabel(f'Window({winID}).Property(TTS.READER)')
    module_logger.debug(f'winID: {winID} reader: {reader_id}')
    if reader_id and reader_id in READERS_MAP:
        reader = READERS_MAP[reader_id]
        module_logger.debug(f'reader: {reader}')
        return reader
    reader = READERS_WINID_MAP.get(winID, DefaultWindowReader)
    module_logger.debug(f'default_window_reader: {reader}')
    return reader
