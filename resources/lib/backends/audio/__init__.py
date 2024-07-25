# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

from common import *
from common.constants import Constants
from common.logger import *

try:
    import xbmc
except:
    xbmc = None

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)
PLAYSFX_HAS_USECACHED: bool = False
BCM_2835_AVAIL: bool = None

try:
    voidWav: str = os.path.join(Constants.ADDON_DIRECTORY, 'resources', 'wavs',
                                'void.wav')
    xbmc.playSFX(voidWav, False)
    PLAYSFX_HAS_USECACHED = True
except AbortException:
    reraise(*sys.exc_info())
except:
    pass


def check_snd_bm2835() -> bool:
    if BCM_2835_AVAIL is None:
        try:
            bcm_2385_avail = 'snd_bcm2835' in subprocess.check_output(['lsmod'],
                                                                      universal_newlines=True)
        except AbortException:
            reraise(*sys.exc_info())
        except:
            module_logger.error('check_snd_bm2835(): lsmod filed')
            bcm_2385_avail = False
    return bcm_2385_avail


def load_snd_bm2835() -> None:
    try:
        if not xbmc or not xbmc.getCondVisibility('System.Platform.Linux'):
            return
    except AbortException:
        reraise(*sys.exc_info())
    except:  # Handles the case where there is an xbmc module installed system wide and
        # we're not running xbmc
        return
    if check_snd_bm2835():
        return
    import getpass
    # TODO: Maybe use util.raspberryPiDistro() to confirm distro
    if getpass.getuser() == 'root':
        module_logger.info(
                'OpenElec on RPi detected - loading snd_bm2835 module...')
        module_logger.info(os.system('modprobe snd-bcm2835')
                           and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS')
        # subprocess.call(['modprobe','snd-bm2835']) #doesn't work on OpenElec
        # (only tested) - can't find module
    elif getpass.getuser() == 'pi':
        module_logger.info('RaspBMC detected - loading snd_bm2835 module...')
        # Will just fail if sudo needs a password
        module_logger.info(os.system('sudo -n modprobe snd-bcm2835')
                           and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS')
    else:
        module_logger.info(
                'UNKNOWN Raspberry Pi - maybe loading snd_bm2835 module...')
        # Will just fail if sudo needs a password
        module_logger.info(os.system('sudo -n modprobe snd-bcm2835')
                           and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS')


"""
AfplayPlayer()
BuiltInAudioPlayer()
Mpg123AudioPlayer()
Mpg321AudioPlayer()
Mpg321OEPiAudioPlayer()
MPlayerAudioPlayer()
PlaySFXAudioPlayer()
PaplayAudioPlayer()
SOXAudioPlayer()
WindowsAudioPlayer()
"""


class AfplayPlayer:
    pass
