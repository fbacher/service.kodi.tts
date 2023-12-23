# -*- coding: utf-8 -*-
import xbmc

from . import guitables
from .base import WindowReaderBase


class YesNoDialogReader(WindowReaderBase):
    ID = 'yesnodialog'

    def getControlText(self, controlID):
        text = xbmc.getInfoLabel('System.CurrentControl')
        return (text, text)

    def getHeading(self):
        heading = guitables.convertTexts(10100, ('1',))
        if heading:
            return heading[0]

    def getWindowTexts(self):
        return self.getWindowExtraTexts()

    def getWindowExtraTexts(self):
        return guitables.convertTexts(10100, ('2', '3', '4', '9'))
