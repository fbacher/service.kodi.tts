# coding=utf-8

from typing import Callable, List

from common.logger import BasicLogger, DEBUG_VERBOSE
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.element_parser import (ElementHandler)
from gui.group_topic_model import GroupTopicModel
from gui.no_topic_models import NoGroupTopicModel
from gui.parse_group import ParseGroup

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class GroupModel(BaseLabelModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlElement.GROUP]

    def __init__(self, parent: BaseLabelModel, parsed_group: ParseGroup) -> None:
        clz = GroupModel
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        super().__init__(window_model=parent.window_model, parser=parsed_group)

        self.parent = parent
        self.alt_info_expr: str = parsed_group.alt_info_expr
        self.default_control_id = parsed_group.default_control_id
        self.default_control_always: bool = parsed_group.default_control_always
        self.description: str = parsed_group.description
        self.visible_expr = parsed_group.visible_expr
        self.best_alt_label: str = ''
        self.best_hint_text: str = ''
        self.best_info_expr: str = ''

        self.convert_children(parsed_group)

    @property
    def supports_heading_label(self) -> bool:
        """
        Indicates whether this control provides a label which explains what it
        is for. For example, a button's label almost certainly is to explain
        why you should press it. On the other hand a label control does not.
        A label control may be displaying a date or the result of an action.
        More information is needed for controls like labels in order to know
        what to do with them.

        :return:
        """
        return False

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return False

    @property
    def supports_label2(self) -> bool:
        #  ControlCapabilities.LABEL2
        return False

    def convert_children(self, parsed_group: ParseGroup) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_group: A ParseGroup instance that
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
        clz = GroupModel

        if parsed_group.topic is not None:
            self.topic = GroupTopicModel(self, parsed_group.topic)
        else:
            self.topic = NoGroupTopicModel(self)

        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'parsed_group: {parsed_group}')
        parsers: List[BaseParser] = parsed_group.get_children()

        for parser in parsers:
            parser: BaseParser
            model_handler: Callable[[BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(parser.item)
            child_model: BaseModel = model_handler(self, parser)
            self.children.append(child_model)

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
        clz = GroupModel

        label_expr_str: str = ''
        if self.label_expr != '':
            label_expr_str = f'\n  label_expr: {self.label_expr}'

        visible_expr_str: str = ''
        if self.visible_expr != '':
            visible_expr_str = f'\n  visible: {self.visible_expr}'

        default_control_id: str = ''
        if self.default_control_id >= 0:
            default_control_id = f'\n  default_control: {self.default_control_id}'

        default_control_id: str = ''
        if self.default_control_id >= 0:
            default_control_id = f'\n  default_control: {self.default_control_id}'
        default_control_always: str = ''
        if self.default_control_always:
            default_control_always = (f'\n  default_control_always: '
                                      f'{self.default_control_always}')
        description_str: str = ''
        if self.description != '':
            description_str = f'\n  description: {self.description}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nGroupModel type: {self.control_type} '
                       f'id: {self.control_id}'
                       f'{default_control_id}{default_control_always}'
                       f'{description_str}'
                       f'{visible_expr_str}'
                       f'{topic_str}'
                       f'\n  #children: {len(self.children)}'
                       )
        results.append(result)

        if include_children:
            for control in self.children:
                control: BaseModel
                result: str = control.to_string(include_children=include_children)
                results.append(result)

        results.append(f'END GroupModel\n')

        return '\n'.join(results)
