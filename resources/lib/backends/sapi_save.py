# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import array
import io
import sys
import wave

import comtypes.client  # Importing comtypes.client will make the gen subpackage
try:
    from comtypes.gen import SpeechLib  # comtypes
except ImportError:
    # Generate the SpeechLib lib and any associated files
    engine = comtypes.client.CreateObject("SAPI.SpVoice")
    stream = comtypes.client.CreateObject("SAPI.SpFileStream")
    from comtypes.gen import SpeechLib

from io import BytesIO
import time
import math
import os
import weakref
from backends.settings.service_types import Services, ServiceType

from common import *

from backends.settings.constraints import Constraints
from common.setting_constants import Backends, Genders, Mode
from common.settings_low_level import SettingsProperties
from xml.sax import saxutils

from common.constants import Constants
from common.logger import *
from common.system_queries import SystemQueries
from common import utils
from backends.base import SimpleTTSBackend

module_logger = BasicLogger.get_module_logger(module_path=__file__)

'''
  SAPI is a built-in Windows TTS api. SAPI 5.4 (the latest) was released 2009
  
  Modern Windows uses System.Speech.Synthesis 
 
    If you run the following command in the terminal, it will speak the words "testing 
    to see if this works properly"
    PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object 
    System.Speech.Synthesis.SpeechSynthesizer).Speak('testing to see if this works 
    properly');"
    This python script generates this command with whatever text is passed to the speak 
    function
    
    
    randomString = "Hello Matt!"
    
    def speak(stringOfText):
            # This function will make windows say whatever string is passed
            # You can copy and paste this function into any script, and call it using: 
            speak("Random String")
            # Be sure to import os into any script you add this function to
            stringOfText = stringOfText.strip()
            # Removes any trailing spaces or new line characters
            stringOfText = stringOfText.replace("'", "")
            # Removes all single quotes by replacing all instances with a blank character
        stringOfText = stringOfText.replace('"', "")
            # Removes all double quotes by replacing all instances with a blank character
        command = f"PowerShell -Command "Add-Type -AssemblyName System.Speech; \
            (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{
            stringOfText}');"
    # This is just a really long command that tells windows to say a text out loud
    # At the end I am adding in the stringOfText parameter to the command
    os.system(command)
    # This runs the command as if you opened up a terminal and typed it in

    speak(randomString)
    speak("testing 1 2 3 4 5")

'''


def lookupGenericComError(com_error):
    try:
        errno = '0x%08X' % (com_error.hresult & 0xffffffff)
        with open(os.path.join(Constants.BACKENDS_DIRECTORY, 'comerrors.txt'), 'r',
                  encoding='utf-8') as f:
            lines = f.read().splitlines()
        for l1, l2, l3 in zip(lines[0::3], lines[1::3], lines[2::3]):
            if errno in l2:
                return l1, l3
    except AbortException:
        reraise(*sys.exc_info())
    except:
        pass
    return None


