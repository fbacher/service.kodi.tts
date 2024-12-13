# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import locale
import os
import re

import xbmc
import xbmcaddon
import xbmcvfs

from common import *

from backends.settings.setting_properties import SettingsProperties
from common import utils
from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.garbage_collector import GarbageCollector
from common.logger import *
from common.monitor import Monitor
from common.settings import Settings

module_logger = BasicLogger.get_logger(__name__)

ADDON_ID = 'service.kodi.tts'
ADDON = xbmcaddon.Addon(ADDON_ID)
T = CriticalSettings.ADDON.getLocalizedString
XT = xbmc.getLocalizedString
ADDON_PATH = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')

LOG_PATH = os.path.join(xbmcvfs.translatePath('special://logpath'), 'kodi.log')

DISABLE_PATH = os.path.join(xbmcvfs.translatePath(
        'special://profile'), 'addon_data', ADDON_ID, 'DISABLED')
ENABLE_PATH = os.path.join(xbmcvfs.translatePath(
        'special://profile'), 'addon_data', ADDON_ID, 'ENABLED')

POSSIBLE_SETTINGS = ['language',
                     SettingsProperties.VOICE,
                     'output',
                     'player',
                     SettingsProperties.PITCH,
                     'gender',
                     SettingsProperties.SPEED,
                     SettingsProperties.VOLUME,
                     'pipe']

language_code = None


def sleep(ms):
    return utils.sleep(ms)


def info(key):
    return xbmcaddon.Addon(ADDON_ID).getAddonInfo(key)


def backendsDirectory():
    return os.path.join(xbmcvfs.translatePath(info('path')), 'lib', 'backends')


def tailXBMCLog(num_lines=10):
    with open(LOG_PATH, "r", encoding='utf-8') as f:
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
            '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {'
            '"properties": ["version", "name"]}, "id": 1 }')
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
        module_logger.debug_v('locale: ' + language_code)
        module_logger.debug_v('System.Language:' + language)
    return language_code


def configuring_settings():
    return Settings.configuring_settings()


def getSetting(key, engine_id: str = None, default=None):
    return Settings.getSetting(key, engine_id, default)


def setSetting(key, value, engine_id: str = None):
    Settings.setSetting(key, value, engine_id)


def runInThread(func: Callable, args: List[Any] = [], name: str = '?',
                delay: float = 0.0, **kwargs) -> None:
    import threading
    thread = threading.Thread(target=thread_wrapper, name=f'Utl_{name}',
                              args=args, kwargs={'target': func,
                                                 'delay' : delay, **kwargs})
    xbmc.log(f'util.runInThread starting thread {name}', xbmc.LOGINFO)
    thread.start()
    GarbageCollector.add_thread(thread)


def thread_wrapper(*args, **kwargs):
    try:
        target: Callable = kwargs.pop('target')
        delay: float = kwargs.pop('delay')
        if delay is not None and isinstance(delay, float):
            Monitor.exception_on_abort(delay)

        target(*args, **kwargs)
    except AbortException:
        return  # Let thread die
    except Exception as e:
        module_logger.exception('')


BASE_COMMAND = ('XBMC.NotifyAll(service.kodi.tts,SAY,"{{\\"text\\":\\"{0}\\",'
                '\\"interrupt\\":{1}}}")')


# def safeEncode(text):
#   return binascii.hexlify(text.encode('utf-8'))

# def safeDecode(enc_text):
#    return binascii.unhexlify(enc_text)

def notifySayText(text, interrupt=False):
    command = BASE_COMMAND.format(text, repr(interrupt).lower())
    command = f'XBMC.NotifyAll(service.kodi.tts,SAY,' \
              f'"{{\\"text\\":\\"{text}\\",\\"interrupt\\":{interrupt}}}")'.lower()
    # print command
    xbmc.executebuiltin(command)


def get_non_negative_int(control_expr: str | int) -> int:
    """
    Attempts to convert control_expr to an int

    :param control_expr: String representation of an int id, or
    some non-control-id
    :return: abs(int value of control_expr), or -1 if control_expr
        is not an int
    """
    try:
        return abs(int(control_expr))
    except ValueError:
        return -1


def init():
    pd = Constants.PROFILE_PATH
    if not os.path.exists(pd):
        os.makedirs(pd)


init()
