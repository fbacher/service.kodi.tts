"""
Provides a means to access a Converter class by name. The map is built using dynamic
code to invoke a Converter's register function which adds itself to the map. This
avoids nasty dependency issues during startup.
"""
from common.setting_constants import Converters
from converters.iconverter import IConverter
from converters.base_converter import BaseAudioConverter
from common.typing import *
from converters.basic_converters import LameAudioConverter


class ConverterIndex:
    converter_ids: List[str] = [
        Converters.NONE,
        Converters.WINDOWS,
        Converters.SOX,
        Converters.MPLAYER,
        Converters.MPG123,
        Converters.MPG321_OE_PI,
        Converters.MPG321,
        Converters.LAME]

    _converter_lookup: Dict[str, IConverter] = {}

    @staticmethod
    def register(converter_id: str, converter: IConverter ) -> None:
        ConverterIndex._converter_lookup[converter_id] = converter
        return

    @staticmethod
    def get_converter(converter_id: str) -> Type[IConverter]:
        converter: IConverter | None = ConverterIndex._converter_lookup.get(converter_id)
        if converter is None:
            BootstrapConverters.load_converter(converter_id)
            converter = ConverterIndex._converter_lookup.get(converter_id)
        return converter
