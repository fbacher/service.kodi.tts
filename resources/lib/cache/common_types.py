# coding=utf-8


"""
CacheEntryInfo
    current_voice_path: Path to cache entry (or tempfile) for the audio file
       produced by the engine which produced it (generally the current engine).
    text_exists: bool indicating if the accompaning .txt file text_exists in the cache
    audio_suffixes: List of audio suffixes of files with the same name as the
    current_voice_path. Generally, there is only one entry with the same suffix as
    the current_voice_path. However, there can be, for example, a .mp3 and .wav
    version of the same audio. This is used for a few messages that are critical
    for startup before external players and engines are installed and configured.

"""
from collections import namedtuple

CacheEntryInfo = namedtuple('CacheEntryInfo',
                            'current_audio_path, '
                            'audio_exists, text_exists, audio_suffixes')
