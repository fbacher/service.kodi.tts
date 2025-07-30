# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *

from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from backends.settings.validators import (NumericValidator, Validator)
from common.base_services import BaseServices
from common.settings_low_level import SettingProp


class BasePlayerServiceSettings(BaseServiceSettings):
    service_id: str = Services.BUILT_IN_PLAYER_ID
    displayName: str = 'NoPlayer'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False

    initialized_settings: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz.initialized_settings:
            return

        if not clz.initialized_settings:
            clz.initialized_settings = True
        clz.init_settings()

        '''
        TRANSCODER?,
        GENDER_VISIBLE,
        GUI,
        SPEECH_DISPATCHER,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_DIGEST,
        #  SPEAK_VIA_KODI,
        TTSD_HOST,
        TTSD_PORT,
        VOICE_VISIBLE,
        VOLUME_VISIBLE
        '''

    @classmethod
    def init_settings(cls):
        pass

    @classmethod
    def register(cls, what: Type[ITTSBackendBase]) -> None:
        BaseServices.register(what)  # _settings(what)
