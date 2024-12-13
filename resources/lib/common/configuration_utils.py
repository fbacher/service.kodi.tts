# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmcaddon
import xbmcgui

from common import *

from backends.backend_info_bridge import BackendInfoBridge
from common.constants import Constants
from common.logger import *
from common.settings import Settings
from common.settings_low_level import SettingsProperties

T = xbmcaddon.Addon(Constants.ADDON_ID).getLocalizedString
module_logger = BasicLogger.get_logger(__name__)


class ConfigUtils:

    _logger: BasicLogger = None

    # def busyDialog(func):
    #     def inner(*args, **kwargs):
    #         try:
    #             xbmc.executebuiltin("ActivateWindow(10138)")
    #             func(*args, **kwargs)
    #         finally:
    #             xbmc.executebuiltin("Dialog.Close(10138)")
    #     return inner

    @classmethod
    def init_class(cls):
        if cls._logger is None:
            cls._logger = module_logger

    @classmethod
    def selectBackend(cls):
        cls._logger.debug_v('selectBackend')
        choices = ['auto']
        display = [T(32184)]

        available = BackendInfoBridge.getAvailableBackends()
        for b in available:
            cls._logger.debug_v('backend: ' + b.displayName)
            choices.append(b.engine_id)
            display.append(b.displayName)
        idx = xbmcgui.Dialog().select(T(32181), display)
        if idx < 0:
            return
        cls._logger.debug_v('service.kodi.tts.util.selectBackend value: ' +
                            choices[idx] + ' idx: ' + str(idx))
        Settings.setSetting(SettingsProperties.ENGINE, choices[idx], None)

    @classmethod
    def selectPlayer(cls, engine_id):
        players = BackendInfoBridge.getPlayers(engine_id)
        if not players:
            xbmcgui.Dialog().ok(T(32182), T(32183))
            return
        players.insert(0, ('', T(32184)))
        disp = []
        for p in players:
            disp.append(p[1])
        idx = xbmcgui.Dialog().select(T(32185), disp)
        if idx < 0:
            return
        player: str = players[idx][0]
        cls._logger.info(f'Player for {engine_id} set to: {player}')
        Settings.set_player(player, engine_id)

    @classmethod
    def selectVoiceSetting(cls, engine_id, voice):
        players = BackendInfoBridge.getPlayers(engine_id)
        if not players:
            xbmcgui.Dialog().ok(T(32182), T(32183))
            return
        players.insert(0, ('', T(32184)))
        disp = []
        for p in players:
            disp.append(p[1])
        idx = xbmcgui.Dialog().select(T(32185), disp)
        if idx < 0:
            return
        player = players[idx][0]
        cls._logger.info(f'Player for {engine_id} set to: {player}')
        Settings.set_player(player, engine_id)

    @classmethod
    def selectSetting(cls, engine_id, setting, *args):
        settingsList = BackendInfoBridge.getSettingsList(engine_id, setting, *args)
        if not settingsList:
            xbmcgui.Dialog().ok(T(32182), T(32186))
            return
        displays = []
        for ID, display in settingsList:
            displays.append(display)
        # xbmcgui.Dialog().select((heading, list[, autoclose, preselect,
        # useDetails])
        auto_close = -1
        current_value = Settings.getSetting(setting, engine_id)
        current_index = -1
        if current_value is not None:
            current_index = displays.index(str(current_value))

        idx = xbmcgui.Dialog().select(T(32187), displays, auto_close, current_index)
        if idx < 0:
            return
        choice = displays[idx]
        cls._logger.info(f'Setting {setting} for {engine_id} set to: {choice}')
        Settings.setSetting(f'{setting}', choice, engine_id)

    @classmethod
    def selectVolumeSetting(cls, engine_id, setting, *args):
        settingsList = BackendInfoBridge.getSettingsList(engine_id, setting, *args)
        if not settingsList:
            xbmcgui.Dialog().ok(T(32182), T(32186))
            return

        # xbmcgui.Dialog().select((heading, list[, autoclose, preselect,
        # useDetails])
        auto_close = -1
        current_value = Settings.getSetting(setting, engine_id)
        current_index = None
        if current_value is not None:
            current_index = settingsList.index(str(current_value))
        idx = xbmcgui.Dialog().select(T(32187), settingsList, auto_close, current_index)
        if idx < 0:
            return
        choice = settingsList[idx]
        cls._logger.info(f'Setting {setting} for {engine_id} set to: {choice}')
        Settings.setSetting(setting, choice, engine_id)

    @classmethod
    def selectGenderSetting(cls, engine_id):
        auto_close = -1
        # yesno(heading, message, nolabel, yeslabel, customlabel, autoclose])
        choice = xbmcgui.Dialog().yesno(T(32211), T(32217), T(32212), T(32213),
                                        T(32211), auto_close)
        if choice:
            voice = 'female'
        else:
            voice = 'male'
        Settings.setSetting(SettingsProperties.GENDER, voice, engine_id)


ConfigUtils.init_class()
