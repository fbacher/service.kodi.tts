# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import hashlib
import json
import os

import xbmc

from common import *

from common.constants import Constants
from common.logger import *
from common.settings import Settings

MY_LOGGER = BasicLogger.get_logger(__name__)

DATAPATH = os.path.join(Constants.PROFILE_PATH, 'addon_data.json')
BASE = '{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddons", "params": {' \
       '"enabled": true,"properties": ["name","version"]}}'
NEW_VERSIONS = False


def getAddonsMD5():
    return hashlib.md5(xbmc.executeJSONRPC(BASE).encode('utf-8')).hexdigest()


def saveAddonsMD5(md5):
    MY_LOGGER.debug_v('addoninfo.saveAddonsMD5')
    Settings.set_addons_md5(md5)


def loadAddonsMD5():
    MY_LOGGER.debug_v('addoninfo.loadAddonsMD5')
    return Settings.get_addons_md5()


def initAddonsData(force=False):
    if not force and loadAddonsMD5() and os.path.exists(DATAPATH):
        return
    md5 = getAddonsMD5()
    saveAddonsMD5(md5)
    jsonString = xbmc.executeJSONRPC(BASE)
    with open(DATAPATH, 'w', encoding='utf-8') as f:
        f.write(jsonString)


def getAddonsDetails():
    data = json.loads(xbmc.executeJSONRPC(BASE))
    details = data['result']['addons']
    return details


def loadAddonsDetails(as_dict=False):
    if not os.path.exists(DATAPATH):
        return None
    with open(DATAPATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    detailsList = data['result']['addons']
    if as_dict:
        return dict((d['addonid'], d) for d in detailsList)
    return detailsList


def checkForNewVersions():
    last = loadAddonsMD5()
    new = getAddonsMD5()
    if last != new:
        saveAddonsMD5(new)
        return True
    return False


def getUpdatedAddons():
    details = loadAddonsDetails(as_dict=True)
    if not details:
        return None
    new = getAddonsDetails()
    ret = []
    for n in new:
        nid = n['addonid']
        if nid in details:
            # print '{0} {1} {2}'.format(nid,n['version'],details[nid]['version'])
            if not n['version'] == details[nid]['version']:
                ret.append(n)
        else:
            ret.append(n)
    initAddonsData(force=True)
    return ret
