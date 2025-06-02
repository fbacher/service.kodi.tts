# coding=utf-8
from __future__ import annotations  # For union operator |

import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Final, List

import pyttsx4

from enum import auto, StrEnum

from pyttsx4.voice import Voice

tmpdir: str = os.environ.get('TEMP')
logfile: str = str(Path(tmpdir) / 'kodi_daemon.log')
logging.basicConfig(filename=logfile, filemode='w')
module_logger: logging.Logger = logging.getLogger('tts_daemon')
module_logger.setLevel(logging.DEBUG)

class Cmds(StrEnum):
    CMD = auto(),
    GET_PROPERTY = auto(),
    INIT = auto(),
    SAY = auto(),
    SET_PROPERTY = auto(),
    RUN_AND_WAIT = 'runAndWait'


class CmdArgument(StrEnum):
    AGE = auto(),
    ARGS = auto(),
    DEBUG = auto(),
    DRIVER_NAME = 'driverName',
    ENGINE = auto(),
    ENGINE_ID = auto(),
    GENDER = auto(),
    LANGUAGES = auto(),
    MSG_ID = auto(),
    NAME = auto(),
    PROPERTY_NAME = auto(),
    SELF = auto(),
    TEXT = auto(),
    VOICE_ID = auto(),
    VALUE = auto(),
    VOICES = auto()

engine_for_id: Dict[str, Any] = {}
driver_for_id: Dict[str, Any] = {}
voice_for_id: Dict[str, Any] = {}


def get_id_for_engine(ptr: Any) -> str:
    str_value = str(hash(ptr))
    engine_for_id[str_value] = ptr
    module_logger.debug(f'engine: {ptr} engine_id: {str_value}')
    return str_value


def get_engine_for_id(id: str) -> Any:
    eng = engine_for_id.get(id)
    module_logger.debug(f'id: {id} type: {type(id)} engine: {eng}')
    if not eng:
        for id2, engx in engine_for_id.items():
            module_logger.debug(f'engine_id: {id2} engine: {engx}')
        eng = engine_for_id[str(id)]
    return eng



if __name__ == '__main__':

    stdin_fileno = sys.stdin
    engine: pyttsx4.Engine | None = None

    module_logger.debug(f'In daemon.main')
    try:
        for line in stdin_fileno:
            try:
                module_logger.debug(f'line: {line}')
                cmd: Dict[str, Any] = json.loads(line)
                # key=init {driverName: str, debug: bool}
                cmd_name: str
                args: Any
                cmd_name = cmd.get(Cmds.CMD.name)
                args = cmd.get(CmdArgument.ARGS.name)
                response: Dict[str, str] | None = None
                match cmd_name:
                    case Cmds.INIT.name:
                        args:  Dict[str, str]
                        msg_id: str = args.get(CmdArgument.MSG_ID.name)
                        driverName: str = args.get(CmdArgument.DRIVER_NAME.name)
                        debug: bool = args.get(CmdArgument.DEBUG.name, False)
                        engine = pyttsx4.init(driverName=driverName, debug=debug)
                        engine_id = get_id_for_engine(engine)
                        module_logger.debug(f'INIT engine: {engine} engine_id: {engine_id}')
                        response = {CmdArgument.MSG_ID.name: msg_id,
                                    CmdArgument.DRIVER_NAME.name: driverName,
                                    CmdArgument.ENGINE.name: engine_id
                                    }
                        # result = engine  # Need to cache engine instances and return
                        # unique value as the key. Presumably there can be more than one
                        # instance of an engine of the same type, voice, etc.

                    case Cmds.GET_PROPERTY.name:
                        args: Dict[str, str]
                        msg_id: str = args.get(CmdArgument.MSG_ID.name)
                        property_name: str = args.get(CmdArgument.NAME.name)
                        engine_id: str = args.get(CmdArgument.ENGINE_ID.name)
                        engine = get_engine_for_id(engine_id)
                        voices: List[Voice] = engine.getProperty(property_name)
                        response: Dict[str, str | List[Dict[str, str]]] = {}
                        response[CmdArgument.MSG_ID.name] = msg_id
                        voice_list: List[Dict[str, str]] = []
                        for voice in voices:
                            voice_entry: Dict[str, str] = {
                                CmdArgument.VOICE_ID.name : voice.id,
                                CmdArgument.NAME.name     : voice.name,
                                CmdArgument.AGE.name      : voice.age,
                                CmdArgument.GENDER.name   : voice.gender,
                                CmdArgument.LANGUAGES.name: voice.languages
                            }
                            voice_list.append(voice_entry)
                        response[CmdArgument.VOICES.name] = voice_list
                    case Cmds.SAY.name:
                        # {"CMD": "SAY",
                        # "ARGS": {"TEXT": "You suck, you old dog.", "NAME": null,
                        #  "SELF": "133775925421",}}

                        args: Dict[str, str]
                        text: str = args.get(CmdArgument.TEXT.name)
                        engine_id = args.get(CmdArgument.ENGINE_ID.name)
                        name: str = args.get(CmdArgument.NAME.name)
                        engine = get_engine_for_id(engine_id)
                        module_logger.debug(f'About to call say: {text} name: {name}')
                        engine.say(text, name)
                    case Cmds.SET_PROPERTY.name:
                        args: Dict[str, str]
                        engine_id = args.get(CmdArgument.ENGINE_ID.name)
                        name: str = args.get(CmdArgument.PROPERTY_NAME.name)
                        value: Any = args.get(CmdArgument.VALUE.name)
                        engine = get_engine_for_id(engine_id)
                        module_logger.debug(f'About to set property {name} to: {value}')
                        engine.setProperty(name, value)

                    case Cmds.RUN_AND_WAIT.name:
                        args: Dict[str, str]
                        engine_id = args.get(CmdArgument.ENGINE_ID.name)
                        engine = get_engine_for_id(engine_id)
                        module_logger.debug(f'runAndWait')
                        engine.runAndWait()
                if response:
                    msg: str = json.dumps(response)
                    module_logger.debug(f'response: {msg}')
                    sys.stdout.write(f'{msg}\n')
                    sys.stdout.flush()
            except ImportError as e:
                module_logger.exception('')  # Driver Not Found
            except RuntimeError as e:
                module_logger.exception('')  # Driver failed to initialize
            except Exception as e:
                module_logger.exception('')
        module_logger.debug(f'At bottom of loop stdin closed: {sys.stdin.closed}')

        module_logger.debug(f'Leaving loop')
    except Exception as e:
        module_logger.exception('')

    module_logger.debug(f'No more input, exiting')
    sys.exit()
