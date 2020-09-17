# -*- coding: utf-8 -*-
import xbmc

from common.messages import Messages
from common.constants import Constants
from common.settings import Settings
from common.logger import LazyLogger

'''
Table data format:
integer: XBMC localized string ID
string integer: controll ID
$INFO[<infolabel>]: infolabel
string: normal string
'''

winNames = {    10000: 10000, #Home
                10001: 10001, #programs
                10002: 10002, #pictures
                10003: 10003, #filemanager
                10004: 10004, #settings
                10005: 10005, #music
                10006: 10006, #video
                10007: 10007, #systeminfo
                10011: 10011, #screencalibration
                10012: 10012, #picturessettings
                10013: 10013, #programssettings
                10014: 10014, #weathersettings
                10015: 10015, #musicsettings
                10016: 10016, #systemsettings
                10017: 10017, #videossettings
                10018: 10018, #servicesettings
                10019: 10019, #appearancesettings
                10020: 10020, #scripts
                10021: Messages.get_msg(Messages.LIVE_TV_SETTINGS), #Live TV Settings
                10024: 10024, #videofiles: Removed in Gotham
                10025: 10025, #videolibrary
                10028: 10028, #videoplaylist
                10029: 10029, #loginscreen
                10034: 10034, #profiles
                10040: 10040, #addonbrowser
                10100: 10100, #yesnodialog
                10101: 10101, #progressdialog
                10103: Messages.get_msg(Messages.VIRTUAL_KEYBOARD),
                10104: Messages.get_msg(Messages.VOLUME_BAR),
                10106: Messages.get_msg(Messages.CONTEXT_MENU),
                10107: Messages.get_msg(Messages.INFO_DIALOG),
                10109: Messages.get_msg(Messages.NUMERIC_INPUT),
                10111: Messages.get_msg(Messages.SHUTDOWN_MENU),
                10113: 'mute bug',
                10114: Messages.get_msg(Messages.PLAYER_CONTROLS),
                10115: Messages.get_msg(Messages.SEEK_BAR),
                10120: Messages.get_msg(Messages.MUSIC_OSD),
                10122: Messages.get_msg(Messages.VISUALISATION_PRESET_LIST),
                10123: Messages.get_msg(Messages.OSD_VIDEO_SETTINGS),
                10124: Messages.get_msg(Messages.OSD_AUDIO_SETTINGS),
                10125: Messages.get_msg(Messages.VIDEO_BOOKMARKS),
                10126: Messages.get_msg(Messages.FILE_BROWSER),
                10128: Messages.get_msg(Messages.NETWORK_SETUP),
                10129: Messages.get_msg(Messages.MEDIA_SOURCE),
                10130: 10034, #profilesettings
                10131: 20043, #locksettings
                10132: 20333, #contentsettings
                10134: 1036, #favourites
                10135: 658, #songinformation
                10136: Messages.get_msg(Messages.SMART_PLAYLIST_EDITOR),
                10137: 21421, #smartplaylistrule
                10138: Messages.get_msg(Messages.BUSY_DIALOG),
                10139: 13406, #pictureinfo
                10140: Messages.get_msg(Messages.ADDON_SETTINGS),
                10141: 1046, #accesspoints
                10142: Messages.get_msg(Messages.FULLSCREEN_INFO),
                10143: Messages.get_msg(Messages.KARAOKE_SELECTOR),
                10144: Messages.get_msg(Messages.KARAOKE_LARGE_SELECTOR),
                10145: Messages.get_msg(Messages.SLIDER_DIALOG),
                10146: Messages.get_msg(Messages.ADDON_INFORMATION),
                10147: Messages.get_msg(Messages.TEXT_VIEWER),
                10149: 35000, #peripherals
                10150: Messages.get_msg(Messages.PERIPHERAL_SETTINGS),
                10151: 10101, #extended progress dialog - using string for progress dialog
                10152: Messages.get_msg(Messages.MEDIA_FILTER),
                10153: Messages.get_msg(Messages.SUBTITLES_DIALOG),
                10500: 20011, #musicplaylist
                10501: 10501, #musicfiles
                10502: 10502, #musiclibrary
                10503: 10503, #musicplaylisteditor
                10601: Messages.get_msg(Messages.PVR),
                10602: Messages.get_msg(Messages.PVR_GUIDE_INFO),
                10603: Messages.get_msg(Messages.PVR_RECORDING_INFO),
                10604: Messages.get_msg(Messages.PVR_TIMER_SETTING),
                10605: Messages.get_msg(Messages.PVR_GROUP_MANAGER),
                10606: Messages.get_msg(Messages.PVR_CHANNEL_MANAGER),
                10607: Messages.get_msg(Messages.PVR_GUIDE_SEARCH),
                10610: Messages.get_msg(Messages.PVR_OSD_CHANNELS),
                10611: Messages.get_msg(Messages.PVR_OSD_GUIDE),
                10615: Messages.get_msg(Messages.PVR_TV_CHANNELS),
                10616: Messages.get_msg(Messages.PVR_TV_RECORDINGS),
                10617: Messages.get_msg(Messages.PVR_TV_GUIDE),
                10618: Messages.get_msg(Messages.PVR_TV_TIMERS),
                10619: Messages.get_msg(Messages.PVR_TV_SEARCH),
                10620: Messages.get_msg(Messages.PVR_RADIO_CHANNELS),
                10621: Messages.get_msg(Messages.PVR_RADIO_RECORDINGS),
                10622: Messages.get_msg(Messages.PVR_RADIO_GUIDE),
                10623: Messages.get_msg(Messages.PVR_RADIO_TIMERS),
                10624: Messages.get_msg(Messages.PVR_RADIO_TIMERS),
                11000: Messages.get_msg(Messages.PVR_RADIO_SEARCH),
                12000: 12000, #selectdialog
                12001: 12001, #musicinformation
                12002: 12002, #okdialog
                12003: 12003, #movieinformation
                12005: 12005, #fullscreenvideo
                12006: 12006, #visualisation
                12007: 108, #slideshow
                12008: 12008, #filestackingdialog
                12009: 13327, #karaoke
                12600: 12600, #weather
                12900: 12900, #screensaver
                12901: 12901, #videoosd
                12902: Messages.get_msg(Messages.VIDEO_MENU),
                12999: 512, #startup
                14000:  Messages.get_msg(Messages.PVR_CLIENT_SPECIFIC_SETTINGS)
}

