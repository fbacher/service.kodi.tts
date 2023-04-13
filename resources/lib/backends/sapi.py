# -*- coding: utf-8 -*-
import os, sys, wave, array, io

try:
    import importlib

    importHelper = importlib.import_module
except ImportError:
    importHelper = __import__
    importlib = None

from xml.sax import saxutils

from common.constants import Constants
from common.setting_constants import Languages, Players, Genders, Misc
from common.logger import LazyLogger
from common.messages import Messages
from common.settings import Settings
from common.system_queries import SystemQueries
from common import utils
from backends.base import SimpleTTSBackendBase

module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


def lookupGenericComError(com_error):
    try:
        errno = '0x%08X' % (com_error.hresult & 0xffffffff)
        with open(os.path.join(Constants.BACKENDS_DIRECTORY, 'comerrors.txt'), 'r') as f:
            lines = f.read().splitlines()
        for l1, l2, l3 in zip(lines[0::3], lines[1::3], lines[2::3]):
            if errno in l2:
                return l1, l3
    except:
        pass
    return None


class SAPI:
    DEFAULT = 0
    ASYNC = 1
    PURGE_BEFORE_SPEAK = 2
    IS_FILENAME = 4
    IS_XML = 8
    IS_NOT_XML = 16
    PERSIST_XML = 32
    SPEAK_PUNC = 64
    PARSE_SAPI = 128

    speedConstraints = (-10, 0, 10, True)
    pitchConstraints = (-10, 0, 10, True)
    volumeConstraints = (0, 100, 100, True)

    settings = {
        'pitch': 0,
        'speed': 0,
        'voice': None,
        'volume': 0
    }
    _logger: LazyLogger = None

    @classmethod
    def class_init(cls):
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    def __init__(self, *args, **kwargs):
        cls = type(self)
        cls._logger.enter()

        self.SpVoice = None
        self.comtypesClient = None
        self.valid = False
        self._voiceName = None
        self.streamFlags = None
        self.flags = None
        self.interrupt = False
        try:
            self.reset()
        except:
            self._logger.exception('SAPI: Initialization failed: retrying...')
            utils.sleep(1000)  # May not be necessary, but here it is
            try:
                self.reset()
            except:
                self._logger.exception('SAPI: Initialization failed: Giving up.')
                return
        self.valid = True
        self.COMError = importHelper('_ctypes').COMError
        self.setStreamFlags()
        cls._logger.exit()

    def importComtypes(self):
        # Remove all (hopefully) references to comtypes import...
        cls = type(self)
        cls._logger.enter()
        del self.comtypesClient
        self.comtypesClient = None
        for m in list(sys.modules.keys()):
            if m.startswith('comtypes'):
                del sys.modules[m]
        import gc
        gc.collect()
        # and then import
        self.comtypesClient = importHelper('comtypes.client')
        cls._logger.exit()

    def reset(self):
        cls = type(self)
        cls._logger.enter()
        del self.SpVoice
        self.SpVoice = None
        self.cleanComtypes()
        self.importComtypes()
        self.resetSpVoice()
        cls._logger.exit()

    def resetSpVoice(self):
        cls = type(self)
        cls._logger.enter()
        self.SpVoice = self.comtypesClient.CreateObject("SAPI.SpVoice")
        voice = self._getVoice()
        if voice:
            self.SpVoice.Voice = voice
        cls._logger.exit()

    def setStreamFlags(self):
        cls = type(self)
        cls._logger.enter()
        self.flags = self.PARSE_SAPI | self.IS_XML | self.ASYNC
        self.streamFlags = self.PARSE_SAPI | self.IS_XML | self.ASYNC
        try:
            self.SpVoice.Speak('', self.flags)
        except self.COMError as e:
            if cls._logger.isEnabledFor(LazyLogger.DEBUG):
                self.logSAPIError(e)
                cls._logger.debug('SAPI: XP Detected - changing flags')
            self.flags = self.ASYNC
            self.streamFlags = self.ASYNC
        finally:
            cls._logger.exit()

    def cleanComtypes(self):  # TODO: Make this SAPI specific?
        cls = type(self)
        cls._logger.enter()
        try:
            gen = os.path.join(Constants.BACKENDS_DIRECTORY, 'comtypes', 'gen')
            import stat, shutil
            os.chmod(gen, stat.S_IWRITE)
            shutil.rmtree(gen, ignore_errors=True)
            if not os.path.exists(gen):
                os.makedirs(gen)
        except:
            cls._logger.exception('SAPI: Failed to empty comtypes gen dir')
        finally:
            cls._logger.exit()

    def logSAPIError(self, com_error, extra=''):
        cls = type(self)
        cls._logger.enter()
        try:
            errno = str(com_error.hresult)
            with open(os.path.join(Constants.BACKENDS_DIRECTORY,
                                   'sapi_comerrors.txt'), 'r') as f:
                lines = f.read().splitlines()
            for l1, l2 in zip(lines[0::2], lines[1::2]):
                bits = l1.split()
                if errno in bits:
                    cls._logger.debug(
                        'SAPI specific COM error ({0})[{1}]: {2}'.format(errno, bits[0],
                                                                         l2 or '?'))
                    break
            else:
                error = lookupGenericComError(com_error)
                if error:
                    cls._logger.debug(
                        'SAPI generic COM error ({0})[{1}]: {2}'.format(errno, error[0],
                                                                        error[1] or '?'))
                else:
                    self._logger.debug(
                        'Failed to lookup SAPI/COM error: {0}'.format(com_error))
        except:
            cls._logger.exception('Error looking up SAPI error: {0}'.format(com_error))
        cls._logger.debug(
            'Line: {1} In: {0}{2}'.format(sys.exc_info()[2].tb_frame.f_code.co_name,
                                          sys.exc_info()[2].tb_lineno,
                                          extra and ' ({0})'.format(extra) or ''))
        cls._logger.exit()

    def _getVoice(self, voice_name=None):
        cls = type(self)
        cls._logger.enter()
        voice_name = voice_name or self._voiceName
        if voice_name:
            v = self.SpVoice.getVoices() or []
            for i in range(len(v)):
                voice = v[i]
                if voice_name == voice.GetDescription():
                    return voice
        cls._logger.exit()
        return None

    def checkSAPI(func):
        def checker(self, *args, **kwargs):
            cls = type(self)
            cls._logger.enter()
            if not self.valid:
                cls._logger.debug('SAPI: Broken - ignoring {0}'.format(func.__name__))
                return None
            try:
                return func(self, *args, **kwargs)
            except self.COMError as e:
                self.logSAPIError(e, func.__name__)
            except:
                cls._logger.exception('SAPI: {0} error'.format(func.__name__))
            self.valid = False
            cls._logger.debug('SAPI: Resetting...')
            utils.sleep(1000)
            try:
                self.reset()
                self.valid = True
                cls._logger.debug('SAPI: Resetting succeeded.')
                return func(self, *args, **kwargs)
            except self.COMError as e:
                self.valid = False
                self.logSAPIError(e, func.__name__)
            except:
                self.valid = False
                cls._logger.error('SAPI: {0} error'.format(func.__name__))
            finally:
                cls._logger.exit()

        return checker

    # Wrapped SAPI methods
    @checkSAPI
    def SpVoice_Speak(self, ssml, flags):
        cls = type(self)
        cls._logger.enter()
        return self.SpVoice.Speak(ssml, flags)

    @checkSAPI
    def SpVoice_GetVoices(self):
        cls = type(self)
        cls._logger.enter()
        return self.SpVoice.getVoices()

    @checkSAPI
    def stopSpeech(self):
        cls = type(self)
        cls._logger.enter()
        self.SpVoice.Speak('', self.ASYNC | self.PURGE_BEFORE_SPEAK)

    @checkSAPI
    def SpFileStream(self):
        cls = type(self)
        cls._logger.enter()
        return self.comtypesClient.CreateObject("SAPI.SpFileStream")

    @checkSAPI
    def SpAudioFormat(self):
        cls = type(self)
        cls._logger.enter()
        return self.comtypesClient.CreateObject("SAPI.SpAudioFormat")

    @checkSAPI
    def SpMemoryStream(self):
        cls = type(self)
        cls._logger.enter()
        return self.comtypesClient.CreateObject("SAPI.SpMemoryStream")

    def validCheck(func):
        def checker(self, *args, **kwargs):
            cls = type(self)
            cls._logger.enter()
            if not self.valid:
                cls._logger.debug('SAPI: Broken - ignoring {0}'.format(func.__name__))
                return
            return func(self, *args, **kwargs)

        return checker

    @validCheck
    def set_SpVoice_Voice(self, voice_name):
        cls = type(self)
        cls._logger.enter()
        self._voiceName = voice_name
        voice = self._getVoice(voice_name)
        self.SpVoice.Voice = voice
        cls._logger.exit()

    @validCheck
    def set_SpVoice_AudioOutputStream(self, stream):
        cls = type(self)
        cls._logger.enter()
        self.SpVoice.AudioOutputStream = stream
        cls._logger.exit()


