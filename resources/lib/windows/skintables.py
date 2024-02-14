# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc
import xbmcvfs

from common import *

from common.messages import Messages

quartz = {10000:
              {301: {'name': 20342, 'prefix': Messages.get_msg(Messages.SECTION)},
               # Movies
               302: {'name': 20343, 'prefix': Messages.get_msg(Messages.SECTION)},
               # TV Shows
               303: {'name': 2, 'prefix': Messages.get_msg(Messages.SECTION)},  # Music
               304: {'name': 1, 'prefix': Messages.get_msg(Messages.SECTION)},  # Pictures
               305: {'name': 24001, 'prefix': Messages.get_msg(Messages.SECTION)},
               # Addons
               306: {'name': 'X B M C', 'prefix': Messages.get_msg(Messages.SECTION)},
               312: {'name': 20387, 'prefix': Messages.get_msg(Messages.AREA)},
               # Recently added tv shows
               313: {'name': 359, 'prefix': Messages.get_msg(Messages.AREA)},
               # Recently added albums
               }

          }

skins = {'quartz': quartz
         }

CURRENT_SKIN_TABLE = None
CURRENT_SKIN = None


def getControlText(winID, controlID):
    table = CURRENT_SKIN_TABLE
    if not table:
        return
    if not winID in table:
        return
    if not controlID in table[winID]:
        return
    label = table[winID][controlID]['name']
    if isinstance(label, int):
        label = xbmc.getLocalizedString(label)
    if not label:
        return
    if not 'prefix' in table[winID][controlID]:
        return label
    return '{0}: {1}'.format(table[winID][controlID]['prefix'], label)


def getSkinTable():
    global CURRENT_SKIN
    import os
    skinPath = xbmcvfs.translatePath('special://skin')
    skinName = os.path.basename(skinPath.rstrip('\/')).split('skin.', 1)[-1]
    CURRENT_SKIN = skinName
    print('service.kodi.tts: SKIN: %s' % skinName)
    return skins.get(skinName)


def updateSkinTable():
    global CURRENT_SKIN_TABLE
    CURRENT_SKIN_TABLE = getSkinTable()


updateSkinTable()
