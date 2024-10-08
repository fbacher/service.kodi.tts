from __future__ import annotations  # For union operator |

import os
import platform
import subprocess
import tempfile

import requests

from common import *

if platform.system() == "Windows":
    try:
        import playsound
    except ImportError:
        print("run pip install playsound")
        raise
else:
    playsound = None


class ResponsiveVoice:
    API_URL = "http://responsivevoice.org/responsivevoice/getvoice.php"

    # Genders
    FEMALE = "female"
    MALE = "male"
    UNKNOWN_GENDER = ""

    # Languages
    ENGLISH_GB = "en-GB"
    ENGLISH_AU = "en-AU"
    ENGLISH_US = "en-US"
    ENGLISH_ZA = "en-ZA"
    ENGLISH_IE = "en-IE"
    HEBREW = "he-IL"
    THAI = "th-TH"
    PORTUGUESE_BR = "pt-BR"
    PORTUGUESE_PT = "pt-PT"
    SLOVAK = "sk-SK"
    FRENCH_CA = "fr-CA"
    ROMANIAN = "ro-RO"
    NORWEGIAN = "no-NO"
    FINNISH = "fi-FI"
    POLISH = "pl-PL"
    GERMAN = "de-DE"
    DUTCH = "nl-NL"
    INDONESIAN = "id-ID"
    TURKISH = "tr-TR"
    ITALIAN = "it-IT"
    FRENCH = "fr-FR"
    RUSSIAN = "ru-RU"
    SPANISH_MX = "es-MX"
    SPANISH_ES = "es-ES"
    CHINESE_HK = "zh-HK"
    CHINESE_TW = "zh-TW"
    CHINESE_CN = "zh-CN"
    SWEDISH = "sv-SE"
    HUNGARIAN = "hu-HU"
    DUTCH_BE = "nl-BE"
    ARABIC_SA = "ar-SA"
    KOREAN = "ko-KR"
    CZECH = "cs-CZ"
    DANISH = "da-DK"
    HINDI = "hi-IN"
    GREEK = "el-GR"
    JAPANESE = "ja-JP"

    def __init__(self, lang=None, gender='',
                 pitch=0.5, rate=0.5, vol=1,
                 voice_name="", service="", key=None):
        self.pitch = pitch
        self.rate = rate
        self.vol = vol
        self.lang = lang or ResponsiveVoice.ENGLISH_US
        self.gender = gender or ResponsiveVoice.UNKNOWN_GENDER
        self.service = service
        self.voice_name = voice_name
        # key extracted from wordpress plugin - FQ9r4hgY
        # alternate key from Bundler - HY7lTyiS
        self.key = key or "FQ9r4hgY"

    @staticmethod
    def play_mp3(mp3_file, play_cmd="mpg123 -q %1", blocking=False):
        # TODO support windows shell commands

        if playsound is not None:
            playsound.playsound(mp3_file, blocking)
        else:
            play_mp3_cmd = str(play_cmd).split(" ")
            for index, cmd in enumerate(play_mp3_cmd):
                if cmd == "%1":
                    play_mp3_cmd[index] = mp3_file
            if blocking:
                return subprocess.call(play_mp3_cmd)
            else:
                '''
                if xbmc.getCondVisibility('System.Platform.Windows'):
                    # Prevent console for ffmpeg from opening

                    self.process = subprocess.Popen(
                        self.args, stdin=None, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=False, universal_newlines=True,
                        env=env,
                        close_fds=True, creationflags=subprocess.DETACHED_PROCESS)
                else:
                    self.process = subprocess.Popen(
                        self.args, stdin=None, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=False, universal_newlines=True,
                        env=env,
                        close_fds=True)
                return subprocess.Popen(play_mp3_cmd)
                '''

    def get_mp3(self, sentence, mp3_file=None, pitch=None, rate=None,
                vol=None, gender=None):
        mp3_file = mp3_file or os.path.join(tempfile.gettempdir(),
                                            str(hash(sentence)))
        if not mp3_file.endswith(".mp3"):
            mp3_file += ".mp3"

        params = {
            "key"   : self.key,
            "t"     : sentence,
            "tl"    : self.lang,
            "pitch" : pitch or self.pitch,
            "rate"  : rate or self.rate,
            "vol"   : vol or self.vol,
            "sv"    : self.service,
            "vn"    : self.voice_name,
            "gender": gender or self.gender
        }

        r = None
        try:
            r = requests.get(self.API_URL, params=params, timeout=35.0)

            if os.path.isfile(mp3_file):
                os.unlink(mp3_file)

            with open(mp3_file, "wb") as f:
                f.write(r.content)
        except Exception as e:
            a = e

        return mp3_file

    def say(self, sentence, mp3_file=None, pitch=None, rate=None, vol=None,
            gender=None,
            play_cmd="mpg123 -q %1", blocking=True):
        filename = self.get_mp3(sentence, mp3_file, pitch=pitch,
                                rate=rate, vol=vol, gender=gender)
        self.play_mp3(filename, play_cmd, blocking)


def get_voices(lang=None, normalize=False):
    import responsive_voice.voices
    voices = {}

    for k in responsive_voice.voices.__dict__:
        if not k.startswith("_") and k != "ResponsiveVoice":
            voice = responsive_voice.voices.__dict__[k]
            if lang:
                if voice().lang != lang:
                    continue
            if normalize:
                k = k.lower()
            voices[k] = voice
    return voices


def get_voice(voice_name, substring=True, lang=None):
    voices = get_voices(normalize=True, lang=lang)
    voice_name = voice_name.lower().replace(" ", "")
    voice = voices.get(voice_name)
    if not voice:
        # substring search
        if substring:
            for v in sorted(list(voices.keys()), key=len):
                if voice_name in v:
                    return voices[v]
    return voice
