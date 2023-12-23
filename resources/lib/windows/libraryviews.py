# -*- coding: utf-8 -*-
import xbmc

from common.messages import Messages
from . import base


class VideoLibraryWindowReader(base.DefaultWindowReader):
    ID = 'videolibrary'

    def getControlText(self, controlID):
        cls = type(self)
        if self.slideoutHasFocus():
            cls._logger.debug(f'slideoutHasFocus controlID: {controlID}'
                              f' slideoutText: {self.getSlideoutText(controlID)}')
            return self.getSlideoutText(controlID)
        cls._logger.debug(f'controlID: {controlID}')
        if not controlID:
            return ('', '')
        text = xbmc.getInfoLabel('ListItem.Label')
        if not text:
            text = base.DefaultWindowReader.getControlText(self, controlID)
            cls._logger.debug(f'ControlText: {text}')
            return text
        status = ''
        if xbmc.getCondVisibility('ListItem.IsResumable'):
            status = ': {0}'.format(Messages.get_msg(Messages.RESUMABLE))
            cls._logger.debug(f'resumable: {status}')
        else:
            if xbmc.getInfoLabel('ListItem.Overlay') == 'OverlayWatched.png':
                status = ': {0}'.format(Messages.get_msg(Messages.WATCHED))
        cls._logger.debug('text: {text} status: {status}')
        return ('{0}{1}'.format(text, status), text)
