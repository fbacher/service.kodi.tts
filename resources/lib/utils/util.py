# -*- coding: utf-8 -*-

import os
import re
import time
import locale

import xbmc
import xbmcaddon
import xbmcvfs

from common.settings import Settings
from common.constants import Constants
from common.logger import *
from common import utils

module_logger = BasicLogger.get_module_logger(module_path=__file__)

ADDON_ID = 'service.kodi.tts'
ADDON = xbmcaddon.Addon(ADDON_ID)
T = xbmcaddon.Addon(ADDON_ID).getLocalizedString
XT = xbmc.getLocalizedString
ADDON_PATH = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')

LOG_PATH = os.path.join(xbmcvfs.translatePath('special://logpath'), 'kodi.log')

DISABLE_PATH = os.path.join(xbmcvfs.translatePath(
    'special://profile'), 'addon_data', ADDON_ID, 'DISABLED')
ENABLE_PATH = os.path.join(xbmcvfs.translatePath(
    'special://profile'), 'addon_data', ADDON_ID, 'ENABLED')

POSSIBLE_SETTINGS = ['language',
                     'voice',
                     'output',
                     'player',
                     'pitch',
                     'gender',
                     'speed',
                     'volume',
                     'pipe']

language_code = None

def sleep(ms):
    return utils.sleep(ms)


def abortRequested():
    return xbmc.Monitor().abortRequested()


def info(key):
    return xbmcaddon.Addon(ADDON_ID).getAddonInfo(key)


def backendsDirectory():
    return os.path.join(xbmcvfs.translatePath(info('path')), 'lib', 'backends')


def tailXBMCLog(num_lines=10):
    with open(LOG_PATH, "r") as f:
        f.seek(0, 2)
        fsize = f.tell()
        f.seek(max(fsize - 1024, 0), 0)
        lines = f.readlines()
    return lines[-num_lines:]


def getTmpfs():
    return utils.getTmpfs()


def getXBMCVersion():
    import json
    resp = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
    data = json.loads(resp)
    if not 'result' in data:
        return None
    if not 'version' in data['result']:
        return None
    return data['result']['version']


XBMC_VERSION_TAGS = ('prealpha', 'alpha', 'beta', 'releasecandidate', 'stable')


def versionTagCompare(tag1, tag2):
    t1 = -1
    t2 = -1
    for i in range(len(XBMC_VERSION_TAGS)):
        if XBMC_VERSION_TAGS[i] in tag1:
            t1 = i
        if XBMC_VERSION_TAGS[i] in tag2:
            t2 = i
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    if tag1 < tag2:
        return -1
    elif tag1 > tag2:
        return 1
    return 0


def getXBMCVersionTag(tag):
    versionInfo = xbmc.getInfoLabel('System.BuildVersion')
    v_t_g = re.split('[- ]', versionInfo)
    if not len(v_t_g) > 1:
        return tag
    return v_t_g[1].lower()


def xbmcVersionGreaterOrEqual(major, minor=0, tag=None):
    version = getXBMCVersion()
    if not version:
        return False
    if major < version['major']:
        return True
    elif major > version['major']:
        return False
    if minor < version['minor']:
        return True
    elif minor > version['minor']:
        return False
    if not tag:
        return True
    vtag = getXBMCVersionTag(version.get('tag'))
    if not vtag:
        return True
    tagCmp = versionTagCompare(tag, vtag)
    return tagCmp < 1


def get_language_code() -> str:
    global language_code
    if language_code is None:
        language_code, encoding = locale.getdefaultlocale()

        language = xbmc.getInfoLabel('System.Language')
        module_logger.debug_verbose('locale: ' + language_code)
        module_logger.debug_verbose('System.Language:' + language)
    return language_code
    #  awk '/locale.language/{ lang=$3; sub(".*resource.language.", "", lang); sub(
    #  "</setting>.*$", "", lang); print lang }' ../userdata/gui*.xml
    # json_query = json_call('Settings.GetSettingValue',
    #                       params={'setting': '%s' % setting}
    #                       )


def configuring_settings():
    return Settings.configuring_settings()


def getSetting(key, backend_id: str = None, default=None):
    return Settings.getSetting(key, backend_id, default)


def setSetting(key, value, backend_id: str = None):
    Settings.setSetting(key, value, backend_id)


def runInThread(func, args=(), name='?'):
    import threading
    thread = threading.Thread(target=func, args=args,
                              name=f'TTSThread: {name}')
    xbmc.log(f'util.runInThread starting thread {name}', xbmc.LOGINFO)
    thread.start()


BASE_COMMAND = 'XBMC.NotifyAll(service.kodi.tts,SAY,"{{\\"text\\":\\"{0}\\",\\"interrupt\\":{1}}}")'

# def safeEncode(text):
#   return binascii.hexlify(text.encode('utf-8'))

# def safeDecode(enc_text):
#    return binascii.unhexlify(enc_text)


def notifySayText(text, interrupt=False):
    command = BASE_COMMAND.format(text, repr(interrupt).lower())
    # print command
    xbmc.executebuiltin(command)


################################################################
# Deprecated in Gotham - now using NotifyAll
LAST_COMMAND_DATA = ''


def initCommands():
    global LAST_COMMAND_DATA
    LAST_COMMAND_DATA = ''
    setSetting('EXTERNAL_COMMAND', '')


def sendCommand(command):
    commandData: str = f'{time.time()}:{command}'
    setSetting('EXTERNAL_COMMAND', commandData)


def getCommand():
    global LAST_COMMAND_DATA
    commandData = getSetting('EXTERNAL_COMMAND', '')
    module_logger.debug_verbose('util.getCommand data: ' + commandData)
    if commandData == LAST_COMMAND_DATA:
        return None
    LAST_COMMAND_DATA = commandData
    return commandData.split(':', 1)[-1]


# End deprecated
################################################################


def init():
    pd = Constants.PROFILE_PATH
    if not os.path.exists(pd):
        os.makedirs(pd)


init()
