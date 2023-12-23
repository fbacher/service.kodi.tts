import xbmc

from common.__init__ import *


class IBackend:

    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        xbmc.log(f'IBackend classname: {self.__class__.__name__}')
        type(self)._class_name = self.__class__.__name__

    @classmethod
    def getBackend(cls, backend_id: str) -> 'IBackend':
        raise Exception('Not Implemented')

    @classmethod
    def isSettingSupported(cls, setting_id: str) -> bool:
        return cls.isSettingSupported(setting_id)

    @classmethod
    def getSettingNames(cls) -> List[str]:
        """
        Gets a list of all of the setting names/keys that this backend uses

        :return:
        """
        return None

    @classmethod
    def get_setting_default(cls, setting_id: str) -> Any:
        return cls.get_setting_default(setting_id)
