# -*- coding: utf-8 -*-
from .base import WindowReaderBase, parseItemExtra
import xbmc
from . import windowparser

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