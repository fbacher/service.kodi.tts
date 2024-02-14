# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from common import *

from common.critical_settings import *

BASE_COMMAND = ('XBMC.NotifyAll(service.kodi.tts,SAY,"{{\\"text\\":\\"{0}\\",'
                '\\"interrupt\\":{1}}}")')


# def safeEncode(text):
#    return binascii.hexlify(text.encode('utf-8'))

# def safeDecode(enc_text):
#    return binascii.unhexlify(enc_text)


def sayText(text, interrupt=False):
    command = BASE_COMMAND.format(text, repr(interrupt).lower())
    # print command
    xbmc.executebuiltin(command)


def stop():
    xbmc.executebuiltin(f'XBMC.NotifyAll({CriticalSettings.ADDON_ID}),STOP)')
