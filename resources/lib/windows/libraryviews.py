# -*- coding: utf-8 -*-
import xbmc

from common.messages import Messages
from . import base


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
            status = ': {0}'.format(Messages.get_msg(Messages.RESUMABLE))
        else:
            if xbmc.getInfoLabel('ListItem.Overlay') == 'OverlayWatched.png':
                status = ': {0}'.format(Messages.get_msg(Messages.WATCHED))
        return ('{0}{1}'.format(text,status),text)
