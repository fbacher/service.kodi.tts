# -*- coding: utf-8 -*-
import xbmc

from . import windowparser
from .base import parseItemExtra, WindowReaderBase


class WeatherReader(WindowReaderBase):
    ID = 'weather'

    def getWindowTexts(self):
        return self.getWindowExtraTexts()

    def getWindowExtraTexts(self):
        texts = windowparser.getWindowParser().getWindowTexts()
        return texts or None

    def getItemExtraTexts(self,controlID):
        return parseItemExtra(controlID, self.getControlText(controlID)[0])

    def getControlText(self,controlID):
        if not controlID: return ('','')
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return ('','')
        return (text,text)
