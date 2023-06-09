from backends.audio.afplay_audio_player import AfplayPlayer
from backends.audio.builtin_audio_player import BuiltInAudioPlayer
from backends.audio.mpg123_audio_player import Mpg123AudioPlayer
from backends.audio.mpg321_audio_player import Mpg321AudioPlayer
from backends.audio.mpg321oep_audio_player import Mpg321OEPiAudioPlayer
from backends.audio.mplayer_audio_player import MPlayerAudioPlayer
from backends.audio.paplay_audio_player import PaplayAudioPlayer
from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
from backends.audio.sox_audio_player import SOXAudioPlayer
from backends.audio.windows_audio_player import WindowsAudioPlayer


class PlayerStartup:
    AfplayPlayer.register()
    BuiltInAudioPlayer.register()
    Mpg123AudioPlayer.register()
    Mpg321AudioPlayer.register()
    Mpg321OEPiAudioPlayer.register()
    MPlayerAudioPlayer.register()
    PlaySFXAudioPlayer.register()
    PaplayAudioPlayer.register()
    SOXAudioPlayer.register()
    WindowsAudioPlayer.register()
