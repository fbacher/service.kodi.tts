"""
Provides a means to access a Converter class by name. The map is built using dynamic
code to invoke a Converter's register function which adds itself to the map. This
avoids nasty dependency issues during startup.
"""
from common.typing import *
from converters.iconverter import IConverter


class ConverterIndex:
    _converter_lookup: Dict[str, IConverter] = {}

    @staticmethod
    def register(converter_id: str, converter: IConverter) -> None:
        ConverterIndex._converter_lookup[converter_id] = converter
        return

    @staticmethod
    def get_converter(converter_id: str) -> IConverter:
        converter: IConverter | None = ConverterIndex._converter_lookup.get(converter_id)
        if converter is None:
            exec(f"{converter_id}.register")
            converter = ConverterIndex._converter_lookup.get(converter_id)
        return converter
