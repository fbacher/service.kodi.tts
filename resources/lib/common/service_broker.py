# coding=utf-8
"""
Provides some basic services without introducing a lot of extra import
dependencies.
"""
from __future__ import annotations

from backends.settings.i_validators import IEngineValidator
from backends.settings.validators import EngineValidator


class ServiceBroker:
    _engine_validator: IEngineValidator = None

    @classmethod
    def get_engine_validator(cls) -> IEngineValidator | EngineValidator:
        if cls._engine_validator is None:
            cls._engine_validator = EngineValidator()
        return cls._engine_validator
