# coding=utf-8
from typing import Dict, List

from backends.settings.i_validators import AllowedValue


class SharedConfigData:

    global_allowed_player_modes: Dict[str, List[AllowedValue]]
