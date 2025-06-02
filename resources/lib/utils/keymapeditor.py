# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
from pathlib import Path
from threading import Timer

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from common import *

from common import utils
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)

ACTIONS = (
    ('REPEAT', 'f1'),
    ('EXTRA', 'f2'),
    ('ITEM_EXTRA', 'f3'),
    ('STOP', 'f4'),
    ('SETTINGS', 'f6'),
    ('DISABLE', 'f12'),
    ('VOL_UP', 'numpadplus mod="ctrl"'),
    ('VOL_DOWN', 'numpadminus mod="ctrl"')

)

BASIC_ACTIONS = (
    ('DISABLE', 'f12'),
)


def processCommand(command):
    if command == 'INSTALL_DEFAULT':
        installDefaultKeymap()
    elif command == 'INSTALL_CUSTOM':
        installCustomKeymap()
    elif command == 'EDIT':
        editKeymap()
    elif command == 'RESET':
        resetKeymap()
    elif command == 'REMOVE':
        removeKeymap()


def _keymapTarget() -> Path:
    return Constants.KEYMAPS_PATH / 'service.kodi.tts.keyboard.xml'


def _keymapSource(kind='base') -> Path:
    source: Path = Constants.KEYMAPS_PROTO_PATH / f'keymap.{kind}.xml'
    MY_LOGGER.debug(f'keymap source: {source}')
    return source


def _keyMapDefsPath() -> Path:
    return Constants.PROFILE_PATH / 'custom.keymap.defs'


def loadCustomKeymapDefs():
    path: Path = _keyMapDefsPath()
    if not path.exists():
        return {}
    with path.open('r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    defs = {}
    try:
        for l in lines:
            if not l:
                continue
            key, val = l.split("=", 1)
            defs[key] = val
        return defs
    except:
        MY_LOGGER.error('Error reading custom keymap definitions')
    return {}


def saveCustomKeymapDefs(defs):
    out = ''
    for k, v in list(defs.items()):
        out += '{0}={1}\n'.format(k, v)
    path: Path = _keyMapDefsPath()
    with path.open('w', encoding='utf-8') as f:
        f.write(out)


def installDefaultKeymap(quiet=False):
    buildKeymap(defaults=True)
    if not quiet:
        xbmcgui.Dialog().ok(Messages.get_msg(Messages.INSTALLED),
                            Messages.get_msg(Messages.DEFAULT_KEYMAP_INSTALLED))


def installBasicKeymap() -> bool:
    restart: bool = False
    target_path: Path = _keymapTarget()
    if target_path.exists():
        MY_LOGGER.debug(f'keymap {target_path} already exists. Delete before replacing')
        return restart

    xml = None
    key_map: Path = _keymapSource('basic')
    if not key_map.exists():
        MY_LOGGER.debug(f'{key_map} prototype keymap {key_map} does NOT exist.')
        return restart
    with _keymapSource('basic').open('r', encoding='utf-8') as f:
        xml = f.read()
    if xml:
        restart = True

    saveKeymapXML(xml)
    return restart


def installCustomKeymap():
    buildKeymap()
    xbmcgui.Dialog().ok(Messages.get_msg(Messages.UPDATED),
                        Messages.get_msg(Messages.CUSTOM_KEYMAP_INSTALLED))


def resetKeymap():
    saveCustomKeymapDefs({})
    buildKeymap()
    xbmcgui.Dialog().ok(Messages.get_msg(Messages.UPDATED),
                        Messages.get_msg(Messages.CUSTOM_KEYMAP_RESET))


def removeKeymap():
    target_path: Path = _keymapTarget()
    target_path.unlink(missing_ok=True)
    xbmc.executebuiltin("action(reloadkeymaps)")
    xbmcgui.Dialog().ok(Messages.get_msg(Messages.REMOVED),
                        Messages.get_msg(Messages.KEYMAP_REMOVED))


def saveKeymapXML(xml):
    target_path: Path = _keymapTarget()
    target_path.unlink(missing_ok=True)
    with target_path.open('w', encoding='utf-8') as f:
        f.write(xml)
    xbmc.executebuiltin("action(reloadkeymaps)")


def buildKeymap(defaults=False):  # TODO: Build XML with ElementTree?
    xml = None
    with _keymapSource().open('r', encoding='utf-8') as f:
        xml = f.read()
    if not xml:
        return
    if defaults:
        defs = {}
    else:
        defs = loadCustomKeymapDefs()
    for action, default in ACTIONS:
        key = defs.get(f'key.{action}')
        if key:
            xml = xml.replace(f'<{action}>',
                              f'<key id="{key}">').replace(
                    f'</{action}>', '</key>')
        else:
            xml = xml.replace(f'<{action}>', f'<{default}>'.replace(
                    f'</{action}>',
                    f'</{default.split(" ", 1)[0]}>'[0]))

    xml = xml.format(SPECIAL=SystemQueries.isPreInstalled() and 'kodi' or 'home')

    saveKeymapXML(xml)


def editKeymap():
    options = (
        ('Repeat Control ({0})', 'key.REPEAT'),
        ('Window Extra Info ({0})', 'key.EXTRA'),
        ('Item Extra Info ({0})', 'key.ITEM_EXTRA'),
        ('Stop Speech ({0})', 'key.STOP'),
        ('Addon Settings ({0})', 'key.SETTINGS'),
        ('Disable/Enable TTS Addon ({0})', 'key.DISABLE'),
        ('Volume Up ({0})', 'key.VOL_UP'),
        ('Volume Down ({0})', 'key.VOL_DOWN')
    )

    while True:
        defs = loadCustomKeymapDefs()
        items = []
        for i, ID in options:
            items.append(i.format(defs.get(ID) or 'Not Set'))

        idx = xbmcgui.Dialog().select('Actions', items)
        if idx < 0:
            return
        ID = options[idx][1]
        editKey(ID, defs)


def editKey(key_id, defs):
    key = KeyListener.record_key()
    if not key:
        return
    utils.notifySayText('Key set', interrupt=True)
    defs[key_id] = key
    saveCustomKeymapDefs(defs)


# Taken from takoi's Keymap Editor


class KeyListener(xbmcgui.WindowXMLDialog):
    TIMEOUT = 60

    def __new__(cls):
        return super(KeyListener, cls).__new__(cls, "DialogKaiToast.xml", "")

    def __init__(self):
        super().__init__()
        self.msg1 = Messages.get_msg(Messages.PRESS_KEY_TO_ASSIGN)
        self.msg2 = '{0}...'.format(Messages.TIMEOUT_IN_X_SECONDS) \
            .format('%.0f' % self.TIMEOUT)
        self.key = None

    def onInit(self):
        try:
            self.getControl(401).addLabel(self.msg1)
            self.getControl(402).addLabel(self.msg2)
        except AttributeError:
            self.getControl(401).setLabel(self.msg1)
            self.getControl(402).setLabel(self.msg2)
        externalWindowObj = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        externalWindowObj.setProperty('TTS.READER', 'keymapkeyinput')

    def onAction(self, action):
        if action == 9 or action == 10 or action == 92:
            self.close()
        else:
            code = action.getButtonCode()
            self.key = None if code == 0 else str(code)
            self.close()

    @staticmethod
    def record_key():
        dialog = KeyListener()
        timeout = Timer(KeyListener.TIMEOUT, dialog.close)
        timeout.start()
        dialog.doModal()
        timeout.cancel()
        key = dialog.key
        del dialog
        return key
