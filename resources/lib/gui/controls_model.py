# coding=utf-8

from typing import Callable, List

from common.logger import BasicLogger, DEBUG_XV
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.element_parser import (ElementHandler)
from gui.no_topic_models import NoControlsTopicModel
from gui.parser.parse_control import ParseControl
from gui.parser.parse_controls import ParseControls
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class ControlsModel(BaseModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.CONTROLS]

    def __init__(self, parent, parsed_controls: ParseControls,
                 windialog_state: WinDialogState | None = None) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
        super().__init__(parent.window_model, parsed_controls,
                         windialog_state=windialog_state)
        self.parent: BaseModel = parent
        # self.topic: TopicModel = None
        # self.control_id: int = parsed_controls.control_id

        self.convert_children(parsed_controls.children)

    def convert_children(self, parsed_controls: List[ParseControl]) -> None:
        """
            Convert Parsed Controls, etc. to models.

        :param parsed_controls:
               needs to be convertd to a GroupModel
        :return:
        """
        '''
        description 	
        attrib: type 
        attrib: id 
        visible 	

        Tags available to focusable controls        
        Tags 	Definition
        onup 	
        ondown 
        onleft 
        onright 	
        onback 	
        oninfo 
        onfocus  
        onunfocus 	
        enable 	 
        '''
        clz = type(self)
        for parser in parsed_controls:
            parser: BaseParser
            model_handler:  Callable[[BaseModel, BaseParser, WinDialogState | None],
                                     BaseModel]
            model_handler = ElementHandler.get_model_handler(parser.item)
            #  clz._logger.debug(f'About to create model from {parser.item}')
            child_model: BaseModel = model_handler(self, parser, None)
            if clz._logger.isEnabledFor(DEBUG_XV):
                clz._logger.debug_xv(f'adding child: {child_model}')
            self.children.append(child_model)
            self.topic = NoControlsTopicModel(self)

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
        clz = type(self)
        results: List[str] = []
        result: str = f'\nControlsModel'
        results.append(result)

        results.append(f'Number of children: {len(self.children)}')
        if include_children:
            for control in self.children:
                control: BaseModel
                result: str = control.to_string(include_children=include_children)
                results.append(result)

        return '\n'.join(results)
