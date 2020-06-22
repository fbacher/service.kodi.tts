# -*- coding: utf-8 -*-
from .base import WindowReaderBase
import xbmc
from lib import util

class SettingsReader(WindowReaderBase):
    ID = 'settings'

    def getWindowExtraTexts(self):
        return None

    def getItemExtraTexts(self,controlID):
        text = xbmc.getInfoLabel('Container({0}).ListItem.Label2'.format(controlID))
        if not text: return None
        return [text.decode]

    def getControlText(self,controlID):
        if not controlID: return ('','')
        sub = ''
        text = self.getSettingControlText(controlID)
        if text.startswith('-'): sub = '{0}: '.format(util.T(32172))
        return ('{0}{1}'.format(sub,text),text)