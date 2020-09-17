# -*- coding: utf-8 -*-
import xbmc
from . import base
from lib import util

class VideoLibraryWindowReader(base.DefaultWindowReader):
    ID = 'videolibrary'

    def getControlText(self,controlID):
        if self.slideoutHasFocus():
            return self.getSlideoutText(controlID)
        if not controlID: return ('','')
        text = xbmc.getInfoLabel('ListItem.Label')
        if not text: return base.DefaultWindowReader.getControlText(self,controlID)
        status = ''
        if xbmc.getCondVisibility('ListItem.IsResumable'):
            status = ': {0}'.format(util.T(32199))
        else:
            if xbmc.getInfoLabel('ListItem.Overlay') == 'OverlayWatched.png':
                status = ': {0}'.format(util.T(32198))
        return ('{0}{1}'.format(text,status),text)