SAPI.class_init()


class SAPITTSBackend(SimpleTTSBackendBase):
    provider = 'SAPI'
    displayName = 'SAPI (Windows Internal)'
    settings = {'speak_via_xbmc': True,
                'voice': '',
                'speed': 0,
                'pitch': 0,
                'volume': 100
                }
    canStreamWav = True
    speedConstraints = (-10, 0, 10, True)
    pitchConstraints = (-10, 0, 10, True)
    volumeConstraints = (0, 100, 100, True)
    volumeExternalEndpoints = (0, 100)
    volumeStep = 5
    volumeSuffix = '%'
    baseSSML = '''<?xml version="1.0"?>
<speak version="1.0"
         xmlns="http://www.w3.org/2001/10/synthesis"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://www.w3.org/2001/10/synthesis
                   http://www.w3.org/TR/speech-synthesis/synthesis.xsd"
         xml:lang="en-US">
  <volume level="{volume}" />
  <pitch absmiddle="{pitch}" />
  <rate absspeed="{speed}" />
  <p>{text}</p>
</speak>'''
    _logger = None

    @classmethod
    def class_init(cls):
        if cls._logger is not None:
            return

        cls._logger = module_logger.getChild(cls.__name__)

    def __init__(self):
        cls = type(self)

        super().__init__()

        self._logger.enter()
        self.ssml = None
        self.streamFlags = None
        self.sapi = SAPI()
        if not self.sapi.valid:
            self.flagAsDead('RESET')
            return
        self.update()
        cls._logger.exit()

    @classmethod
    def isSupportedOnPlatform(cls):
        cls._logger.enter()
        return SystemQueries.isWindows()

    @classmethod
    def isInstalled(cls):
        cls._logger.enter()
        return cls.isSupportedOnPlatform()

    def sapiValidCheck(func):
        def checker(self, *args, **kwargs):
            cls = type(self)
            cls._logger.enter()
            if not self.sapi or not self.sapi.valid:
                return self.flagAsDead('RESET')
            else:
                return func(self, *args, **kwargs)

        return checker

    @sapiValidCheck
    def runCommand(self, text, outFile):
        cls = type(self)
        cls._logger.enter()
        stream = self.sapi.SpFileStream()
        if not stream:
            cls._logger.exit()
            return False
        try:
            stream.Open(outFile, 3)  # 3=SSFMCreateForWrite
        except self.sapi.COMError as e:
            self.sapi.logSAPIError(e)
            return False
        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml, self.sapi.streamFlags)
        stream.close()
        cls._logger.exit()
        return True

    @sapiValidCheck
    def runCommandAndSpeak(self, text):
        cls = type(self)
        cls._logger.enter()
        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml, self.sapi.flags)
        cls._logger.exit()

    @sapiValidCheck
    def getWavStream(self, text):
        cls = type(self)
        cls._logger.enter()
        fmt = self.sapi.SpAudioFormat()
        if not fmt:
            cls._logger.exit()
            return None
        fmt.Type = 22

        stream = self.sapi.SpMemoryStream()
        if not stream:
            cls._logger.exit()
            return None
        stream.Format = fmt
        self.sapi.set_SpVoice_AudioOutputStream(stream)

        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml, self.streamFlags)

        wavIO = io.StringIO()
        self.createWavFileObject(wavIO, stream)
        cls._logger.exit()
        return wavIO

    def createWavFileObject(self, wavIO, stream):
        cls = type(self)
        cls._logger.enter()
        # Write wave via the wave module
        wavFileObj = wave.open(wavIO, 'wb')
        wavFileObj.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
        wavFileObj.writeframes(array.array('B', stream.GetData()).tostring())
        wavFileObj.close()
        cls._logger.exit()

    def stop(self):
        cls = type(self)
        cls._logger.enter()
        if not self.sapi:
            cls._logger.exit()
            return
        if not self.inWavStreamMode:
            self.sapi.stopSpeech()
        cls._logger.exit()

    def update(self):
        cls = type(self)
        cls._logger.enter()
        self.setMode(self.getMode())
        self.ssml = self.baseSSML.format(text='{text}', volume=self.setting('volume'),
                                         speed=self.setting('speed'),
                                         pitch=self.setting('pitch'))
        voice_name = self.setting('voice')
        self.sapi.set_SpVoice_Voice(voice_name)
        cls._logger.exit()

    def getMode(self):
        cls = type(self)
        cls._logger.enter()
        if self.setting('speak_via_xbmc'):
            cls._logger.exit()
            return SimpleTTSBackendBase.WAVOUT
        else:
            if self.sapi:
                self.sapi.set_SpVoice_AudioOutputStream(None)
            cls._logger.exit()
            return SimpleTTSBackendBase.ENGINESPEAK

    @classmethod
    def settingList(cls, setting, *args):
        cls._logger.enter()
        sapi = SAPI()
        if setting == 'voice':
            voices = []
            v = sapi.SpVoice_GetVoices()
            if not v:
                return voices
            for i in range(len(v)):
                name = 'voice name not found'
                try:
                    name = v[i].GetDescription()
                except Exception as e:  # COMError as e: #analysis:ignore
                    sapi.logSAPIError(e)
                voices.append((name, name))
            cls._logger.exit()
            return voices

    @staticmethod
    def available():
        SAPITTSBackend._logger.enter()
        return SystemQueries.isWindows()

#    def getWavStream(self,text):
#        #Have SAPI write to file
#        stream = self.sapi.SpFileStream()
#        fpath = os.path.join(util.getTmpfs(),'speech.wav')
#        open(fpath,'w').close()
#        stream.Open(fpath,3)
#        self.sapi.set_SpVoice_AudioOutputStream(stream)
#        self.sapi.SpVoice_Speak(text,0)
#        stream.close()
#        return open(fpath,'rb')

#    def createWavFileObject(self,wavIO,stream):
#        #Write wave headers manually
#        import struct
#        data = array.array('B',stream.GetData()).tostring()
#        dlen = len(data)
#        header = struct.pack(        '4sl8slhhllhh4sl',
#                                            'RIFF',
#                                            dlen+36,
#                                            'WAVEfmt ',
#                                            16, #Bits
#                                            1, #Mode
#                                            1, #Channels
#                                            22050, #Samplerate
#                                            22050*16/8, #Samplerate*Bits/8
#                                            1*16/8, #Channels*Bits/8
#                                            16,
#                                            'data',
#                                            dlen
#        )
#        wavIO.write(header)
#        wavIO.write(data)


SAPITTSBackend.class_init()