# -*- coding: utf-8 -*-

import hashlib
import io
import os
import pickle

import xbmc
import xbmcvfs

from common.constants import Constants
from common.logger import LazyLogger
from common.settings import Settings
from cache.voicecache import VoiceCache


module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


class MyMonitor(xbmc.Monitor):

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(self.__class__.__name__)  # type: LazyLogger

    def onSettingsChanged(self):
        self._logger.debug_verbose('Settings changed,clearing shadow_settings')
        self.settings_changed()

    def settings_changed(self):
        change_file = xbmcvfs.translatePath(
            'special://userdata/addon_data/{}/settings_changed.pickle'.format(Constants.ADDON_ID))
        settings_file = xbmcvfs.translatePath(
            'special://userdata/addon_data/{}/settings.xml'.format(Constants.ADDON_ID))

        with io.open(settings_file, mode='rb') as settings_file_fd:
            settings = settings_file_fd.read()
            new_settings_digest = hashlib.md5(settings).hexdigest()

        changed = False
        change_record = dict()
        if not os.path.exists(change_file):
            changed = True
        else:
            if not os.access(change_file, os.R_OK | os.W_OK):
                self._logger.error('No rw access: {}'.format(change_file))
                changed = True
                try:
                    os.remove(change_file)
                except Exception as e:
                    self._logger.error('Can not delete {}'.format(change_file))

        if not changed:
            try:
                settings_digest = None
                with io.open(change_file, mode='rb') as settings_changed_fd:
                    change_record = pickle.load(settings_changed_fd)
                    settings_digest = change_record.get(
                        Settings.SETTINGS_DIGEST, None)

                if new_settings_digest != settings_digest:
                    changed = True

            except (IOError) as e:
                self._logger.error('Error reading {} or {}'.format(
                    change_file, settings_file))
                changed = True
            except (Exception) as e:
                self._logger.error('Error processing {} or {}'.format(
                    change_file, settings_file))
                changed = True

        if changed:
            change_record[Settings.SETTINGS_DIGEST] = new_settings_digest
            with io.open(change_file, mode='wb') as change_file_fd:
                pickle.dump(change_record, change_file_fd)

        #  TODO: Change to callback

            VoiceCache.clean_cache(changed)
        else:
            VoiceCache.clean_cache(changed)


my_monitor = MyMonitor()