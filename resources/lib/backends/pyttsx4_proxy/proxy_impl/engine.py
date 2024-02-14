from __future__ import annotations  # For union operator |

from typing import Any, Dict, List

from backends.pyttsx4_proxy.proxy_impl.voice import Voice
from common.logger import BasicLogger
from backends.pyttsx4_proxy.proxy import Transport, Cmds, CmdArgument

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Engine:
    """
    @ivar proxy: Proxy to a driver implementation
    @type proxy: L{DriverProxy}
    @ivar _connects: Array of subscriptions
    @type _connects: list
    @ivar _inLoop: Running an event loop or not
    @type _inLoop: bool
    @ivar _driverLoop: Using a driver event loop or not
    @type _driverLoop: bool
    @ivar _debug: Print exceptions or not
    @type _debug: bool
    """
    logger: BasicLogger = None

    def __init__(self, driverName: str = None, debug: bool = False) -> None:
        """
        Constructs a new TTS engine instance or reuses the existing instance for
        the driver name.

        @param driverName: Name of the platform specific driver to use. If
            None, selects the default driver for the operating system.
        @param debug: Debugging output enabled or not
        @return: Engine instance
        @rtype: L{engine.Engine}
        """
        clz = type(self)
        if clz.logger is None:
            clz.logger = module_logger.getChild(clz.__name__)

        self._proxy_self: str = None
        self._driver_name: str = None
        try:
            msg_id: str = Transport.get_msg_id()
            cmd: Dict[str, Any] = {Cmds.CMD.name        : Cmds.INIT.name,
                                   CmdArgument.ARGS.name: {CmdArgument.MSG_ID.name: msg_id,
                                                      CmdArgument.DRIVER_NAME.name: driverName,
                                                      CmdArgument.DEBUG.name      : debug}
                                   }
            Transport.send(cmd)
            # Response: {'MSG_ID': '1', 'ENGINE': 139947667575}^
            response: Dict[str, str] = Transport.get_response()
            self._proxy_self = response.get(CmdArgument.ENGINE.name)
            self._driver_name = response.get(CmdArgument.DRIVER_NAME)
            if self._proxy_self is None:
                clz.logger.error(f'Invalid engine proxy. raw response: {response}')
            else:
                clz.logger.debug(f'created engine for driver: {self._driver_name}')
        except Exception as e:
            response = None
            clz.logger.exception('')

        return

    '''
    def connect(self, topic, cb):
        """
        Registers a callback for an event topic. Valid topics and their
        associated values:

        started-utterance: name=<str>
        started-word: name=<str>, location=<int>, length=<int>
        finished-utterance: name=<str>, completed=<bool>
        error: name=<str>, exception=<exception>

        @param topic: Event topic name
        @type topic: str
        @param cb: Callback function
        @type cb: callable
        @return: Token to use to unregister
        @rtype: dict
        """
        arr = self._connects.setdefault(topic, [])
        arr.append(cb)
        return {'topic': topic, 'cb': cb}

    def disconnect(self, token):
        """
        Unregisters a callback for an event topic.

        @param token: Token of the callback to unregister
        @type token: dict
        """
        topic = token['topic']
        try:
            arr = self._connects[topic]
        except KeyError:
            return
        arr.remove(token['cb'])
        if len(arr) == 0:
            del self._connects[topic]
    '''

    def say(self, text: str, name: str | None = None) -> str | None:
        """
               Adds an utterance to speak to the event queue.

               @param text: Text to sepak
               @param name: Name to associate with this utterance. Included in
                   notifications about this utterance.
               """
        clz = type(self)
        clz.logger.debug(f'text: {text} name: {name}')
        if text is None:
            return "Argument value can't be none or empty"
        else:
            try:
                cmd: Dict[str, str] = {Cmds.CMD.name        : Cmds.SAY.name,
                                       CmdArgument.ARGS.name: {CmdArgument.TEXT.name: text,
                                                               CmdArgument.ENGINE_ID.name: self._proxy_self,
                                                          CmdArgument.NAME.name: name}
                                       }
                Transport.send(cmd)
            except Exception as e:
                pass
        return

    '''
    def stop(self):
        """
        Stops the current utterance and clears the event queue.
        """
        self.proxy.stop()

    def save_to_file(self, text, filename, name=None):
        """
        Adds an utterance to speak to the event queue.

        @param text: Text to sepak
        @type text: unicode
        @param filename: the name of file to save.
        @param name: Name to associate with this utterance. Included in
            notifications about this utterance.
        @type name: str
        """
        self.proxy.save_to_file(text, filename, name)

    def isBusy(self):
        """
        @return: True if an utterance is currently being spoken, false if not
        @rtype: bool
        """
        return self.proxy.isBusy()
    '''

    def getProperty(self, name) -> Any:
        """
        Gets the current value of a property. Valid names and values include:

        voices: List of L{voice.Voice} objects supported by the driver
        voice: String ID of the current voice
        rate: Integer speech rate in words per minute
        volume: Floating point volume of speech in the range [0.0, 1.0]

        Numeric values outside the valid range supported by the driver are
        clipped.

        @param name: Name of the property to fetch
        @type name: str
        @return: Value associated with the property
        @rtype: object
        @raise KeyError: When the property name is unknown
        """
        clz = type(self)
        clz.logger.debug(f'name: {name}')
        voices: List[Voice] = []
        if name is None:
            return "Argument value can't be none or empty"
        else:
            try:
                cmd: Dict[str, str] = {Cmds.CMD.name        : Cmds.GET_PROPERTY.name,
                                       CmdArgument.ARGS.name: {
                                           CmdArgument.ENGINE_ID.name: self._proxy_self,
                                           CmdArgument.NAME.name     : name}
                                       }
                Transport.send(cmd)
                # Response: {'MSG_ID': '123',
                #             'VOICES':  [{VOICE_ID: <string_id>>,
                #                             NAME: <voice name>},
                #                             ... ]
                #           }
                response: Dict[str, str | List[Dict[str, str]]] = Transport.get_response()
                voice_list: List[Dict[str, str]] = response.get(CmdArgument.VOICES.name)
                if not voice_list:
                    clz.logger.error(f'Expected list of VOICEs')
                    return []
                voice_entry: Dict[str, str]
                for voice_entry in voice_list:
                    voice_id: str = voice_entry.get(CmdArgument.VOICE_ID.name)
                    voice_name: str = voice_entry.get(CmdArgument.NAME.name)
                    voice_age: int = voice_entry.get(CmdArgument.AGE.name)
                    voice_gender: str = voice_entry.get(CmdArgument.GENDER.name)
                    voice_languages: List[str] = voice_entry.get(CmdArgument.LANGUAGES.name)

                    voice = Voice(voice_id, name=voice_name, age=voice_age,
                                  gender=voice_gender, languages=voice_languages)
                    voices.append(voice)

            except Exception as e:
                clz.logger.exception('')
        return voices

    def setProperty(self, name: str, value: Any) -> None:
        """
        Adds a property value to set to the event queue. Valid names and values
        include:

        voice: String ID of the voice
        rate: Integer speech rate in words per minute
        volume: Floating point volume of speech in the range [0.0, 1.0]

        Numeric values outside the valid range supported by the driver are
        clipped.

        @param name: Name of the property to fetch
        @type name: str
        @param: Value to set for the property
        @rtype: object
        @raise KeyError: When the property name is unknown
        """
        clz = type(self)
        clz.logger.debug(f'name: {name} value: {value}')
        voices: List[Voice] = []
        if name is None:
            clz.logger.error( "Argument value can't be none or empty")
        else:
            try:
                cmd: Dict[str, str] = {Cmds.CMD.name        : Cmds.SET_PROPERTY.name,
                                       CmdArgument.ARGS.name: {
                                           CmdArgument.ENGINE_ID.name: self._proxy_self,
                                           CmdArgument.PROPERTY_NAME.name     : name,
                                           CmdArgument.VALUE.name : value}
                                       }
                Transport.send(cmd)
            except Exception as e:
                clz.logger.exception('')
        return

    def runAndWait(self) -> None:
        """
        Runs an event loop until all commands queued up until this method call
        complete. Blocks during the event loop and returns when the queue is
        cleared.

        @raise RuntimeError: When the loop is already running
        """
        try:
            cmd: Dict[str, str] = {Cmds.CMD.name: Cmds.RUN_AND_WAIT.name,
                                   CmdArgument.ARGS.name: {CmdArgument.ENGINE_ID.name:
                                                           self._proxy_self}
                                   }
            Transport.send(cmd)
        except Exception as e:
            pass
        return

    '''
    def runAndWait(self):
        """
        Runs an event loop until all commands queued up until this method call
        complete. Blocks during the event loop and returns when the queue is
        cleared.

        @raise RuntimeError: When the loop is already running
        """
        if self._inLoop:
            raise RuntimeError('run loop already started')
        self._inLoop = True
        self._driverLoop = True
        self.proxy.runAndWait()

    def startLoop(self, useDriverLoop=True):
        """
        Starts an event loop to process queued commands and callbacks.

        @param useDriverLoop: If True, uses the run loop provided by the driver
            (the default). If False, assumes the caller will enter its own
            run loop which will pump any events for the TTS engine properly.
        @type useDriverLoop: bool
        @raise RuntimeError: When the loop is already running
        """
        if self._inLoop:
            raise RuntimeError('run loop already started')
        self._inLoop = True
        self._driverLoop = useDriverLoop
        self.proxy.startLoop(self._driverLoop)

    def endLoop(self):
        """
        Stops a running event loop.

        @raise RuntimeError: When the loop is not running
        """
        if not self._inLoop:
            raise RuntimeError('run loop not started')
        self.proxy.endLoop(self._driverLoop)
        self._inLoop = False

    def iterate(self):
        """
        Must be called regularly when using an external event loop.
        """
        if not self._inLoop:
            raise RuntimeError('run loop not started')
        elif self._driverLoop:
            raise RuntimeError('iterate not valid in driver run loop')
        self.proxy.iterate()
    '''
