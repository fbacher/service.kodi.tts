# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.service_types import ServiceID, Services
from common import *

from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (NumericValidator, StringValidator,
                                          Validator)
from common.base_services import BaseServices
from common.setting_constants import Players


class BasePlayerSettings(BaseServiceSettings):
    service_id: ServiceID | None = None  # Overridden
    broken = False

    settings: Dict[str, Validator] = {}
    constraints: Dict[str, Constraints] = {}

    initialized_settings: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz.initialized_settings:
            return

        if not clz.initialized_settings:
            clz.initialized_settings = True

        allowed_engine_ids: List[str] = []

    @classmethod
    def init_settings(cls):

        valid_players: List[str] = [Players.SFX, Players.WINDOWS, Players.APLAY,
                                    Players.PAPLAY, Players.AFPLAY, Players.SOX,
                                    Players.MPLAYER, Players.MPG321, Players.MPG123,
                                    Players.BUILT_IN, Players.MPG321_OE_PI]
        player_validator: StringValidator
        player_validator = StringValidator(cls.service_id,
                                           allowed_values=valid_players,
                                           default=Players.MPV)

        SettingsMap.define_setting(cls.service_id,
                                   validator=player_validator)

    @classmethod
    def register(cls, what: Type[ITTSBackendBase]) -> None:
        BaseServices.register(what)
