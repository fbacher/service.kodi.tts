# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import BasicLogger
from common.phrases import Phrase, PhraseList

from . import base, DefaultWindowReader

module_logger = BasicLogger.get_logger(__name__)


class VideoInfoDialogReader(base.DefaultWindowReader):
    ID = 'videoinfodialog'

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None) -> None:
        cls = type(self)
        super().__init__(win_id, service)
        cls._logger = module_logger
        self.listMap: Dict[int, str] = None

    def init(self):
        self.listMap = {
                        20376: xbmc.getInfoLabel('ListItem.OriginalTitle'),
                        20339: xbmc.getInfoLabel('ListItem.Director'),
                        20417: xbmc.getInfoLabel('ListItem.Writer'),
                        572  : xbmc.getInfoLabel('ListItem.Studio'),
                        515  : xbmc.getInfoLabel('ListItem.Genre'),
                        562  : xbmc.getInfoLabel('ListItem.Year'),
                        2050 : '{0} {1}'.format(xbmc.getInfoLabel('ListItem.Duration'),
                                                xbmc.getLocalizedString(12391)),
                        563  : xbmc.getInfoLabel('ListItem.RatingAndVotes'),
                        # Works the same as ListItem.Rating when no votes, at least as
                        # far as speech goes
                        202  : xbmc.getInfoLabel('ListItem.TagLine'),
                        203  : xbmc.getInfoLabel('ListItem.PlotOutline'),
                        20074: xbmc.getInfoLabel('ListItem.mpaa'),
                        15311: xbmc.getInfoLabel('ListItem.FilenameAndPath'),
                        20364: xbmc.getInfoLabel('ListItem.TVShowTitle'),
                        20373: xbmc.getInfoLabel('ListItem.Season'),
                        20359: xbmc.getInfoLabel('ListItem.Episode'),
                        31322: xbmc.getInfoLabel('ListItem.Premiered'),
                        20360: '{0} ({1} - {2})'.format(
                            xbmc.getInfoLabel('ListItem.episode'), xbmc.getInfoLabel(
                                '$INFO[ListItem.Property(WatchedEpisodes),, $LOCALIZE['
                                '16102]]'),
                            xbmc.getInfoLabel(
                                '$INFO[ListItem.Property(UnWatchedEpisodes), , '
                                '$LOCALIZE[16101]]')),
                        557  : xbmc.getInfoLabel('ListItem.Artist'),
                        558  : xbmc.getInfoLabel('ListItem.Album'),
                        }

    def getHeading(self, phrases: PhraseList) -> bool:
        text = xbmc.getInfoLabel('ListItem.Title')
        if text != '':
            phrases.add_text(texts=text)
            return True
        return False

    def getControlText(self, control_id: int, phrases: PhraseList) -> bool:
        clz = type(self)
        if not control_id:
            return False
        text: str = ''
        if control_id == 49:
            text = xbmc.getInfoLabel('System.CurrentControl'.format(control_id)).strip(
                ': ')
            for k in self.listMap.keys():
                if text == xbmc.getLocalizedString(k).strip(': '):
                    text = '{0}: {1}'.format(text, self.listMap[k])
                    break
        elif control_id == 50:
            text = '{0}: {1}'.format(xbmc.getInfoLabel('Container(50).ListItem.Label'),
                                     xbmc.getInfoLabel('Container(50).ListItem.Label2'))
        elif control_id == 61:
            text = '{0}: {1}'.format(xbmc.getLocalizedString(207),
                                     xbmc.getInfoLabel('ListItem.Plot'))
        elif control_id == 138:
            text = xbmc.getInfoLabel('ListItem.Plot')
        else:
            text = xbmc.getInfoLabel(f'Control.GetLabel({control_id})')

        if not text:
            text = xbmc.getInfoLabel('System.CurrentControl')
        if not text:
            return False
        clz._logger.debug(f'text: {text} control_id: {control_id}')
        phrases.add_text(texts=text)
        return True

    def getControlPostfix(self, control_id: int | None, phrases: PhraseList) -> bool:
        cls = type(self)
        success: bool = False
        if self.service.current_control_id == 50:
            phrases.add_text(texts='Cast:')
            DefaultWindowReader.getControlPostfix(self, self.service.current_control_id,
                                                  phrases)
            cls._logger.debug(f'TODO: Suspicious code. '
                              f'control_id: {self.service.current_control_id}\n{phrases}')
            return True
        return False   # TODO: this looks wrong
