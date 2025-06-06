# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from backends.settings.service_unavailable_exception import ServiceUnavailable
from common import *

from backends.backend_info_bridge import BackendInfoBridge
from backends.i_backend_index import IEngineIndex
from backends.i_backend_info import IBackendInfo
from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.service_types import (ServiceID, ServiceType)
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
from common.setting_constants import Backends
from common.settings_bridge import SettingsBridge
from common.system_queries import SystemQueries
from windowNavigation.choice import Choice

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class BackendInfo(IBackendInfo):

    backendsByPriority: List[ITTSBackendBase] = []
    backendsById: Dict[str, ITTSBackendBase] = {}
    backendByClassName: Dict[str, Type[ITTSBackendBase]] = {}
    backendIds: List[str] = []
    _initialized: bool = False

    @classmethod
    def init(cls):
        if not cls._initialized:
            cls._initialized = True
            MY_LOGGER.debug(f'Setting BackendInfoBridge backend Ref')
            BackendInfoBridge.setBackendInfo(BackendInfo)

    @classmethod
    def removeBackendsByProvider(cls, to_remove):
        rem = []
        for b in cls.backendsByPriority:
            if b.engine_id in to_remove:
                rem.append(b)
        for r in rem:
            cls.backendsByPriority.remove(r)

    @classmethod
    def isValidBackend(cls, engine_id: str):
        if engine_id is None or len(engine_id) == 0:
            return False
        backends: List[ITTSBackendBase] = cls.getAvailableBackends()
        for backend in backends:
            if engine_id == backend.engine_id:
                return True
        return False

    @classmethod
    def getAvailableBackends(cls,
                             can_stream_wav: bool = False) -> List[ITTSBackendBase]:
        available: List[ITTSBackendBase] = []
        MY_LOGGER.debug_v(
                f'backends.__init__.getAvailableBackends can_stream_wav: '
                f'{str(can_stream_wav)}')
        for engine_id in Backends.ALL_ENGINE_IDS:
            engine: ITTSBackendBase | None = None
            try:
                engine = BaseServices.get_service(ServiceID(ServiceType.ENGINE, engine_id))
                if engine is None or not engine.is_available_and_usable():
                    continue
            except ServiceUnavailable:
                MY_LOGGER.debug(f'Could not Load {engine}')
            except AttributeError:
                continue

            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(
                    f'Available engine: {engine.__class__.__name__}')
            available.append(engine)
        return available

    @classmethod
    def getBackendFallback(cls) -> ITTSBackendBase | None:
        if SystemQueries.isATV2():
            return cls.getBackendByClassName(IEngineIndex.FliteTTSBackend)
        elif SystemQueries.isWindows():
            return cls.getBackendByClassName(IEngineIndex.SAPITTSBackend)
        elif SystemQueries.isOSX():
            return cls.getBackendByClassName(IEngineIndex.OSXSayTTSBackend)
        elif SystemQueries.isOpenElec():
            return cls.getBackendByClassName(IEngineIndex.ESpeakTTSBackend)
        for b in cls.backendsByPriority:
            if b._available():
                return b
        return None

    #  TODO: getBackendByProvider appears broke, never initialized
    # TODO: Looks like a HACK. Only applies to several engines/backends and there
    # is no definition in TTSBackend for voices() so it could blow up
    @classmethod
    def getVoices(cls, engine_id):
        voices = None
        bClass: Callable | ITTSBackendBase = cls.getBackendByProvider(engine_id)
        if bClass:
            with bClass as b:
                voices = b.voices()
        return voices

    @classmethod
    def getLanguages(cls, engine_id):
        languages = None
        bClass: Callable | ITTSBackendBase = cls.getBackendByProvider(engine_id)
        if bClass:
            with bClass as b:
                languages = b.languages()
        return languages

    @classmethod
    def getSettingsList(cls, engine_id, setting,
                        *args) -> List[Choice]:
        settings: List[Choice] | None
        settings = None
        bClass: Callable | ITTSBackendBase = cls.getBackendByProvider(engine_id)
        if bClass:
            MY_LOGGER.debug(f'bClass: {type(bClass)}')
            settings = bClass.settingList(setting, *args)
        return settings

    @classmethod
    def getPlayers(cls, engine_id):
        players = None
        bClass = cls.getBackendByProvider(engine_id)
        if bClass and hasattr(bClass, 'players'):
            players = bClass.players()
        return players

    @classmethod
    def getBackend(cls, engine_id: str = SettingsBridge.BACKEND_DEFAULT) \
            -> ITTSBackendBase | None:
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'getBackend engine_id: {engine_id}')

        engine_id = SettingsBridge.get_engine_id() or engine_id
        b = cls.getBackendByProvider(engine_id)
        if not b or not b._available():
            for b in cls.backendsByPriority:
                if b._available():
                    break
        return b

    @classmethod
    def getWavStreamBackend(cls, engine_id='auto') -> ITTSBackendBase | None:
        b: Callable | ITTSBackendBase = cls.getBackendByProvider(engine_id)
        if not b or not b._available() or not b.canStreamWav:
            for b in cls.backendsByPriority:
                if b._available() and b.canStreamWav:
                    return b
        return None

    @classmethod
    def getBackendByProvider(cls, provider_id: str = None) \
            -> Callable | Type[ITTSBackendBase] | None:
        MY_LOGGER.debug(f'provider_id: {provider_id}')
        if provider_id == 'auto':
            return None
        for b in cls.backendsByPriority:
            MY_LOGGER.debug(f'backend {b.engine_id}')
            MY_LOGGER.debug(f'available: {b._available()}')
            if b.engine_id == provider_id and b._available():
                return b
        return None

    @classmethod
    def getBackendByClassName(cls, name) -> Callable | ITTSBackendBase | None:
        MY_LOGGER.debug(f'getBackendByClassName name: {name}')
        #  if name == Constants.AUTO:
        #      return None
        instance: Type[ITTSBackendBase] = cls.backendByClassName.get(name, None)
        MY_LOGGER.debug(f'instance: {instance}')
        if instance:
            MY_LOGGER.debug(f'available: {instance._available}')
        if instance and instance._available():
            return instance
        return None

    @classmethod
    def getBackendIds(cls) -> List[str]:
        return cls.backendIds

    @classmethod
    def setBackendByPriorities(cls, backendsByPriority: List[ITTSBackendBase],
                               backendsById: Dict[str, ITTSBackendBase]) -> None:
        if len(cls.backendsByPriority) == 0:
            cls.backendsByPriority = backendsByPriority
            cls.backendsById = backendsById
            for backendId in backendsById.keys():
                cls.backendIds.append(backendId)

            for backend in backendsByPriority:
                backend: Type[ITTSBackendBase]
                backend_class_name: str = backend.engine_id
                cls.backendByClassName[backend_class_name] = backend
        return