winTexts = {}

winExtraTexts = {    10000:(555,'$INFO[System.Time]',8,'$INFO[Weather.Temperature]','$INFO[Weather.Conditions]'), #Home
                    10146:(    21863, #Addon Info Dialog
                            '$INFO[ListItem.Property(Addon.Creator)]',
                            19114,
                            '$INFO[ListItem.Property(Addon.Version)]',
                            21821,'$INFO[ListItem.Property(Addon.Description)]'
                    )
}

itemExtraTexts = {    }

winListItemProperties = {        10040:('$INFO[ListItem.Property(Addon.Status)]',)

}


def getWindowAddonID(winID):
    path = xbmc.getInfoLabel('Window({0}).Property(xmlfile)'.format(winID))
    addonID = path.replace('\\', '/').split('/addons/',1)[-1].split('/',1)[0]
    return addonID

def getWindowAddonName(winID):
    addonID = getWindowAddonID(winID)
    return xbmc.getInfoLabel('System.AddonTitle({0})'.format(addonID)) or addonID

def getWindowName(winID):
    name = None
    if winID in winNames:
        name = winNames[winID]
        if isinstance(name,int): name = xbmc.getLocalizedString(name)
    elif winID > 12999:
        return getWindowAddonName(winID)
    return name or xbmc.getInfoLabel('System.CurrentWindow') \
           or Messages.get_msg(Messages.UNKNOWN) #T(unknown)

def convertTexts(winID,data_list):
    ret = []
    for sid in data_list:
        if isinstance(sid,int):
            sid = xbmc.getLocalizedString(sid)
        elif sid.isdigit():
            sid = xbmc.getInfoLabel('Control.GetLabel({0})'.format(sid))
        elif sid.startswith('$INFO['):
            info = sid[6:-1]
            sid = xbmc.getInfoLabel(info)
        if sid: ret.append(sid)
    return ret

def getWindowTexts(winID,table=winTexts):
    if not winID in table: return None
    return convertTexts(winID,table[winID]) or None

def getExtraTexts(winID):
    return getWindowTexts(winID,table=winExtraTexts)

def getItemExtraTexts(winID):
    return getWindowTexts(winID,table=itemExtraTexts)

def getListItemProperty(winID):
    texts = getWindowTexts(winID,table=winListItemProperties)
    if not texts: return None
    return ','.join(texts)

def getSongInfo():
    if xbmc.getCondVisibility('ListItem.IsFolder'): return None
    title = xbmc.getInfoLabel('ListItem.Title')
    genre = xbmc.getInfoLabel('ListItem.Genre')
    duration = xbmc.getInfoLabel('ListItem.Duration')
    if not (title or genre or duration): return None
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

