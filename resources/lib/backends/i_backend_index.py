from common import *
from backends.i_tts_backend_base import ITTSBackendBase


class IBackendIndex:
    SAPITTSBackend = 'SAPITTSBackend'
    OSXSayTTSBackend = 'OSXSayTTSBackend'
    ESpeakTTSBackend = 'ESpeakTTSBackend'
    JAWSTTSBackend = 'JAWSTTSBackend'
    NVDATTSBackend = 'NVDATTSBackend'
    FliteTTSBackend = 'FliteTTSBackend'
    Pico2WaveTTSBackend = 'Pico2WaveTTSBackend'
    FestivalTTSBackend = 'FestivalTTSBackend'
    CepstralTTSBackend = 'CepstralTTSBackend'
    #            CepstralTTSOEBackend,
    SpeechDispatcherTTSBackend = 'SpeechDispatcherTTSBackend'
    #            VoiceOverBackend,
    SpeechServerBackend = 'SpeechServerBackend'
    ReciteTTSBackend = 'ReciteTTSBackend'
    GoogleTTSBackend = 'GoogleTTSBackend'
    ResponsiveVoiceTTSBackend = 'ResponsiveVoiceTTSBackend'
    #            SpeechUtilComTTSBackend,
    ESpeakCtypesTTSBackend = 'ESpeakCtypesTTSBackend'
    LogOnlyTTSBackend = 'LogOnlyTTSBackend'

    backendClassNames: List[str] = [SAPITTSBackend,
                                    OSXSayTTSBackend,
                                    ESpeakTTSBackend,
                                    JAWSTTSBackend,
                                    NVDATTSBackend,
                                    FliteTTSBackend,
                                    Pico2WaveTTSBackend,
                                    FestivalTTSBackend,
                                    CepstralTTSBackend,
                                    #            CepstralTTSOEBackend,
                                    SpeechDispatcherTTSBackend,
                                    #            VoiceOverBackend,
                                    SpeechServerBackend,
                                    ReciteTTSBackend,
                                    GoogleTTSBackend,
                                    ResponsiveVoiceTTSBackend,
                                    #            SpeechUtilComTTSBackend,
                                    ESpeakCtypesTTSBackend,
                                    LogOnlyTTSBackend
                                    ]

    @classmethod
    def setBackendByPriorities(cls, backendsByPriority: List[ITTSBackendBase],
                           backendsById: Dict[str, ITTSBackendBase]) -> None:
        pass
