# coding=utf-8

"""
Provides a Skeleton Topic Model that supports a Label control without
a topic. It is meant to help simplify the implementations.
"""
from common.phrases import PhraseList
from gui.base_model import BaseModel
from gui.base_tags import (BaseAttributeType as BAT, control_elements, Item)
from gui.base_topic_model import BaseTopicModel


class BaseFakeTopic(BaseTopicModel):
    """
        Provides a skeletal Topic implementation
    """
    item: Item = control_elements[BAT.TOPIC]

    def __init__(self, parent: BaseModel, topic_name: str) -> None:
        super().__init__(parent=parent, topic_name=topic_name, real_topic=False)
        self.is_real_topic: bool = False
        self.is_new_topic: bool = True

        # Type provides a means to voice what kind of control this is other than just
        # the Kodi standard controls, group, groupList, etc.

        self.type: str = self.parent.control_type

    @property
    def name(self) -> str:
        if super().name == '':
            super()._name = super().parent.tree_id
        return super().name

    def voice_info_label(self, phrases: PhraseList) -> bool:
        return False

    def voice_label_expr(self, phrases: PhraseList) -> bool:
        return False

    def voice_labeled_by(self, phrases: PhraseList) -> bool:
        return False

    def voice_labels(self, phrases: PhraseList,
                     control_id_expr: str | None = None) -> bool:
        """
        Convenience method that calls this topic's control to voice the labels.

        :param phrases: Append any voicings to phrases
        :param control_id_expr: IGNORED
        :return: True if at least one phrase was appended. False if no phrases
                added.
        """
        return False

    def __repr__(self) -> str:
        clz = type(self)

        return 'END NoLabelTopicModel'
