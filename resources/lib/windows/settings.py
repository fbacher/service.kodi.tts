# -*- coding: utf-8 -*-
import xbmc

from common.messages import Messages
from .base import WindowReaderBase


class SettingsReader(WindowReaderBase):
    ID = 'settings'

    def getWindowExtraTexts(self):
        return None

    def getItemExtraTexts(self,controlID):
        text = xbmc.getInfoLabel('Container({0}).ListItem.Label2'.format(controlID))
        if not text: return None
        return [text]

    def getControlText(self,controlID):
        if not controlID: return ('','')
        sub = ''
        text = self.getSettingControlText(controlID)
        if text.startswith('-'): sub = '{0}: '.format(Messages.get_msg(Messages.SUB_SETTING))
        return ('{0}{1}'.format(sub,text),text)
