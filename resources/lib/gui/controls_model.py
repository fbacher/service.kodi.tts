# coding=utf-8

from typing import Callable, List

from common.logger import BasicLogger, DEBUG_EXTRA_VERBOSE
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.element_parser import (BaseElementParser,
                                ElementHandler)
from gui.parse_control import ParseControl
from gui.parse_controls import ParseControls

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ControlsModel(BaseModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlElement.CONTROLS]

    def __init__(self, parent, parsed_controls: ParseControls) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(parent.window_model, parsed_controls)
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
            model_handler:  Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(parser.item)
            #  clz._logger.debug(f'About to create model from {parser.item}')
            child_model: BaseModel = model_handler(self, parser)
            if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                clz._logger.debug_extra_verbose(f'adding child: {child_model}')
            self.children.append(child_model)

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
