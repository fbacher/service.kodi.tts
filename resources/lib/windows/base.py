# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc
import xbmcgui

from common import *

from common.constants import Constants
from common.logger import BasicLogger
from common.messages import Messages
from . import guitables, skintables, windowparser

CURRENT_SKIN = skintables.CURRENT_SKIN

module_logger = BasicLogger.get_module_logger(module_path=__file__)


def parseItemExtra(controlID, current=None):
    texts = windowparser.getWindowParser().getListItemTexts(controlID)
    if current and texts:
        while current in texts:
            texts.pop(texts.index(current))
    return texts


class WindowHandlerBase:
    ID = None

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None):
        self.service: ForwardRef('TTSService') = service
        self.winID = win_id
        self._reset(win_id)

    def _reset(self, win_id):
        self.winID = win_id
        self.init()

    def window(self):
        return xbmcgui.Window(self.winID)

    def visible(self):
        return xbmc.getCondVisibility(f'Window.IsVisible({self.winID})')

    def init(self): pass

    def getMonitoredText(self, isSpeaking=False): return None

    def close(self): pass


class WindowReaderBase(WindowHandlerBase):
    _slideoutGroupID = 9000
    _logger: BasicLogger = None

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None) -> None:
        cls = type(self)
        super().__init__(win_id, service)
        cls._logger = module_logger.getChild(cls.__class__.__name__)

    def getName(self):
        return guitables.getWindowName(self.winID)

    def getHeading(self):
        return None

    def getWindowTexts(self):
        return None

    def getControlDescription(self, controlID):
        return None

    def getControlText(self, controlID):
        text = xbmc.getInfoLabel('System.CurrentControl')
        return (text, text)

    def getControlPostfix(self, controlID, ):
        cls = type(self)
        if not self.service.speakListCount:
            return ''
        numItems = xbmc.getInfoLabel(f'Container({self.service.controlID}).NumItems')
        if numItems:
            result = '... {0} {1}'.format(numItems, numItems != '1' and Messages.get_msg(
                    Messages.ITEMS) or Messages.get_msg(Messages.ITEM))
            cls._logger.debug(f'result: {result}')
            return result
        return ''

    def getSecondaryText(self):
        return None

    def getItemExtraTexts(self, controlID):
        return None

    def getWindowExtraTexts(self):
        texts = guitables.getExtraTexts(self.winID)
        if not texts:
            texts = windowparser.getWindowParser().getWindowTexts()
        return texts or None

    def slideoutHasFocus(self):
        return xbmc.getCondVisibility(f'ControlGroup({self._slideoutGroupID})'
                                      f'.HasFocus({self._slideoutGroupID})')

    def getSettingControlText(self, controlID):
        cls = type(self)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if text.endswith(')'):  # Skip this most of the time
            cls._logger.debug(f'elipsis substitution orig text: {text} ')
            text = text.replace('( )', '{0} {1}'.format(Constants.PAUSE_INSERT,
                                                        Messages.get_msg(
                                                                Messages.NO)).replace(
                '(*)',
                '{0} '
                '{1}'.format(
                        Constants.PAUSE_INSERT,
                        Messages.get_msg(
                                Messages.YES))))  # For boolean settings
        return text

    def getSlideoutText(self, controlID):
        text = self.getSettingControlText(controlID)
        if not text:
            return ('', '')
        return (text, text)


class DefaultWindowReader(WindowReaderBase):
    ID = 'default'

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None) -> None:
        super().__init__(win_id, service)
        pass

    def getHeading(self):
        return xbmc.getInfoLabel('Control.GetLabel(1)') or ''

    def getWindowTexts(self):
        return guitables.getWindowTexts(self.winID)

    def getControlDescription(self, controlID):
        return skintables.getControlText(self.winID, controlID) or ''

    def getControlText(self, controlID):
        if self.slideoutHasFocus():
            return self.getSlideoutText(controlID)

        if not controlID:
            return ('', '')
        text = xbmc.getInfoLabel('ListItem.Title')
        if not text:
            text = xbmc.getInfoLabel('Container({0}).ListItem.Label'.format(controlID))
        if not text:
            text = xbmc.getInfoLabel('Control.GetLabel({0})'.format(controlID))
        if not text:
            text = xbmc.getInfoLabel('System.CurrentControl')
        if not text:
            return ('', '')
        compare = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel(
                'ListItem.EndTime')
        return (text, compare)

    def getSecondaryText(self):
        return guitables.getListItemProperty(self.winID)

    def getItemExtraTexts(self, controlID):
        text = guitables.getItemExtraTexts(self.winID)
        if not text:
            text = xbmc.getInfoLabel('ListItem.Plot')
        if not text:
            text = xbmc.getInfoLabel('Container.ShowPlot')
        if not text:
            text = xbmc.getInfoLabel('ListItem.Property(Artist_Description)')
        if not text:
            text = xbmc.getInfoLabel('ListItem.Property(Album_Description)')
        if not text:
            text = xbmc.getInfoLabel('ListItem.Property(Addon.Description)')
        if not text:
            text = guitables.getSongInfo()
        if not text:
            text = parseItemExtra(controlID, self.getControlText(controlID)[0])
        if not text:
            return None
        if not isinstance(text, (list, tuple)):
            text = [text]
        return text


class NullReader(WindowReaderBase):
    ID = 'null'

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None) -> None:
        super().__init__(win_id, service)
        pass

    def getName(self): return None

    def getControlText(self, controlID): return ('', '')

    def getWindowExtraTexts(self): return None


class KeymapKeyInputReader(NullReader):
    ID = 'keymapkeyinput'

    def getWindowTexts(self): return [Messages.get_msg(Messages.PRESS_THE_KEY_TO_ASSIGN)]
