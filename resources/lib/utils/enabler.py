# -*- coding: utf-8 -*-
import os
import sys
import xbmc
import xbmcaddon
import xbmcvfs

DISABLE_PATH = os.path.join(xbmcvfs.translatePath('special://profile'), 'addon_data', 'service.kodi.tts', 'DISABLED')
ENABLE_PATH = os.path.join(xbmcvfs.translatePath('special://profile'), 'addon_data', 'service.kodi.tts', 'ENABLED')

def getXBMCVersion():
    import json
    resp = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
    data = json.loads(resp)
    if not 'result' in data: return None
    if not 'version' in data['result']: return None
    return data['result']['version']

BASE = '{ "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": { "addonid": "service.kodi.tts","enabled":%s}, "id": 1 }'


def enableAddon():
    if os.path.exists(DISABLE_PATH):
        os.remove(DISABLE_PATH)

    markPreOrPost(enable=True)

    if isPostInstalled():
        if addonIsEnabled():
            xbmc.executebuiltin('RunScript(service.kodi.tts)')
        else:
            xbmc.executeJSONRPC(BASE % 'true') #So enable it instead
    else:
        xbmc.executebuiltin('RunScript(service.kodi.tts)')


def disableAddon():
    if os.path.exists(ENABLE_PATH):
        os.remove(ENABLE_PATH)

    markPreOrPost(disable=True)

    if isPostInstalled():
        version = getXBMCVersion()
        if not version or version['major'] < 13: return #Disabling in this manner crashes on Frodo
        xbmc.executeJSONRPC(BASE % 'false') #Try to disable it
        #if res and 'error' in res: #If we have an error, it's already disabled
        #print res


def markPreOrPost(enable=False, disable=False):
    if os.path.exists(ENABLE_PATH) or enable:
        with open(ENABLE_PATH, 'w') as f:
            f.write(isPostInstalled() and 'POST' or 'PRE')

    if os.path.exists(DISABLE_PATH) or disable:
        with open(DISABLE_PATH, 'w') as f:
            f.write(isPostInstalled() and 'POST' or 'PRE')

def addonIsEnabled():
    if os.path.exists(DISABLE_PATH):
        return False

    if isPostInstalled():
        import json
        resp = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails", "params": {"addonid":"service.kodi.tts","properties": ["name","version","enabled"]}}')
        data = json.loads(resp)
        if 'result' not in data: return False
        if 'addon' not in data['result']: return False
        if 'enabled' not in data['result']['addon']: return False
        return data['result']['addon']['enabled']
    else:
        return True


def toggleEnabled():
    try:
        if not addonIsEnabled(): raise Exception('Addon Disabled')
        xbmcaddon.Addon('service.kodi.tts')
        xbmc.log('service.kodi.tts: DISABLING')
        xbmc.executebuiltin('RunScript(service.kodi.tts,key.SHUTDOWN)')
    except:
        xbmc.log('service.kodi.tts: ENABLING')
        enableAddon()


def reset():
    if not addonIsEnabled(): return
    disableAddon()
    ct=0
    while addonIsEnabled() and ct < 11:
        xbmc.sleep(500)
        ct+=1
    enableAddon()


def isPostInstalled():
    homePath = xbmcvfs.translatePath('special://home')
    postInstalledPath = os.path.join(homePath, 'addons', 'service.kodi.tts')
    return os.path.exists(postInstalledPath)


if __name__ == '__main__':
    arg = None
    if len(sys.argv) > 1: arg = sys.argv[1]
    if arg == 'RESET':
        reset()
    else:
        toggleEnabled()