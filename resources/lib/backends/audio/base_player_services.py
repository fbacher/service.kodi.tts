# coding=utf-8
from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.i_validators import IValidator
from common.base_services import IServices


class BasePlayerServices(IServices):

    @classmethod
    def get_player(cls, service_or_id: str) -> IPlayer:
        service_id: str
        if isinstance(service_or_id, BasePlayerServices):
            service_id = service_or_id.service_ID
        else:
            service_id = service_or_id
        return PlayerIndex.get_player(service_id)