class SAPI_Utils:
    """

    """
    ID = Backends.SAPI_ID
    service_ID: str = Services.SAPI_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    backend_id: str = Backends.SAPI_ID
    engine_id: str = Backends.SAPI_ID
    displayName: str = 'SAPI'
    UTF_8: Final[str] = '1'

    voice_map: Dict[str, Tuple[str, str, Genders]] = None
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False

    DEFAULT = 0
    ASYNC = 1
    PURGE_BEFORE_SPEAK = 2
    IS_FILENAME = 4
    IS_XML = 8
    IS_NOT_XML = 16
    PERSIST_XML = 32
    SPEAK_PUNC = 64
    PARSE_SAPI = 128

    speedConstraints: Constraints = Constraints(-10, 0, 10, True, False, 1.0,
                                                SettingsProperties.SPEED)
    pitchConstraints: Constraints = Constraints(-10, 0, 10, True, False, 1.0,
                                                SettingsProperties.PITCH)
    volumeConstraints: Constraints = Constraints(0, 100, 100, True, False, 1.0,
                                                 SettingsProperties.VOLUME)

    @classmethod
    def class_init(cls):
        cls._class_name = cls.__class__.__name__
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    def __init__(self, *args, **kwargs):
        cls = type(self)

        self.SpVoice = None
        self.comtypesClient = None
        self.valid = False
        self._voiceName = None
        self.streamFlags = None
        self.flags = None
        self.interrupt = False
        try:
            self.reset()
        except AbortException:
            reraise(*sys.exc_info())
        except:
            self._logger.exception('SAPI: Initialization failed: retrying...')
            utils.sleep(1000)  # May not be necessary, but here it is
            try:
                self.reset()
            except AbortException:
                reraise(*sys.exc_info())
            except:
                self._logger.exception('SAPI: Initialization failed: Giving up.')
                return
        self.valid = True
        #  self.COMError = importHelper('_ctypes').COMError
        self.setStreamFlags()

    '''
    def importComtypes(self):
        # Remove all (hopefully) references to comtypes import...
        cls = type(self)

        del self.comtypesClient
        self.comtypesClient = None
        for m in list(sys.modules.keys()):
            if m.startswith('comtypes'):
                del sys.modules[m]
        import gc
        gc.collect()
        # and then import
        self.comtypesClient = importHelper('comtypes.client')
    '''

    def reset(self):
        cls = type(self)

        del self.SpVoice
        self.SpVoice = None
        # self.cleanComtypes()
        # self.importComtypes()
        self.resetSpVoice()

    def resetSpVoice(self):
        cls = type(self)

        self.SpVoice = comtypes.client.CreateObject('SAPI.SPVoice')
        voice = self._getVoice()
        if voice:
            self.SpVoice.Voice = voice

    def setStreamFlags(self):
        cls = type(self)

        self.flags = self.PARSE_SAPI | self.IS_XML | self.ASYNC
        self.streamFlags = self.PARSE_SAPI | self.IS_XML | self.ASYNC
        try:
            self.SpVoice.Speak('', self.flags)
        except Exception as e:  # self.COMError as e:
            cls._logger.exception('')
            if cls._logger.isEnabledFor(DEBUG):
                # self.logSAPIError(e)
                cls._logger.debug('SAPI: XP Detected - changing flags')
            self.flags = self.ASYNC
            self.streamFlags = self.ASYNC
        finally:
            pass

    def cleanComtypes(self):  # TODO: Make this SAPI specific?
        cls = type(self)

        '''
        try:
            gen = os.path.join(Constants.BACKENDS_DIRECTORY, 'comtypes', 'gen')
            import stat, shutil
            os.chmod(gen, stat.S_IWRITE)
            shutil.rmtree(gen, ignore_errors=True)
            if not os.path.text_exists(gen):
                os.makedirs(gen)
        except AbortException:
            reraise(*sys.exc_info())
        except:
            cls._logger.exception('SAPI: Failed to empty comtypes gen dir')
        finally:
            pass
        '''
        pass

    '''
    def logSAPIError(self, com_error, extra=''):
        cls = type(self)

        try:
            errno = str(com_error.hresult)
            with open(os.path.join(Constants.BACKENDS_DIRECTORY,
                                   'sapi_comerrors.txt'), 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            for l1, l2 in zip(lines[0::2], lines[1::2]):
                bits = l1.split()
                if errno in bits:
                    cls._logger.debug(
                            'SAPI specific COM error ({0})[{1}]: {2}'.format(errno,
                                                                             bits[0],
                                                                             l2 or '?'))
                    break
            else:
                error = lookupGenericComError(com_error)
                if error:
                    cls._logger.debug(
                            'SAPI generic COM error ({0})[{1}]: {2}'.format(errno,
                                                                            error[0],
                                                                            error[
                                                                                1] or
                                                                            '?'))
                else:
                    self._logger.debug(
                            'Failed to lookup SAPI/COM error: {0}'.format(com_error))
        except AbortException:
            reraise(*sys.exc_info())
        except:
            cls._logger.exception('Error looking up SAPI error: {0}'.format(com_error))
    '''

    def _getVoice(self, voice_name=None):
        cls = type(self)

        voice_name = voice_name or self._voiceName
        if voice_name:
            v = self.SpVoice.getVoices() or []
            for i in range(len(v)):
                voice = v[i]
                if voice_name == voice.GetDescription():
                    return voice
        return None

    def checkSAPI(func):
        def checker(self, *args, **kwargs):
            cls = type(self)

            if not self.valid:
                cls._logger.debug('SAPI: Broken - ignoring {0}'.format(func.__name__))
                return None
            try:
                return func(self, *args, **kwargs)
            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:  # self.COMError as e:
                cls._logger.exception('')
            self.valid = False
            cls._logger.debug('SAPI: Resetting...')
            utils.sleep(1000)
            try:
                self.reset()
                self.valid = True
                cls._logger.debug('SAPI: Resetting succeeded.')
                return func(self, *args, **kwargs)
            except AbortException:
                reraise(*sys.exc_info())
            except:
                self.valid = False
                cls._logger.error('SAPI: {0} error'.format(func.__name__))
            finally:
                pass

        return checker

    # Wrapped SAPI methods
    @checkSAPI
    def SpVoice_Speak(self, ssml, flags):
        cls = type(self)

        return self.SpVoice.Speak(ssml, flags)

    @checkSAPI
    def SpVoice_GetVoices(self):
        cls = type(self)

        return self.SpVoice.getVoices()

    @checkSAPI
    def stopSpeech(self):
        cls = type(self)

        self.SpVoice.Speak('', self.ASYNC | self.PURGE_BEFORE_SPEAK)

    @checkSAPI
    def SpFileStream(self):
        cls = type(self)

        return self.comtypesClient.CreateObject("SAPI.SpFileStream")

    @checkSAPI
    def SpAudioFormat(self):
        cls = type(self)

        return self.comtypesClient.CreateObject("SAPI.SpAudioFormat")

    @checkSAPI
    def SpMemoryStream(self):
        cls = type(self)

        return self.comtypesClient.CreateObject("SAPI.SpMemoryStream")

    def validCheck(func):
        def checker(self, *args, **kwargs):
            cls = type(self)

            if not self.valid:
                cls._logger.debug('SAPI: Broken - ignoring {0}'.format(func.__name__))
                return
            return func(self, *args, **kwargs)

        return checker

    @validCheck
    def set_SpVoice_Voice(self, voice_name):
        cls = type(self)

        self._voiceName = voice_name
        voice = self._getVoice(voice_name)
        self.SpVoice.Voice = voice

    @validCheck
    def set_SpVoice_AudioOutputStream(self, stream):
        cls = type(self)

        self.SpVoice.AudioOutputStream = stream


