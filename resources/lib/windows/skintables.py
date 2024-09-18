# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc
import xbmcvfs

from common import *
from common.logger import BasicLogger

from common.messages import Messages
from common.phrases import Phrase, PhraseList
module_logger = BasicLogger.get_logger(__name__)

quartz = {10000:
              {301: {'name': 20342, 'prefix': Messages.get_msg(Messages.SECTION)},
               # Movies
               302: {'name': 20343, 'prefix': Messages.get_msg(Messages.SECTION)},
               # TV Shows
               303: {'name': 2, 'prefix': Messages.get_msg(Messages.SECTION)},  # Music
               304: {'name': 1, 'prefix': Messages.get_msg(Messages.SECTION)},  # Pictures
               305: {'name': 24001, 'prefix': Messages.get_msg(Messages.SECTION)},
               # Addons
               306: {'name': 'Kodi', 'prefix': Messages.get_msg(Messages.SECTION)},
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


def getControlText(winID, control_id, phrases: PhraseList) -> bool:
    table = CURRENT_SKIN_TABLE
    if not table:
        return False
    if winID not in table:
        return False
    if control_id not in table[winID]:
        return False
    label = table[winID][control_id]['name']
    if isinstance(label, int):
        label = xbmc.getLocalizedString(label)
    if label is None:
        return False
    if 'prefix' not in table[winID][control_id]:
        return False

    phrases.add_text(texts=f"{table[winID][control_id]['prefix']}: {label}")
    return True


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
