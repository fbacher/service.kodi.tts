import xbmc
from common import *
from backends.i_tts_backend_base import ITTSBackendBase
from backends.i_backend_index import IBackendIndex
from backends.backend_info import BackendInfo
from .base import LogOnlyTTSBackend
from .nvda import NVDATTSBackend
from .festival import FestivalTTSBackend
from .pico2wave import Pico2WaveTTSBackend
from .flite import FliteTTSBackend
from .osxsay import OSXSayTTSBackend
# from .sapi import SAPITTSBackend
from .espeak import ESpeakTTSBackend, ESpeakCtypesTTSBackend
from .speechdispatcher import SpeechDispatcherTTSBackend
from .jaws import JAWSTTSBackend
from .speech_server import SpeechServerBackend
# from .cepstral import CepstralTTSBackend  # , CepstralTTSOEBackend
# from .google import GoogleTTSBackend
from .responsive_voice import ResponsiveVoiceTTSBackend
# from speechutil import SpeechUtilComTTSBackend
from .recite import ReciteTTSBackend


# from voiceover import VoiceOverBackend #Can't test


class BackendIndex(IBackendIndex):
    # Instances of ITTSBackendBase
    backendsByPriority: List[ITTSBackendBase] = [# SAPITTSBackend(),
                                                       # OSXSayTTSBackend(),
                                                       ESpeakTTSBackend(),
                                                       # JAWSTTSBackend(),
                                                       # NVDATTSBackend(),
                                                       FliteTTSBackend(),
                                                       Pico2WaveTTSBackend(),
                                                       FestivalTTSBackend(),
                                                       # CepstralTTSBackend(),
                                                       #            CepstralTTSOEBackend(),
                                                       SpeechDispatcherTTSBackend(),
                                                       #            VoiceOverBackend(),
                                                       # SpeechServerBackend(),
                                                       # ReciteTTSBackend(),
                                                       # GoogleTTSBackend(),
                                                       ResponsiveVoiceTTSBackend(),
                                                       #   SpeechUtilComTTSBackend(),
                                                       # ESpeakCtypesTTSBackend(),
                                                       LogOnlyTTSBackend()
                                                       ]
    backendsById: Dict[str, ITTSBackendBase] = {}

    _initialized: bool = False

    @classmethod
    def init(cls) -> None:
        if not cls._initialized:
            cls.initialized = True

            xbmc.log(f'BackendInfo.init', xbmc.LOGINFO)
            if len(cls.backendsById) == 0:
                xbmc.log(f'Populating len backendsByPriority: {len(cls.backendsByPriority)}',
                         xbmc.LOGINFO)
                for backend in cls.backendsByPriority:
                    backend: ITTSBackendBase
                    backend_id: str = backend.get_backend_id()
                    cls.backendsById[backend_id] = backend
                    xbmc.log(f'backend-id: {backend_id}', xbmc.LOGINFO)

            BackendInfo.setBackendByPriorities(cls.backendsByPriority, cls.backendsById)


BackendIndex.init()