SAPI_Utils.class_init()


class SAPI_Backend(SimpleTTSBackend):
    ID = Backends.SAPI_ID
    service_ID: str = Services.SAPI_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    backend_id: str = Backends.SAPI_ID
    engine_id: str = Backends.SAPI_ID
    displayName: str = 'SAPI'
    UTF_8: Final[str] = '1'

    voice_map: Dict[str, Tuple[str, str, Genders]] = None
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False
    displayName = 'SAPI (Windows Internal)'
    settings = {SettingsProperties.SPEAK_VIA_KODI: True,
                SettingsProperties.VOICE         : '',
                SettingsProperties.SPEED         : 0,
                SettingsProperties.PITCH         : 0,
                SettingsProperties.VOLUME        : 100
                }
    canStreamWav = True
    speedConstraints: Constraints = Constraints(-10, 0, 10, True, False, 1.0,
                                                SettingsProperties.SPEED)
    pitchConstraints: Constraints = Constraints(-10, 0, 10, True, False, 1.0,
                                                SettingsProperties.PITCH)
    volumeConstraints: Constraints = Constraints(0, 100, 100, True, False, 1.0,
                                                 SettingsProperties.VOLUME)
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

    _logger: BasicLogger = None
    _class_name: str = None

    @classmethod
    def class_init(cls):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)

        self.ssml = None
        self.streamFlags = None
        self.sapi = comtypes.client.CreateObject('SAPI.SPVoice')
        if not self.sapi.valid:
            self.flagAsDead('RESET')
            return
        self.update()

    @classmethod
    def isSupportedOnPlatform(cls):

        return SystemQueries.isWindows()

    @classmethod
    def isInstalled(cls):

        return cls.isSupportedOnPlatform()

    def sapiValidCheck(func):
        def checker(self, *args, **kwargs):
            cls = type(self)

            if not self.sapi or not self.sapi.valid:
                return self.flagAsDead('RESET')
            else:
                return func(self, *args, **kwargs)

        return checker

    @sapiValidCheck
    def runCommand(self, text, outFile):
        cls = type(self)

        stream = self.sapi.SpFileStream()
        if not stream:
            return False
        try:
            stream.Open(outFile, 3)  # 3=SSFMCreateForWrite
        except Exception as e:  # self.sapi.COMError as e:
            cls._logger.exception('')
            return False
        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml, self.sapi.streamFlags)
        stream.close()
        return True

    @sapiValidCheck
    def runCommandAndSpeak(self, text):
        cls = type(self)

        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml, self.sapi.flags)

    @sapiValidCheck
    def getWavStream(self, text):
        cls = type(self)

        fmt = self.sapi.SpAudioFormat()
        if not fmt:
            return None
        fmt.Type = 22

        stream = self.sapi.SpMemoryStream()
        if not stream:
            return None
        stream.Format = fmt
        self.sapi.set_SpVoice_AudioOutputStream(stream)

        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml, self.streamFlags)

        wavIO = io.StringIO()
        self.createWavFileObject(wavIO, stream)
        return wavIO

    def createWavFileObject(self, wavIO, stream):
        cls = type(self)

        # Write wave via the wave module
        wavFileObj = wave.open(wavIO, 'wb')
        wavFileObj.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
        wavFileObj.writeframes(array.array('B', stream.GetData()).tostring())
        wavFileObj.close()

    def stop(self):
        cls = type(self)

        if not self.sapi:
            return
        if not self.inWavStreamMode:
            self.sapi.stopSpeech()

    def update(self):
        cls = type(self)

        self.setMode(self.getMode())
        self.ssml = self.baseSSML.format(text='{text}',
                                         volume=self.setting(SettingsProperties.VOLUME),
                                         speed=self.setting(SettingsProperties.SPEED),
                                         pitch=self.setting(SettingsProperties.PITCH))
        voice_name = self.setting(SettingsProperties.VOICE)
        self.sapi.set_SpVoice_Voice(voice_name)

    def getMode(self):
        cls = type(self)

        if self.setting(SettingsProperties.SPEAK_VIA_KODI):
            return Mode.FILEOUT
        else:
            if self.sapi:
                self.sapi.set_SpVoice_AudioOutputStream(None)
            return Mode.ENGINESPEAK

    @classmethod
    def settingList(cls, setting, *args):

        sapi = SAPI_Backend()
        if setting == SettingsProperties.VOICE:
            voices = []
            v = sapi.SpVoice_GetVoices()
            if not v:
                return voices
            for i in range(len(v)):
                name = 'voice name not found'
                try:
                    name = v[i].GetDescription()
                except Exception as e:  # COMError as e: #analysis:ignore
                    cls._logger.exception('')
                    # sapi.logSAPIError(e)
                voices.append((name, name))
            return voices

    @staticmethod
    def available():
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


SAPI_Backend.class_init()
