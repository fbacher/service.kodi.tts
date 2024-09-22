# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from common import *

from backends.backend_info_bridge import BackendInfoBridge
from backends.i_backend_index import IEngineIndex
from backends.i_backend_info import IBackendInfo
from backends.i_tts_backend_base import ITTSBackendBase
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
from common.setting_constants import Backends
from common.settings_bridge import SettingsBridge
from common.system_queries import SystemQueries
from windowNavigation.choice import Choice


class BackendInfo(IBackendInfo):

    module_logger = BasicLogger.get_logger(__name__)
    backendsByPriority: List[ITTSBackendBase] = []
    backendsById: Dict[str, ITTSBackendBase] = {}
    backendByClassName: Dict[str, Type[ITTSBackendBase]] = {}
    backendIds: List[str] = []
    _logger: BasicLogger
    _initialized: bool = False

    @classmethod
    def init(cls):
        if not cls._initialized:
            cls._initialized = True
            cls._logger = BasicLogger.get_logger(__name__)
            cls._logger.debug(f'Setting BackendInfoBridge backend Ref')
            BackendInfoBridge.setBackendInfo(BackendInfo)

    @classmethod
    def removeBackendsByProvider(cls, to_remove):
        rem = []
        for b in cls.backendsByPriority:
            if b.backend_id in to_remove:
                rem.append(b)
        for r in rem:
            cls.backendsByPriority.remove(r)

    @classmethod
    def isValidBackend(cls, backend_id: str):
        if backend_id is None or len(backend_id) == 0:
            return False
        backends: List[ITTSBackendBase] = cls.getAvailableBackends()
        for backend in backends:
            if backend_id == backend.backend_id:
                return True
        return False

    @classmethod
    def getAvailableBackends(cls,
                             can_stream_wav: bool = False) -> List[ITTSBackendBase]:
        available: List[ITTSBackendBase] = []
        cls._logger.debug_v(
                f'backends.__init__.getAvailableBackends can_stream_wav: '
                f'{str(can_stream_wav)}')
        for engine_id in Backends.ALL_ENGINE_IDS:
            engine: ITTSBackendBase
            engine = BaseServices.getService(engine_id)
            try:
                if engine is None or not engine.is_available_and_usable():
                    continue
            except AttributeError:
                continue

            if cls._logger.isEnabledFor(DEBUG_V):
                cls._logger.debug_v(
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
    def getVoices(cls, backend_id):
        voices = None
        bClass: ITTSBackendBase = cls.getBackendByProvider(backend_id)
        if bClass:
            voices = bClass.voices()
        return voices

    @classmethod
    def getLanguages(cls, backend_id):
        languages = None
        bClass: Callable | ITTSBackendBase = cls.getBackendByProvider(backend_id)
        if bClass:
            with bClass as b:
                languages = b.languages()
        return languages

    @classmethod
    def getSettingsList(cls, backend_id, setting,
                        *args) -> List[Choice]:
        settings: List[Choice]
        settings = None
        bClass: Callable | ITTSBackendBase = cls.getBackendByProvider(backend_id)
        if bClass:
            cls._logger.debug(f'bClass: {type(bClass)}')
            settings = bClass.settingList(setting, *args)
        return settings

    @classmethod
    def getPlayers(cls, backend_id):
        players = None
        bClass = cls.getBackendByProvider(backend_id)
        if bClass and hasattr(bClass, 'players'):
            players = bClass.players()
        return players

    @classmethod
    def getBackend(cls, backend_id: str = SettingsBridge.BACKEND_DEFAULT) \
            -> ITTSBackendBase | None:
        if cls._logger.isEnabledFor(DEBUG_V):
            cls._logger.debug_v(f'getBackend backend_id: {backend_id}')

        backend_id = SettingsBridge.get_engine_id() or backend_id
        b = cls.getBackendByProvider(backend_id)
        if not b or not b._available():
            for b in cls.backendsByPriority:
                if b._available():
                    break
        return b

    @classmethod
    def getWavStreamBackend(cls, backend_id='auto') -> ITTSBackendBase | None:
        b: ITTSBackendBase = cls.getBackendByProvider(backend_id)
        if not b or not b._available() or not b.canStreamWav:
            for b in cls.backendsByPriority:
                if b._available() and b.canStreamWav:
                    return b
        return None

    @classmethod
    def getBackendByProvider(cls, provider_id: str = None) \
            -> Callable | Type[ITTSBackendBase] | None:
        cls._logger.debug(f'provider_id: {provider_id}')
        if provider_id == 'auto':
            return None
        for b in cls.backendsByPriority:
            cls._logger.debug(f'backend {b.backend_id}')
            cls._logger.debug(f'available: {b._available()}')
            if b.backend_id == provider_id and b._available():
                return b
        return None

    @classmethod
    def getBackendByClassName(cls, name) -> Callable | ITTSBackendBase | None:
        cls._logger.debug(f'getBackendByClassName name: {name}')
        if name == Constants.AUTO:
            return None
        instance: Type[ITTSBackendBase] = cls.backendByClassName.get(name, None)
        cls._logger.debug(f'instance: {instance}')
        if instance:
            cls._logger.debug(f'available: {instance._available}')
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
                backend_class_name: str = backend.backend_id
                cls.backendByClassName[backend_class_name] = backend
        return
